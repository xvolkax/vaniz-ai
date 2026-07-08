"""Calls API — production-ready, fully tenant-scoped, dashboard-optimized.

Endpoints:
  GET /calls        list + search + filters + pagination + sorting
  GET /calls/{id}   full detail: transcript, AI summary, requirements, score,
                    next action, follow-up, appointment linkage, latency

Filters: created/started date range, outcome, duration range, lead_id, and a
future-safe campaign_id. The list is optimized with eager-loaded lead + summary
to avoid N+1 queries.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from priya.api.schemas import (
    ActiveCallItem,
    ActiveCallsResponse,
    AppointmentItem,
    CallDetailResponse,
    CallListItem,
    CallListResponse,
    LatencyMetrics,
    ListenTokenResponse,
    RecordingUrlResponse,
)
from priya.auth.dependencies import CurrentUser, get_current_user, get_db, require_role
from priya.config import settings
from priya.db.models import Call, CallDirection, CallOutcome, UserRole
from priya.db.repositories import AppointmentRepository, CallRepository
from priya.telephony.control import end_call, listen_token
from priya.telephony.recording import generate_presigned_get_url
from priya.utils.logging import get_logger

router = APIRouter(prefix="/calls", tags=["calls"])
log = get_logger(__name__)

_SORT_FIELDS = {"started_at", "ended_at", "duration_seconds", "qualification_score"}


def _phone_for(call: Call) -> str | None:
    """The counterparty (lead) number for display."""
    if call.lead is not None and call.lead.phone_number:
        return call.lead.phone_number
    if call.direction == CallDirection.outbound:
        return call.to_number
    return call.from_number


def _score_for(call: Call) -> int | None:
    if call.summary is not None and call.summary.qualification_score is not None:
        return call.summary.qualification_score
    return call.lead.qualification_score if call.lead is not None else None


def _filters(
    date_from: datetime | None,
    date_to: datetime | None,
    outcome: CallOutcome | None,
    duration_min: float | None,
    duration_max: float | None,
    lead_id: uuid.UUID | None,
    campaign_id: uuid.UUID | None,
    search: str | None,
) -> dict:
    return {
        "date_from": date_from,
        "date_to": date_to,
        "outcome": outcome,
        "duration_min": duration_min,
        "duration_max": duration_max,
        "lead_id": lead_id,
        "campaign_id": campaign_id,
        "search": search,
    }


@router.get("", response_model=CallListResponse)
async def list_calls(
    date_from: datetime | None = Query(default=None, description="started_at >= (ISO 8601)"),
    date_to: datetime | None = Query(default=None, description="started_at <= (ISO 8601)"),
    outcome: CallOutcome | None = Query(default=None),
    duration_min: float | None = Query(default=None, ge=0, description="min duration (seconds)"),
    duration_max: float | None = Query(default=None, ge=0, description="max duration (seconds)"),
    lead_id: uuid.UUID | None = Query(default=None),
    campaign_id: uuid.UUID | None = Query(default=None),
    search: str | None = Query(default=None, max_length=120),
    sort_by: str = Query(default="started_at"),
    order: str = Query(default="desc", pattern="^(asc|desc)$"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> CallListResponse:
    if sort_by not in _SORT_FIELDS:
        raise HTTPException(
            status_code=422, detail=f"sort_by must be one of {sorted(_SORT_FIELDS)}"
        )
    filters = _filters(
        date_from, date_to, outcome, duration_min, duration_max, lead_id, campaign_id, search
    )
    repo = CallRepository(session)
    rows = await repo.list_filtered(
        user.tenant_id,
        limit=limit,
        offset=offset,
        sort_by=sort_by,
        descending=(order == "desc"),
        **filters,
    )
    total = await repo.count_filtered(user.tenant_id, **filters)
    items = [
        CallListItem(
            id=c.id,
            lead_id=c.lead_id,
            lead_name=c.lead.name if c.lead is not None else None,
            phone_number=_phone_for(c),
            direction=c.direction,
            call_date=c.started_at,
            duration_seconds=c.duration_seconds,
            outcome=c.outcome,
            qualification_score=_score_for(c),
            has_recording=c.recording_key is not None,
        )
        for c in rows
    ]
    return CallListResponse(items=items, total=total, limit=limit, offset=offset)


# --------------------------------------------------------------------------- #
# Live calls (declared before /{call_id} so "active" isn't parsed as an id)
# --------------------------------------------------------------------------- #
@router.get("/active", response_model=ActiveCallsResponse)
async def list_active_calls(
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> ActiveCallsResponse:
    rows = await CallRepository(session).list_active(user.tenant_id)
    return ActiveCallsResponse(
        items=[
            ActiveCallItem(
                id=c.id,
                lead_id=c.lead_id,
                lead_name=c.lead.name if c.lead is not None else None,
                phone_number=_phone_for(c),
                direction=c.direction,
                started_at=c.started_at,
            )
            for c in rows
        ]
    )


@router.post("/{call_id}/hangup", status_code=status.HTTP_204_NO_CONTENT)
async def hangup_call(
    call_id: uuid.UUID,
    user: CurrentUser = Depends(require_role(UserRole.agent)),
    session: AsyncSession = Depends(get_db),
) -> None:
    call = await CallRepository(session).get(call_id)
    if call is None or call.tenant_id != user.tenant_id:
        raise HTTPException(status_code=404, detail="Call not found")
    if not call.room_name:
        raise HTTPException(status_code=409, detail="Call is not live")
    try:
        await end_call(call.room_name)
    except Exception as exc:  # noqa: BLE001
        log.error("calls.hangup.error", error=str(exc))
        raise HTTPException(status_code=502, detail="Failed to end call") from exc


@router.post("/{call_id}/listen-token", response_model=ListenTokenResponse)
async def get_listen_token(
    call_id: uuid.UUID,
    user: CurrentUser = Depends(require_role(UserRole.agent)),
    session: AsyncSession = Depends(get_db),
) -> ListenTokenResponse:
    call = await CallRepository(session).get(call_id)
    if call is None or call.tenant_id != user.tenant_id:
        raise HTTPException(status_code=404, detail="Call not found")
    if not call.room_name:
        raise HTTPException(status_code=409, detail="Call is not live")
    try:
        token = listen_token(call.room_name, identity=f"supervisor-{user.id}")
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return ListenTokenResponse(url=settings.livekit_url, token=token, room=call.room_name)


@router.get("/{call_id}/recording")
async def get_call_recording(
    call_id: uuid.UUID,
    redirect: bool = Query(
        default=False,
        description="If true, 302-redirect to the presigned URL instead of returning JSON.",
    ),
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Return a short-lived presigned URL to play/download the call recording.

    Security:
      * Authenticated (any tenant user, same as call detail/list access).
      * Tenant-scoped lookup prevents IDOR — a call from another tenant returns
        404 (indistinguishable from "not found"), so IDs can't be enumerated.
      * The bucket stays private; only a time-boxed presigned GET URL is exposed.
        Access keys/secrets are never sent to the client.

    Responses:
      * 200 JSON {url, expires_in}  (default; consumed by the SPA)
      * 302 redirect to the presigned URL when ?redirect=true
      * 404 if the call doesn't exist, isn't in the caller's tenant, or has no
            recording yet (not ready / not enabled)
      * 503 if recording storage isn't configured or presigning failed
    """
    # Tenant-scoped query → authorization enforced at the SQL layer (same pattern
    # as GET /calls/{id}). Missing OR cross-tenant both yield None => identical 404.
    call = await CallRepository(session).get_detail(call_id, tenant_id=user.tenant_id)
    if call is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Call not found")

    if not call.recording_key:
        # No recording captured (not enabled, still processing, or never made).
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Recording not available"
        )

    url = generate_presigned_get_url(call.recording_key)
    if not url:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Recording storage not configured",
        )

    if redirect:
        return RedirectResponse(url=url, status_code=status.HTTP_302_FOUND)
    return RecordingUrlResponse(url=url, expires_in=settings.recording_url_ttl_seconds)


@router.get("/{call_id}", response_model=CallDetailResponse)
async def get_call(
    call_id: uuid.UUID,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> CallDetailResponse:
    call = await CallRepository(session).get_detail(call_id, tenant_id=user.tenant_id)
    if call is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Call not found")

    summary = call.summary
    appointments: list[AppointmentItem] = []
    if call.lead_id is not None:
        appts = await AppointmentRepository(session).list_for_lead(call.lead_id)
        appointments = [AppointmentItem.model_validate(a) for a in appts]

    return CallDetailResponse(
        id=call.id,
        tenant_id=call.tenant_id,
        lead_id=call.lead_id,
        lead_name=call.lead.name if call.lead is not None else None,
        phone_number=_phone_for(call),
        campaign_id=call.campaign_id,
        direction=call.direction,
        room_name=call.room_name,
        from_number=call.from_number,
        to_number=call.to_number,
        started_at=call.started_at,
        ended_at=call.ended_at,
        duration_seconds=call.duration_seconds,
        outcome=call.outcome,
        final_state=call.final_state,
        has_recording=call.recording_key is not None,
        transcript=summary.transcript if summary else None,
        summary=summary.summary if summary else None,
        key_requirements=summary.key_requirements if summary else None,
        qualification_score=(
            summary.qualification_score if summary else None
        ) or (call.lead.qualification_score if call.lead else None),
        recommended_next_action=summary.recommended_next_action if summary else None,
        follow_up_recommendation=summary.follow_up_recommendation if summary else None,
        appointments=appointments,
        latency=LatencyMetrics(
            avg_stt_latency_ms=call.avg_stt_latency_ms,
            avg_llm_latency_ms=call.avg_llm_latency_ms,
            avg_tts_latency_ms=call.avg_tts_latency_ms,
            avg_e2e_latency_ms=call.avg_e2e_latency_ms,
            user_interruptions=call.user_interruptions,
        ),
    )
