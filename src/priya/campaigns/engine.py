"""In-process asyncio campaign runner.

Each running campaign owns one asyncio task (`_run`) that repeatedly claims
dial-eligible targets (row-locked, so it's safe across concurrent workers) and
dials them through `place_outbound_call`, honouring:

  * concurrency        — at most `campaign.concurrency` calls in flight
  * retry logic        — failed dials are requeued up to `max_attempts`
  * retry delay        — requeued with a `retry_delay_minutes` backoff
  * working hours       — dialing pauses outside [start, end) IST

NOTE (scaling): this runs inside the API process and assumes a single active
replica per campaign. Target claiming uses FOR UPDATE SKIP LOCKED so it is
correctness-safe across replicas, but per-replica loops would each apply the
concurrency cap. For multi-replica execution, move the loop behind a distributed
lock / queue. The DB is the source of truth, so restarts recover cleanly.
"""
from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from priya.config import settings
from priya.db.database import session_scope
from priya.db.models import CampaignStatus
from priya.db.repositories import CampaignRepository
from priya.telephony.outbound import place_outbound_call
from priya.utils.logging import get_logger

log = get_logger(__name__)

IST = timezone(timedelta(hours=5, minutes=30))


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _within_working_hours(start_h: int, end_h: int) -> bool:
    h = datetime.now(IST).hour
    if start_h == end_h:
        return True  # 24x7
    if start_h < end_h:
        return start_h <= h < end_h
    return h >= start_h or h < end_h  # window wraps past midnight


@dataclass
class _RunHandle:
    campaign_id: uuid.UUID
    paused: bool = False
    stop: bool = False
    error: str | None = None
    task: asyncio.Task | None = field(default=None, repr=False)


class CampaignEngine:
    def __init__(self) -> None:
        self._runs: dict[uuid.UUID, _RunHandle] = {}

    # ------------------------------------------------------------------ #
    # Public control surface (called by the API router)
    # ------------------------------------------------------------------ #
    def is_running(self, campaign_id: uuid.UUID) -> bool:
        h = self._runs.get(campaign_id)
        return h is not None and h.task is not None and not h.task.done()

    async def start(self, campaign_id: uuid.UUID) -> None:
        if self.is_running(campaign_id):
            self._runs[campaign_id].paused = False
            return
        handle = _RunHandle(campaign_id=campaign_id)
        handle.task = asyncio.create_task(self._run(handle))
        self._runs[campaign_id] = handle
        log.info("campaign.engine.start", campaign_id=str(campaign_id))

    async def pause(self, campaign_id: uuid.UUID) -> None:
        h = self._runs.get(campaign_id)
        if h is not None:
            h.paused = True
        log.info("campaign.engine.pause", campaign_id=str(campaign_id))

    async def resume(self, campaign_id: uuid.UUID) -> None:
        if self.is_running(campaign_id):
            self._runs[campaign_id].paused = False
            log.info("campaign.engine.resume", campaign_id=str(campaign_id))
        else:
            await self.start(campaign_id)  # relaunch (e.g. after a restart)

    async def stop(self, campaign_id: uuid.UUID) -> None:
        h = self._runs.get(campaign_id)
        if h is not None:
            h.stop = True
        log.info("campaign.engine.stop", campaign_id=str(campaign_id))

    async def shutdown(self) -> None:
        for h in list(self._runs.values()):
            h.stop = True
        tasks = [h.task for h in self._runs.values() if h.task is not None]
        for t in tasks:
            t.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        self._runs.clear()

    # ------------------------------------------------------------------ #
    # Runner loop
    # ------------------------------------------------------------------ #
    async def _run(self, handle: _RunHandle) -> None:
        campaign_id = handle.campaign_id
        poll = settings.campaign_poll_interval_seconds
        inflight: set[asyncio.Task] = set()
        try:
            while not handle.stop:
                async with session_scope() as s:
                    camp = await CampaignRepository(s).get(campaign_id)
                if camp is None or camp.status in (
                    CampaignStatus.completed,
                    CampaignStatus.failed,
                ):
                    break
                if handle.paused or camp.status == CampaignStatus.paused:
                    await asyncio.sleep(poll)
                    continue
                if not _within_working_hours(camp.working_hours_start, camp.working_hours_end):
                    await asyncio.sleep(min(poll * 6, 60.0))
                    continue

                capacity = max(1, min(camp.concurrency, settings.campaign_max_concurrency))
                launched = False
                while len(inflight) < capacity and not handle.stop:
                    async with session_scope() as s:
                        claim = await CampaignRepository(s).claim_next(campaign_id, _utcnow())
                    if claim is None:
                        break
                    target_id, phone, name, _attempts = claim
                    t = asyncio.create_task(
                        self._dial(
                            campaign_id,
                            camp.tenant_id,
                            camp.max_attempts,
                            camp.retry_delay_minutes,
                            target_id,
                            phone,
                            name,
                        )
                    )
                    inflight.add(t)
                    t.add_done_callback(inflight.discard)
                    launched = True

                if not inflight:
                    async with session_scope() as s:
                        active = await CampaignRepository(s).has_active(campaign_id)
                    if not active:
                        break  # nothing pending, nothing in flight → done
                    await asyncio.sleep(poll)  # pending items waiting on retry backoff
                else:
                    await asyncio.sleep(0.2 if launched else poll)

            if inflight:
                await asyncio.gather(*inflight, return_exceptions=True)
        except asyncio.CancelledError:
            handle.stop = True
        except Exception as exc:  # noqa: BLE001
            handle.error = str(exc)
            log.error("campaign.engine.error", campaign_id=str(campaign_id), error=str(exc))
        finally:
            await self._finalize(handle)

    async def _dial(
        self,
        campaign_id: uuid.UUID,
        tenant_id: uuid.UUID,
        max_attempts: int,
        retry_delay_minutes: int,
        target_id: uuid.UUID,
        phone: str | None,
        name: str | None,
    ) -> None:
        success = False
        error: str | None = None
        if not phone:
            error = "lead has no phone number"
        else:
            try:
                await place_outbound_call(
                    phone,
                    name,
                    tenant_id=str(tenant_id),
                    campaign_id=str(campaign_id),
                )
                success = True
            except Exception as exc:  # noqa: BLE001
                error = str(exc)
        async with session_scope() as s:
            await CampaignRepository(s).mark_result(
                target_id,
                success=success,
                max_attempts=max_attempts,
                retry_delay_minutes=retry_delay_minutes,
                now=_utcnow(),
                error=error,
            )

    async def _finalize(self, handle: _RunHandle) -> None:
        campaign_id = handle.campaign_id
        self._runs.pop(campaign_id, None)
        if handle.stop:
            return  # the router already set the terminal state on stop
        async with session_scope() as s:
            repo = CampaignRepository(s)
            camp = await repo.get(campaign_id)
            if camp is not None and camp.status == CampaignStatus.running:
                status = CampaignStatus.failed if handle.error else CampaignStatus.completed
                await repo.set_fields(campaign_id, status=status, completed_at=_utcnow())
        log.info("campaign.engine.finalized", campaign_id=str(campaign_id))

    async def resume_running(self) -> None:
        """Re-launch campaigns left 'running' after an API restart."""
        async with session_scope() as s:
            ids = await CampaignRepository(s).running_campaign_ids()
        for cid in ids:
            await self.start(cid)
        if ids:
            log.info("campaign.engine.resumed_on_startup", count=len(ids))


# Module-level singleton.
engine = CampaignEngine()
