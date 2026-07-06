"""Analytics API — dashboard-ready aggregate JSON, fully tenant-scoped.

  GET /analytics/overview            headline KPIs over a rolling window
  GET /analytics/call-outcomes       outcome distribution (counts + %)
  GET /analytics/lead-sources        lead source distribution (counts + %)
  GET /analytics/conversion-trends   daily time series (zero-filled)

All windows default to the last 30 days (?days=1..365). Queries are set-based
and backed by the ix_calls_tenant_started / ix_leads_tenant_* composite indexes.
"""
from __future__ import annotations

from datetime import timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from priya.api.routers._common import period
from priya.api.schemas import (
    AnalyticsOverview,
    BreakdownItem,
    BreakdownResponse,
    ConversionTrendPoint,
    ConversionTrendsResponse,
)
from priya.auth.dependencies import CurrentUser, get_current_user, get_db
from priya.db.repositories import AnalyticsRepository
from priya.utils.logging import get_logger

router = APIRouter(prefix="/analytics", tags=["analytics"])
log = get_logger(__name__)


def _breakdown(period_days: int, rows: list[tuple[str, int]]) -> BreakdownResponse:
    total = sum(n for _, n in rows)
    items = [
        BreakdownItem(
            key=key,
            count=n,
            percentage=round(n / total * 100, 1) if total else 0.0,
        )
        for key, n in sorted(rows, key=lambda r: r[1], reverse=True)
    ]
    return BreakdownResponse(period_days=period_days, total=total, items=items)


@router.get("/overview", response_model=AnalyticsOverview)
async def analytics_overview(
    days: int = Query(default=30, ge=1, le=365),
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> AnalyticsOverview:
    start, end = period(days)
    data = await AnalyticsRepository(session).overview(user.tenant_id, start, end)
    return AnalyticsOverview(period_days=days, **data)


@router.get("/call-outcomes", response_model=BreakdownResponse)
async def analytics_call_outcomes(
    days: int = Query(default=30, ge=1, le=365),
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> BreakdownResponse:
    start, end = period(days)
    rows = await AnalyticsRepository(session).call_outcomes(user.tenant_id, start, end)
    return _breakdown(days, rows)


@router.get("/lead-sources", response_model=BreakdownResponse)
async def analytics_lead_sources(
    days: int = Query(default=30, ge=1, le=365),
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> BreakdownResponse:
    start, end = period(days)
    rows = await AnalyticsRepository(session).lead_sources(user.tenant_id, start, end)
    return _breakdown(days, rows)


@router.get("/conversion-trends", response_model=ConversionTrendsResponse)
async def analytics_conversion_trends(
    days: int = Query(default=30, ge=1, le=365),
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> ConversionTrendsResponse:
    start, end = period(days)
    buckets = await AnalyticsRepository(session).conversion_trends(user.tenant_id, start, end)

    # Zero-fill every day in the window so charts have a continuous x-axis.
    points: list[ConversionTrendPoint] = []
    cursor = start
    for _ in range(days):
        key = cursor.date().isoformat()
        b = buckets.get(key, {"calls": 0, "answered": 0, "site_visits": 0, "new_leads": 0})
        points.append(
            ConversionTrendPoint(
                date=key,
                calls=b["calls"],
                answered=b["answered"],
                site_visits=b["site_visits"],
                new_leads=b["new_leads"],
            )
        )
        cursor = cursor + timedelta(days=1)

    return ConversionTrendsResponse(period_days=days, points=points)
