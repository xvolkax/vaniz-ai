"""Dashboard summary API — a single tenant-scoped snapshot for the home screen.

GET /dashboard/summary returns headline KPIs (computed with conditional-aggregate
queries) plus three recent-activity feeds. Designed to load the whole dashboard
in a small, fixed number of index-backed queries.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from priya.api.routers._common import day_start, month_start, now_ist
from priya.api.routers.calls import _phone_for, _score_for
from priya.api.schemas import (
    CallListItem,
    DashboardSummary,
    LeadResponse,
    RecentAppointmentItem,
)
from priya.auth.dependencies import CurrentUser, get_current_user, get_db
from priya.db.repositories import (
    AnalyticsRepository,
    AppointmentRepository,
    CallRepository,
    LeadRepository,
)
from priya.utils.logging import get_logger

router = APIRouter(prefix="/dashboard", tags=["dashboard"])
log = get_logger(__name__)


@router.get("/summary", response_model=DashboardSummary)
async def dashboard_summary(
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> DashboardSummary:
    tid = user.tenant_id
    now = now_ist()
    today = day_start(now)
    mstart = month_start(now)

    analytics = AnalyticsRepository(session)
    calls = await analytics.call_summary(tid, today, mstart)
    leads = await analytics.lead_summary(tid)
    appts = await analytics.appointment_summary(tid, mstart)

    answered = calls["answered_calls"]
    site_visits = appts["site_visits_booked"]
    conversion_rate = round(site_visits / answered * 100, 1) if answered else 0.0

    # Recent activity feeds (each capped at 10).
    recent_call_rows = await CallRepository(session).list_filtered(tid, limit=10)
    recent_calls = [
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
        )
        for c in recent_call_rows
    ]

    recent_appt_rows = await AppointmentRepository(session).recent_with_lead(tid, limit=10)
    recent_appointments = [
        RecentAppointmentItem(
            id=a.id,
            lead_id=a.lead_id,
            lead_name=lead_name,
            type=a.type,
            status=a.status,
            scheduled_at=a.scheduled_at,
            location=a.location,
        )
        for a, lead_name in recent_appt_rows
    ]

    hot_lead_rows = await LeadRepository(session).list_filtered(
        tid, score_min=70, limit=10, sort_by="created_at", descending=True
    )
    recent_hot_leads = [LeadResponse.model_validate(lead) for lead in hot_lead_rows]

    return DashboardSummary(
        calls_today=calls["calls_today"],
        calls_this_month=calls["calls_this_month"],
        answered_calls=answered,
        interested_leads=leads["interested_leads"],
        site_visits_booked=site_visits,
        callback_requests=appts["callback_requests"],
        hot_leads=leads["hot_leads"],
        conversion_rate=conversion_rate,
        recent_calls=recent_calls,
        recent_appointments=recent_appointments,
        recent_hot_leads=recent_hot_leads,
    )
