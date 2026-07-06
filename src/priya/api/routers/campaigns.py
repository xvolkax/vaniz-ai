"""Campaigns API — create, populate, control, and analyze outbound campaigns.

  POST /campaigns                 create (optionally seed with lead_ids)
  GET  /campaigns                 list (paginated)
  GET  /campaigns/{id}            detail
  POST /campaigns/{id}/leads      add leads as targets
  POST /campaigns/{id}/start      draft/failed -> running
  POST /campaigns/{id}/pause      running -> paused
  POST /campaigns/{id}/resume     paused -> running
  POST /campaigns/{id}/stop       -> completed (remaining targets skipped)
  GET  /campaigns/{id}/analytics  campaign summary metrics

All operations are tenant-scoped via the JWT. Control endpoints drive the
in-process execution engine.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from priya.api.schemas import (
    AddLeadsRequest,
    AddLeadsResponse,
    CampaignAnalytics,
    CampaignCreate,
    CampaignListResponse,
    CampaignResponse,
)
from priya.auth.dependencies import CurrentUser, get_current_user, get_db, require_role
from priya.campaigns import engine
from priya.db.models import CampaignStatus, UserRole
from priya.db.repositories import CampaignRepository
from priya.utils.logging import get_logger

router = APIRouter(prefix="/campaigns", tags=["campaigns"])
log = get_logger(__name__)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


async def _load(
    repo: CampaignRepository, campaign_id: uuid.UUID, tenant_id: uuid.UUID
):
    campaign = await repo.get(campaign_id, tenant_id=tenant_id)
    if campaign is None:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return campaign


@router.post("", response_model=CampaignResponse, status_code=status.HTTP_201_CREATED)
async def create_campaign(
    payload: CampaignCreate,
    user: CurrentUser = Depends(require_role(UserRole.agent)),
    session: AsyncSession = Depends(get_db),
) -> CampaignResponse:
    if payload.working_hours_start == payload.working_hours_end and payload.working_hours_start != 0:
        # start==end is only meaningful as 0==0 (24x7); otherwise it's ambiguous.
        raise HTTPException(status_code=422, detail="working_hours_start and _end must differ")
    repo = CampaignRepository(session)
    campaign = await repo.create(
        user.tenant_id,
        name=payload.name,
        concurrency=payload.concurrency,
        max_attempts=payload.max_attempts,
        retry_delay_minutes=payload.retry_delay_minutes,
        working_hours_start=payload.working_hours_start,
        working_hours_end=payload.working_hours_end,
    )
    if payload.lead_ids:
        await repo.add_targets(campaign.id, user.tenant_id, payload.lead_ids)
    log.info("campaigns.create", tenant=str(user.tenant_id), campaign=str(campaign.id))
    return CampaignResponse.model_validate(campaign)


@router.get("", response_model=CampaignListResponse)
async def list_campaigns(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> CampaignListResponse:
    repo = CampaignRepository(session)
    rows = await repo.list(user.tenant_id, limit=limit, offset=offset)
    total = await repo.count(user.tenant_id)
    return CampaignListResponse(
        items=[CampaignResponse.model_validate(c) for c in rows],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{campaign_id}", response_model=CampaignResponse)
async def get_campaign(
    campaign_id: uuid.UUID,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> CampaignResponse:
    campaign = await _load(CampaignRepository(session), campaign_id, user.tenant_id)
    return CampaignResponse.model_validate(campaign)


@router.post("/{campaign_id}/leads", response_model=AddLeadsResponse)
async def add_leads(
    campaign_id: uuid.UUID,
    payload: AddLeadsRequest,
    user: CurrentUser = Depends(require_role(UserRole.agent)),
    session: AsyncSession = Depends(get_db),
) -> AddLeadsResponse:
    repo = CampaignRepository(session)
    campaign = await _load(repo, campaign_id, user.tenant_id)
    if campaign.status in (CampaignStatus.completed, CampaignStatus.failed):
        raise HTTPException(status_code=409, detail="Cannot add leads to a finished campaign")
    added = await repo.add_targets(campaign_id, user.tenant_id, payload.lead_ids)
    counts = await repo.target_status_counts(campaign_id)
    return AddLeadsResponse(added=added, total_targets=sum(counts.values()))


# --------------------------------------------------------------------------- #
# Lifecycle control
# --------------------------------------------------------------------------- #
@router.post("/{campaign_id}/start", response_model=CampaignResponse)
async def start_campaign(
    campaign_id: uuid.UUID,
    user: CurrentUser = Depends(require_role(UserRole.agent)),
    session: AsyncSession = Depends(get_db),
) -> CampaignResponse:
    repo = CampaignRepository(session)
    campaign = await _load(repo, campaign_id, user.tenant_id)
    if campaign.status not in (CampaignStatus.draft, CampaignStatus.failed):
        raise HTTPException(
            status_code=409, detail=f"Cannot start a campaign in '{campaign.status.value}' state"
        )
    if not await repo.has_pending(campaign_id):
        raise HTTPException(status_code=409, detail="Campaign has no pending targets")
    fields = {"status": CampaignStatus.running}
    if campaign.started_at is None:
        fields["started_at"] = _utcnow()
    campaign = await repo.set_fields(campaign_id, **fields)
    await session.commit()  # persist before engine reads it
    await engine.start(campaign_id)
    return CampaignResponse.model_validate(campaign)


@router.post("/{campaign_id}/pause", response_model=CampaignResponse)
async def pause_campaign(
    campaign_id: uuid.UUID,
    user: CurrentUser = Depends(require_role(UserRole.agent)),
    session: AsyncSession = Depends(get_db),
) -> CampaignResponse:
    repo = CampaignRepository(session)
    campaign = await _load(repo, campaign_id, user.tenant_id)
    if campaign.status != CampaignStatus.running:
        raise HTTPException(status_code=409, detail="Only a running campaign can be paused")
    campaign = await repo.set_fields(campaign_id, status=CampaignStatus.paused)
    await session.commit()
    await engine.pause(campaign_id)
    return CampaignResponse.model_validate(campaign)


@router.post("/{campaign_id}/resume", response_model=CampaignResponse)
async def resume_campaign(
    campaign_id: uuid.UUID,
    user: CurrentUser = Depends(require_role(UserRole.agent)),
    session: AsyncSession = Depends(get_db),
) -> CampaignResponse:
    repo = CampaignRepository(session)
    campaign = await _load(repo, campaign_id, user.tenant_id)
    if campaign.status != CampaignStatus.paused:
        raise HTTPException(status_code=409, detail="Only a paused campaign can be resumed")
    campaign = await repo.set_fields(campaign_id, status=CampaignStatus.running)
    await session.commit()
    await engine.resume(campaign_id)
    return CampaignResponse.model_validate(campaign)


@router.post("/{campaign_id}/stop", response_model=CampaignResponse)
async def stop_campaign(
    campaign_id: uuid.UUID,
    user: CurrentUser = Depends(require_role(UserRole.agent)),
    session: AsyncSession = Depends(get_db),
) -> CampaignResponse:
    repo = CampaignRepository(session)
    campaign = await _load(repo, campaign_id, user.tenant_id)
    if campaign.status in (CampaignStatus.completed, CampaignStatus.failed):
        raise HTTPException(status_code=409, detail="Campaign is already finished")
    await engine.stop(campaign_id)
    await repo.skip_remaining(campaign_id)
    campaign = await repo.set_fields(
        campaign_id, status=CampaignStatus.completed, completed_at=_utcnow()
    )
    return CampaignResponse.model_validate(campaign)


@router.get("/{campaign_id}/analytics", response_model=CampaignAnalytics)
async def campaign_analytics(
    campaign_id: uuid.UUID,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> CampaignAnalytics:
    repo = CampaignRepository(session)
    await _load(repo, campaign_id, user.tenant_id)
    data = await repo.analytics(campaign_id)
    return CampaignAnalytics(campaign_id=campaign_id, **data)
