"""Async repositories — the only place that talks to the ORM.

Repositories keep DB access off the audio hot-path by exposing small, awaitable
methods. All writes are idempotent-friendly (upsert-by-phone for leads).
"""
from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import Select, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from priya.db.models import (
    Appointment,
    AppointmentType,
    AuditLog,
    Call,
    CallOutcome,
    Campaign,
    CampaignStatus,
    CampaignTarget,
    ConversationSummary,
    Lead,
    LeadSource,
    LeadStatus,
    Property,
    PropertyType,
    TargetStatus,
    Tenant,
    User,
)
from priya.utils.logging import get_logger

log = get_logger(__name__)

# Fields that must NOT be overwritten on an upsert-update (first value wins).
_UPSERT_IMMUTABLE = {"source"}

# Whitelisted sort columns for the leads list endpoint.
_LEAD_SORT_COLUMNS = {
    "created_at": Lead.created_at,
    "updated_at": Lead.updated_at,
    "qualification_score": Lead.qualification_score,
    "name": Lead.name,
}


class LeadRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_phone(
        self, phone_number: str, tenant_id: uuid.UUID | None = None
    ) -> Lead | None:
        stmt = select(Lead).where(Lead.phone_number == phone_number)
        if tenant_id is not None:
            stmt = stmt.where(Lead.tenant_id == tenant_id)
        res = await self.session.execute(stmt.order_by(Lead.created_at.desc()))
        return res.scalars().first()

    async def get(self, lead_id: uuid.UUID, tenant_id: uuid.UUID | None = None) -> Lead | None:
        lead = await self.session.get(Lead, lead_id)
        if lead is None:
            return None
        if tenant_id is not None and lead.tenant_id != tenant_id:
            return None
        return lead

    # ----------------------------------------------------------------- #
    # Filtered querying (list / count / export share one filter builder)
    # ----------------------------------------------------------------- #
    @staticmethod
    def _apply_filters(
        stmt: Select,
        tenant_id: uuid.UUID,
        *,
        status: LeadStatus | None = None,
        source: LeadSource | None = None,
        score_min: int | None = None,
        score_max: int | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        search: str | None = None,
    ) -> Select:
        stmt = stmt.where(Lead.tenant_id == tenant_id)
        if status is not None:
            stmt = stmt.where(Lead.status == status)
        if source is not None:
            stmt = stmt.where(Lead.source == source)
        if score_min is not None:
            stmt = stmt.where(Lead.qualification_score >= score_min)
        if score_max is not None:
            stmt = stmt.where(Lead.qualification_score <= score_max)
        if date_from is not None:
            stmt = stmt.where(Lead.created_at >= date_from)
        if date_to is not None:
            stmt = stmt.where(Lead.created_at <= date_to)
        if search:
            like = f"%{search.strip()}%"
            stmt = stmt.where(
                or_(
                    Lead.name.ilike(like),
                    Lead.phone_number.ilike(like),
                    Lead.city.ilike(like),
                    Lead.preferred_location.ilike(like),
                )
            )
        return stmt

    async def list_filtered(
        self,
        tenant_id: uuid.UUID,
        *,
        limit: int = 50,
        offset: int = 0,
        sort_by: str = "created_at",
        descending: bool = True,
        **filters: Any,
    ) -> list[Lead]:
        stmt = self._apply_filters(select(Lead), tenant_id, **filters)
        col = _LEAD_SORT_COLUMNS.get(sort_by, Lead.created_at)
        stmt = stmt.order_by(col.desc() if descending else col.asc())
        stmt = stmt.limit(limit).offset(offset)
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def count_filtered(self, tenant_id: uuid.UUID, **filters: Any) -> int:
        stmt = self._apply_filters(
            select(func.count()).select_from(Lead), tenant_id, **filters
        )
        res = await self.session.execute(stmt)
        return int(res.scalar() or 0)

    async def stream_filtered(
        self, tenant_id: uuid.UUID, *, chunk: int = 500, **filters: Any
    ) -> Sequence[Lead]:
        """Fetch all matching leads (ordered) for CSV export."""
        stmt = self._apply_filters(select(Lead), tenant_id, **filters).order_by(
            Lead.created_at.desc()
        )
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    # Backwards-compatible simple list (used elsewhere).
    async def list(
        self,
        tenant_id: uuid.UUID,
        *,
        status: LeadStatus | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Lead]:
        return await self.list_filtered(
            tenant_id, status=status, limit=limit, offset=offset
        )

    async def create(self, tenant_id: uuid.UUID, **fields: Any) -> Lead:
        lead = Lead(tenant_id=tenant_id, **fields)
        self.session.add(lead)
        await self.session.flush()
        return lead

    async def upsert_by_phone(
        self, phone_number: str, tenant_id: uuid.UUID | None = None, **fields: Any
    ) -> Lead:
        lead = await self.get_by_phone(phone_number, tenant_id=tenant_id)
        if lead is None:
            lead = Lead(phone_number=phone_number, tenant_id=tenant_id, **fields)
            self.session.add(lead)
        else:
            for key, value in fields.items():
                # Preserve first-seen values for immutable attribution fields.
                if key in _UPSERT_IMMUTABLE:
                    continue
                if value is not None:
                    setattr(lead, key, value)
        await self.session.flush()
        return lead

    async def update(
        self, lead_id: uuid.UUID, tenant_id: uuid.UUID | None = None, **fields: Any
    ) -> Lead | None:
        lead = await self.get(lead_id, tenant_id=tenant_id)
        if lead is None:
            return None
        for key, value in fields.items():
            if value is not None:
                setattr(lead, key, value)
        await self.session.flush()
        return lead

    async def delete(self, lead_id: uuid.UUID, tenant_id: uuid.UUID | None = None) -> bool:
        lead = await self.get(lead_id, tenant_id=tenant_id)
        if lead is None:
            return False
        await self.session.delete(lead)
        await self.session.flush()
        return True

    async def set_status(self, lead_id: uuid.UUID, status: LeadStatus) -> None:
        lead = await self.get(lead_id)
        if lead:
            lead.status = status
            await self.session.flush()


class CallRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, **fields: Any) -> Call:
        call = Call(**fields)
        self.session.add(call)
        await self.session.flush()
        return call

    async def get(self, call_id: uuid.UUID) -> Call | None:
        return await self.session.get(Call, call_id)

    async def get_detail(
        self, call_id: uuid.UUID, tenant_id: uuid.UUID | None = None
    ) -> Call | None:
        """Fetch a call with its lead + summary eagerly loaded (tenant-scoped)."""
        stmt = (
            select(Call)
            .where(Call.id == call_id)
            .options(selectinload(Call.lead), selectinload(Call.summary))
        )
        if tenant_id is not None:
            stmt = stmt.where(Call.tenant_id == tenant_id)
        res = await self.session.execute(stmt)
        return res.scalars().first()

    async def list_for_lead(self, lead_id: uuid.UUID) -> list[Call]:
        res = await self.session.execute(
            select(Call).where(Call.lead_id == lead_id).order_by(Call.started_at.desc())
        )
        return list(res.scalars().all())

    async def list_active(self, tenant_id: uuid.UUID) -> list[Call]:
        """In-progress calls: started but not yet ended (tenant-scoped)."""
        res = await self.session.execute(
            select(Call)
            .where(Call.tenant_id == tenant_id, Call.ended_at.is_(None))
            .options(selectinload(Call.lead))
            .order_by(Call.started_at.desc())
        )
        return list(res.scalars().all())

    async def set_recording_url(self, call_id: uuid.UUID, url: str) -> None:
        call = await self.get(call_id)
        if call is not None:
            call.recording_url = url
            await self.session.flush()

    # ----------------------------------------------------------------- #
    # Filtered querying for the dashboard list (tenant-scoped)
    # ----------------------------------------------------------------- #
    @staticmethod
    def _build_conditions(
        tenant_id: uuid.UUID,
        *,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        outcome: CallOutcome | None = None,
        duration_min: float | None = None,
        duration_max: float | None = None,
        lead_id: uuid.UUID | None = None,
        campaign_id: uuid.UUID | None = None,
        search: str | None = None,
    ) -> tuple[list, bool]:
        conds: list = [Call.tenant_id == tenant_id]
        if date_from is not None:
            conds.append(Call.started_at >= date_from)
        if date_to is not None:
            conds.append(Call.started_at <= date_to)
        if outcome is not None:
            conds.append(Call.outcome == outcome)
        if duration_min is not None:
            conds.append(Call.duration_seconds >= duration_min)
        if duration_max is not None:
            conds.append(Call.duration_seconds <= duration_max)
        if lead_id is not None:
            conds.append(Call.lead_id == lead_id)
        if campaign_id is not None:
            conds.append(Call.campaign_id == campaign_id)
        needs_lead_join = False
        if search:
            like = f"%{search.strip()}%"
            conds.append(
                or_(
                    Lead.name.ilike(like),
                    Lead.phone_number.ilike(like),
                    Call.from_number.ilike(like),
                    Call.to_number.ilike(like),
                    Call.room_name.ilike(like),
                )
            )
            needs_lead_join = True
        return conds, needs_lead_join

    async def list_filtered(
        self,
        tenant_id: uuid.UUID,
        *,
        limit: int = 50,
        offset: int = 0,
        sort_by: str = "started_at",
        descending: bool = True,
        **filters: Any,
    ) -> list[Call]:
        conds, needs_lead_join = self._build_conditions(tenant_id, **filters)
        stmt = select(Call)
        if needs_lead_join or sort_by == "qualification_score":
            stmt = stmt.outerjoin(Lead, Call.lead_id == Lead.id)
        if sort_by == "qualification_score":
            stmt = stmt.outerjoin(ConversationSummary, ConversationSummary.call_id == Call.id)
        stmt = stmt.where(*conds).options(
            selectinload(Call.lead), selectinload(Call.summary)
        )
        sort_map = {
            "started_at": Call.started_at,
            "ended_at": Call.ended_at,
            "duration_seconds": Call.duration_seconds,
            "qualification_score": ConversationSummary.qualification_score,
        }
        col = sort_map.get(sort_by, Call.started_at)
        stmt = stmt.order_by(col.desc() if descending else col.asc())
        stmt = stmt.limit(limit).offset(offset)
        res = await self.session.execute(stmt)
        return list(res.scalars().unique().all())

    async def count_filtered(self, tenant_id: uuid.UUID, **filters: Any) -> int:
        conds, needs_lead_join = self._build_conditions(tenant_id, **filters)
        stmt = select(func.count(Call.id))
        if needs_lead_join:
            stmt = stmt.outerjoin(Lead, Call.lead_id == Lead.id)
        stmt = stmt.where(*conds)
        res = await self.session.execute(stmt)
        return int(res.scalar() or 0)

    async def finalize(self, call_id: uuid.UUID, **fields: Any) -> Call | None:
        call = await self.get(call_id)
        if call is None:
            return None
        ended = fields.pop("ended_at", datetime.now(timezone.utc))
        call.ended_at = ended
        if call.started_at:
            started = call.started_at
            if started.tzinfo is None:
                started = started.replace(tzinfo=timezone.utc)
            call.duration_seconds = (ended - started).total_seconds()
        for key, value in fields.items():
            if value is not None:
                setattr(call, key, value)
        await self.session.flush()
        return call


class SummaryRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, call_id: uuid.UUID, **fields: Any) -> ConversationSummary:
        summary = ConversationSummary(call_id=call_id, **fields)
        self.session.add(summary)
        await self.session.flush()
        return summary


class AppointmentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, **fields: Any) -> Appointment:
        appt = Appointment(**fields)
        self.session.add(appt)
        await self.session.flush()
        return appt

    async def list_for_lead(self, lead_id: uuid.UUID) -> list[Appointment]:
        res = await self.session.execute(
            select(Appointment)
            .where(Appointment.lead_id == lead_id)
            .order_by(Appointment.scheduled_at.desc())
        )
        return list(res.scalars().all())

    async def recent_with_lead(
        self, tenant_id: uuid.UUID, limit: int = 10
    ) -> list[tuple[Appointment, str | None]]:
        """Most recently booked appointments joined to lead name (tenant-scoped)."""
        res = await self.session.execute(
            select(Appointment, Lead.name)
            .outerjoin(Lead, Appointment.lead_id == Lead.id)
            .where(Appointment.tenant_id == tenant_id)
            .order_by(Appointment.created_at.desc())
            .limit(limit)
        )
        return [(row[0], row[1]) for row in res.all()]

    async def list_between(self, start: datetime, end: datetime) -> list[Appointment]:
        res = await self.session.execute(
            select(Appointment).where(
                Appointment.scheduled_at >= start, Appointment.scheduled_at < end
            )
        )
        return list(res.scalars().all())


class AuditRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def log(self, action: str, **fields: Any) -> None:
        entry = AuditLog(action=action, **fields)
        self.session.add(entry)
        await self.session.flush()


# --------------------------------------------------------------------------- #
# Multi-tenant repositories (control-plane / dashboard)
# --------------------------------------------------------------------------- #
class TenantRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, tenant_id: uuid.UUID) -> Tenant | None:
        return await self.session.get(Tenant, tenant_id)

    async def get_by_slug(self, slug: str) -> Tenant | None:
        res = await self.session.execute(select(Tenant).where(Tenant.slug == slug))
        return res.scalars().first()

    async def get_by_phone(self, phone_number: str) -> Tenant | None:
        res = await self.session.execute(
            select(Tenant).where(Tenant.phone_number == phone_number, Tenant.is_active.is_(True))
        )
        return res.scalars().first()

    async def create(self, **fields: Any) -> Tenant:
        tenant = Tenant(**fields)
        self.session.add(tenant)
        await self.session.flush()
        return tenant

    async def update(self, tenant_id: uuid.UUID, **fields: Any) -> Tenant | None:
        tenant = await self.get(tenant_id)
        if tenant is None:
            return None
        for key, value in fields.items():
            setattr(tenant, key, value)
        await self.session.flush()
        return tenant


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, user_id: uuid.UUID) -> User | None:
        return await self.session.get(User, user_id)

    async def get_by_email(self, email: str) -> User | None:
        res = await self.session.execute(select(User).where(User.email == email.lower()))
        return res.scalars().first()

    async def list_for_tenant(self, tenant_id: uuid.UUID) -> list[User]:
        res = await self.session.execute(
            select(User).where(User.tenant_id == tenant_id).order_by(User.created_at)
        )
        return list(res.scalars().all())

    async def create(self, **fields: Any) -> User:
        if "email" in fields and fields["email"]:
            fields["email"] = fields["email"].lower()
        user = User(**fields)
        self.session.add(user)
        await self.session.flush()
        return user

    async def update(self, user_id: uuid.UUID, **fields: Any) -> User | None:
        user = await self.get(user_id)
        if user is None:
            return None
        for key, value in fields.items():
            if value is not None:
                setattr(user, key, value)
        await self.session.flush()
        return user

    async def delete(self, user_id: uuid.UUID) -> bool:
        user = await self.get(user_id)
        if user is None:
            return False
        await self.session.delete(user)
        await self.session.flush()
        return True


class PropertyRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(
        self, property_id: uuid.UUID, tenant_id: uuid.UUID | None = None
    ) -> Property | None:
        prop = await self.session.get(Property, property_id)
        if prop is None:
            return None
        if tenant_id is not None and prop.tenant_id != tenant_id:
            return None
        return prop

    async def list(
        self,
        tenant_id: uuid.UUID,
        *,
        active_only: bool = False,
        limit: int = 200,
        offset: int = 0,
    ) -> list[Property]:
        stmt = select(Property).where(Property.tenant_id == tenant_id)
        if active_only:
            stmt = stmt.where(Property.is_active.is_(True))
        stmt = stmt.order_by(Property.created_at.desc()).limit(limit).offset(offset)
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def search(
        self,
        tenant_id: uuid.UUID,
        *,
        property_type: PropertyType | None = None,
        location: str | None = None,
        budget_max: float | None = None,
        limit: int = 5,
    ) -> list[Property]:
        """Structured lookup used by the agent during a call."""
        stmt = select(Property).where(
            Property.tenant_id == tenant_id, Property.is_active.is_(True)
        )
        if property_type is not None:
            stmt = stmt.where(Property.property_type == property_type)
        if location:
            stmt = stmt.where(Property.location.ilike(f"%{location}%"))
        if budget_max is not None:
            # Keep projects whose entry price is within (or unknown vs) budget.
            stmt = stmt.where(
                (Property.price_min.is_(None)) | (Property.price_min <= budget_max * 1.1)
            )
        res = await self.session.execute(stmt.limit(limit))
        return list(res.scalars().all())

    async def create(self, **fields: Any) -> Property:
        prop = Property(**fields)
        self.session.add(prop)
        await self.session.flush()
        return prop

    async def update(self, property_id: uuid.UUID, **fields: Any) -> Property | None:
        prop = await self.get(property_id)
        if prop is None:
            return None
        for key, value in fields.items():
            setattr(prop, key, value)
        await self.session.flush()
        return prop

    async def delete(self, property_id: uuid.UUID) -> bool:
        prop = await self.get(property_id)
        if prop is None:
            return False
        await self.session.delete(prop)
        await self.session.flush()
        return True

    async def count(self, tenant_id: uuid.UUID) -> int:
        res = await self.session.execute(
            select(func.count()).select_from(Property).where(Property.tenant_id == tenant_id)
        )
        return int(res.scalar() or 0)


class AnalyticsRepository:
    """Read-only aggregate queries for dashboard + analytics.

    Every method is tenant-scoped and uses set-based aggregation (COUNT/AVG with
    conditional FILTER, GROUP BY, date_trunc) so a dashboard load is a handful of
    index-backed queries rather than row scans. Backed by the composite indexes
    ix_calls_tenant_started / ix_leads_tenant_* / ix_appointments_tenant_*.
    """

    # Outcomes considered "answered" (a human picked up and talked).
    _ANSWERED = (
        CallOutcome.completed,
        CallOutcome.not_interested,
        CallOutcome.callback_requested,
        CallOutcome.transfer_requested,
    )
    _HOT_SCORE = 70
    _INTERESTED_STATUSES = (LeadStatus.qualifying, LeadStatus.qualified, LeadStatus.booked)

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # ------------------------------------------------------------------ #
    # Dashboard summary
    # ------------------------------------------------------------------ #
    async def call_summary(
        self, tenant_id: uuid.UUID, today_start: datetime, month_start: datetime
    ) -> dict:
        """One scan → calls_today, calls_this_month, answered_this_month."""
        stmt = select(
            func.count().filter(Call.started_at >= today_start).label("calls_today"),
            func.count().filter(Call.started_at >= month_start).label("calls_this_month"),
            func.count()
            .filter(Call.started_at >= month_start, Call.outcome.in_(self._ANSWERED))
            .label("answered_calls"),
        ).where(Call.tenant_id == tenant_id)
        row = (await self.session.execute(stmt)).one()
        return {
            "calls_today": int(row.calls_today or 0),
            "calls_this_month": int(row.calls_this_month or 0),
            "answered_calls": int(row.answered_calls or 0),
        }

    async def lead_summary(self, tenant_id: uuid.UUID) -> dict:
        """One scan → interested_leads, hot_leads (current pipeline state)."""
        stmt = select(
            func.count()
            .filter(Lead.status.in_(self._INTERESTED_STATUSES))
            .label("interested_leads"),
            func.count()
            .filter(Lead.qualification_score >= self._HOT_SCORE)
            .label("hot_leads"),
        ).where(Lead.tenant_id == tenant_id)
        row = (await self.session.execute(stmt)).one()
        return {
            "interested_leads": int(row.interested_leads or 0),
            "hot_leads": int(row.hot_leads or 0),
        }

    async def appointment_summary(self, tenant_id: uuid.UUID, month_start: datetime) -> dict:
        """One scan → site_visits_booked, callback_requests (booked this month)."""
        stmt = select(
            func.count()
            .filter(Appointment.type == AppointmentType.site_visit)
            .label("site_visits"),
            func.count()
            .filter(Appointment.type == AppointmentType.callback)
            .label("callbacks"),
        ).where(Appointment.tenant_id == tenant_id, Appointment.created_at >= month_start)
        row = (await self.session.execute(stmt)).one()
        return {
            "site_visits_booked": int(row.site_visits or 0),
            "callback_requests": int(row.callbacks or 0),
        }

    # ------------------------------------------------------------------ #
    # Analytics — overview over a [start, end) window
    # ------------------------------------------------------------------ #
    async def overview(self, tenant_id: uuid.UUID, start: datetime, end: datetime) -> dict:
        call_row = (
            await self.session.execute(
                select(
                    func.count().label("total_calls"),
                    func.count().filter(Call.outcome.in_(self._ANSWERED)).label("answered"),
                    func.avg(Call.duration_seconds).label("avg_duration"),
                    func.avg(Call.avg_e2e_latency_ms).label("avg_e2e"),
                ).where(
                    Call.tenant_id == tenant_id,
                    Call.started_at >= start,
                    Call.started_at < end,
                )
            )
        ).one()

        lead_row = (
            await self.session.execute(
                select(
                    func.count().label("total_leads"),
                    func.count()
                    .filter(Lead.status.in_((LeadStatus.qualified, LeadStatus.booked)))
                    .label("qualified"),
                    func.count()
                    .filter(Lead.qualification_score >= self._HOT_SCORE)
                    .label("hot"),
                    func.avg(Lead.qualification_score).label("avg_score"),
                ).where(
                    Lead.tenant_id == tenant_id,
                    Lead.created_at >= start,
                    Lead.created_at < end,
                )
            )
        ).one()

        appt_row = (
            await self.session.execute(
                select(
                    func.count()
                    .filter(Appointment.type == AppointmentType.site_visit)
                    .label("site_visits"),
                    func.count()
                    .filter(Appointment.type == AppointmentType.callback)
                    .label("callbacks"),
                ).where(
                    Appointment.tenant_id == tenant_id,
                    Appointment.created_at >= start,
                    Appointment.created_at < end,
                )
            )
        ).one()

        total_calls = int(call_row.total_calls or 0)
        answered = int(call_row.answered or 0)
        site_visits = int(appt_row.site_visits or 0)
        return {
            "total_calls": total_calls,
            "answered_calls": answered,
            "answer_rate": round(answered / total_calls * 100, 1) if total_calls else 0.0,
            "avg_call_duration_seconds": round(float(call_row.avg_duration), 1)
            if call_row.avg_duration is not None
            else None,
            "avg_e2e_latency_ms": round(float(call_row.avg_e2e), 1)
            if call_row.avg_e2e is not None
            else None,
            "total_leads": int(lead_row.total_leads or 0),
            "qualified_leads": int(lead_row.qualified or 0),
            "hot_leads": int(lead_row.hot or 0),
            "avg_qualification_score": round(float(lead_row.avg_score), 1)
            if lead_row.avg_score is not None
            else None,
            "site_visits": site_visits,
            "callbacks": int(appt_row.callbacks or 0),
            "conversion_rate": round(site_visits / answered * 100, 1) if answered else 0.0,
        }

    async def call_outcomes(
        self, tenant_id: uuid.UUID, start: datetime, end: datetime
    ) -> list[tuple[str, int]]:
        rows = await self.session.execute(
            select(Call.outcome, func.count().label("n"))
            .where(
                Call.tenant_id == tenant_id,
                Call.started_at >= start,
                Call.started_at < end,
            )
            .group_by(Call.outcome)
        )
        return [((o.value if o is not None else "unknown"), int(n)) for o, n in rows.all()]

    async def lead_sources(
        self, tenant_id: uuid.UUID, start: datetime, end: datetime
    ) -> list[tuple[str, int]]:
        rows = await self.session.execute(
            select(Lead.source, func.count().label("n"))
            .where(
                Lead.tenant_id == tenant_id,
                Lead.created_at >= start,
                Lead.created_at < end,
            )
            .group_by(Lead.source)
        )
        return [((s.value if s is not None else "unknown"), int(n)) for s, n in rows.all()]

    async def conversion_trends(
        self, tenant_id: uuid.UUID, start: datetime, end: datetime
    ) -> dict[str, dict]:
        """Daily buckets keyed by ISO date → {calls, answered, site_visits, new_leads}."""
        buckets: dict[str, dict] = {}

        def _key(dt: datetime) -> str:
            return dt.date().isoformat()

        call_day = func.date_trunc("day", Call.started_at)
        call_rows = await self.session.execute(
            select(
                call_day.label("d"),
                func.count().label("calls"),
                func.count().filter(Call.outcome.in_(self._ANSWERED)).label("answered"),
            )
            .where(
                Call.tenant_id == tenant_id,
                Call.started_at >= start,
                Call.started_at < end,
            )
            .group_by(call_day)
        )
        for d, calls, answered in call_rows.all():
            b = buckets.setdefault(_key(d), {"calls": 0, "answered": 0, "site_visits": 0, "new_leads": 0})
            b["calls"] = int(calls)
            b["answered"] = int(answered)

        appt_day = func.date_trunc("day", Appointment.created_at)
        appt_rows = await self.session.execute(
            select(appt_day.label("d"), func.count().label("n"))
            .where(
                Appointment.tenant_id == tenant_id,
                Appointment.type == AppointmentType.site_visit,
                Appointment.created_at >= start,
                Appointment.created_at < end,
            )
            .group_by(appt_day)
        )
        for d, n in appt_rows.all():
            b = buckets.setdefault(_key(d), {"calls": 0, "answered": 0, "site_visits": 0, "new_leads": 0})
            b["site_visits"] = int(n)

        lead_day = func.date_trunc("day", Lead.created_at)
        lead_rows = await self.session.execute(
            select(lead_day.label("d"), func.count().label("n"))
            .where(
                Lead.tenant_id == tenant_id,
                Lead.created_at >= start,
                Lead.created_at < end,
            )
            .group_by(lead_day)
        )
        for d, n in lead_rows.all():
            b = buckets.setdefault(_key(d), {"calls": 0, "answered": 0, "site_visits": 0, "new_leads": 0})
            b["new_leads"] = int(n)

        return buckets


class CampaignRepository:
    """Campaigns + their targets. Target claiming uses row locks so multiple
    engine workers (or replicas) never dial the same target twice."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # ---- Campaign CRUD ----
    async def create(self, tenant_id: uuid.UUID, **fields: Any) -> Campaign:
        campaign = Campaign(tenant_id=tenant_id, **fields)
        self.session.add(campaign)
        await self.session.flush()
        return campaign

    async def get(self, campaign_id: uuid.UUID, tenant_id: uuid.UUID | None = None) -> Campaign | None:
        c = await self.session.get(Campaign, campaign_id)
        if c is None:
            return None
        if tenant_id is not None and c.tenant_id != tenant_id:
            return None
        return c

    async def list(
        self, tenant_id: uuid.UUID, *, limit: int = 50, offset: int = 0
    ) -> list[Campaign]:
        res = await self.session.execute(
            select(Campaign)
            .where(Campaign.tenant_id == tenant_id)
            .order_by(Campaign.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(res.scalars().all())

    async def count(self, tenant_id: uuid.UUID) -> int:
        res = await self.session.execute(
            select(func.count()).select_from(Campaign).where(Campaign.tenant_id == tenant_id)
        )
        return int(res.scalar() or 0)

    async def set_fields(self, campaign_id: uuid.UUID, **fields: Any) -> Campaign | None:
        c = await self.session.get(Campaign, campaign_id)
        if c is None:
            return None
        for key, value in fields.items():
            setattr(c, key, value)
        await self.session.flush()
        return c

    # ---- Targets ----
    async def add_targets(
        self, campaign_id: uuid.UUID, tenant_id: uuid.UUID, lead_ids: list[uuid.UUID]
    ) -> int:
        """Add leads as pending targets. Idempotent (skips dupes / cross-tenant)."""
        if not lead_ids:
            return 0
        # Only accept leads that belong to this tenant.
        valid = await self.session.execute(
            select(Lead.id).where(Lead.tenant_id == tenant_id, Lead.id.in_(lead_ids))
        )
        valid_ids = {r for (r,) in valid.all()}
        existing = await self.session.execute(
            select(CampaignTarget.lead_id).where(CampaignTarget.campaign_id == campaign_id)
        )
        already = {r for (r,) in existing.all()}
        added = 0
        for lid in valid_ids - already:
            self.session.add(
                CampaignTarget(campaign_id=campaign_id, tenant_id=tenant_id, lead_id=lid)
            )
            added += 1
        await self.session.flush()
        return added

    async def claim_next(self, campaign_id: uuid.UUID, now: datetime) -> tuple | None:
        """Atomically claim one dial-eligible target → (target_id, phone, name).

        Uses FOR UPDATE SKIP LOCKED so concurrent workers never grab the same row.
        Marks it `calling` and bumps attempts/last_attempt_at.
        """
        stmt = (
            select(CampaignTarget, Lead.phone_number, Lead.name)
            .join(Lead, CampaignTarget.lead_id == Lead.id)
            .where(
                CampaignTarget.campaign_id == campaign_id,
                CampaignTarget.status == TargetStatus.pending,
                (CampaignTarget.next_attempt_at.is_(None))
                | (CampaignTarget.next_attempt_at <= now),
            )
            .order_by(CampaignTarget.created_at)
            .limit(1)
            .with_for_update(skip_locked=True, of=CampaignTarget)
        )
        row = (await self.session.execute(stmt)).first()
        if row is None:
            return None
        target, phone, name = row
        target.status = TargetStatus.calling
        target.attempts += 1
        target.last_attempt_at = now
        await self.session.flush()
        return target.id, phone, name, target.attempts

    async def mark_result(
        self,
        target_id: uuid.UUID,
        *,
        success: bool,
        max_attempts: int,
        retry_delay_minutes: int,
        now: datetime,
        call_id: uuid.UUID | None = None,
        error: str | None = None,
    ) -> None:
        target = await self.session.get(CampaignTarget, target_id)
        if target is None:
            return
        target.last_call_id = call_id
        if success:
            target.status = TargetStatus.completed
            target.last_error = None
            target.next_attempt_at = None
        elif target.attempts < max_attempts:
            # Requeue with backoff for another attempt.
            target.status = TargetStatus.pending
            target.next_attempt_at = now + timedelta(minutes=retry_delay_minutes)
            target.last_error = (error or "")[:255]
        else:
            target.status = TargetStatus.failed
            target.last_error = (error or "")[:255]
        await self.session.flush()

    async def reconcile_from_call(
        self,
        campaign_id: uuid.UUID,
        lead_id: uuid.UUID,
        *,
        outcome: CallOutcome | None,
        qualification_score: int | None,
        interested: bool | None,
        callback: bool,
        site_visit_booked: bool,
        call_id: uuid.UUID | None = None,
    ) -> CampaignTarget | None:
        """Fold a finalized call's result into its CampaignTarget.

        Called by the agent's finalize_call(). Because the target reached the
        agent, the call connected; we mark it completed and record the final
        outcome + flags so analytics reads reconciled truth, not dial attempts.
        """
        res = await self.session.execute(
            select(CampaignTarget).where(
                CampaignTarget.campaign_id == campaign_id,
                CampaignTarget.lead_id == lead_id,
            )
        )
        target = res.scalars().first()
        if target is None:
            return None
        target.status = TargetStatus.completed
        target.connected = True
        target.outcome = outcome
        target.qualification_score = qualification_score
        target.interested = interested
        target.callback = callback
        target.site_visit_booked = site_visit_booked
        target.next_attempt_at = None
        target.last_error = None
        if call_id is not None:
            target.last_call_id = call_id
        await self.session.flush()
        return target

    async def target_status_counts(self, campaign_id: uuid.UUID) -> dict[str, int]:
        rows = await self.session.execute(
            select(CampaignTarget.status, func.count())
            .where(CampaignTarget.campaign_id == campaign_id)
            .group_by(CampaignTarget.status)
        )
        return {status.value: int(n) for status, n in rows.all()}

    async def has_pending(self, campaign_id: uuid.UUID) -> bool:
        res = await self.session.execute(
            select(func.count())
            .select_from(CampaignTarget)
            .where(
                CampaignTarget.campaign_id == campaign_id,
                CampaignTarget.status == TargetStatus.pending,
            )
        )
        return int(res.scalar() or 0) > 0

    async def has_active(self, campaign_id: uuid.UUID) -> bool:
        """Any target still pending or mid-call (i.e. work remains)."""
        res = await self.session.execute(
            select(func.count())
            .select_from(CampaignTarget)
            .where(
                CampaignTarget.campaign_id == campaign_id,
                CampaignTarget.status.in_((TargetStatus.pending, TargetStatus.calling)),
            )
        )
        return int(res.scalar() or 0) > 0

    async def skip_remaining(self, campaign_id: uuid.UUID) -> int:
        """Mark all not-yet-final targets as skipped (used on stop)."""
        targets = await self.session.execute(
            select(CampaignTarget).where(
                CampaignTarget.campaign_id == campaign_id,
                CampaignTarget.status.in_((TargetStatus.pending, TargetStatus.calling)),
            )
        )
        n = 0
        for t in targets.scalars().all():
            t.status = TargetStatus.skipped
            n += 1
        await self.session.flush()
        return n

    async def running_campaign_ids(self) -> list[uuid.UUID]:
        res = await self.session.execute(
            select(Campaign.id).where(Campaign.status == CampaignStatus.running)
        )
        return [r for (r,) in res.all()]

    # ---- Analytics (reconciled: CampaignTarget is the source of truth) ----
    async def analytics(self, campaign_id: uuid.UUID) -> dict:
        counts = await self.target_status_counts(campaign_id)
        row = (
            await self.session.execute(
                select(
                    func.count().label("total"),
                    func.count().filter(CampaignTarget.attempts > 0).label("attempted"),
                    func.count().filter(CampaignTarget.connected.is_(True)).label("connected"),
                    func.count()
                    .filter(CampaignTarget.interested.is_(True))
                    .label("interested"),
                    func.count().filter(CampaignTarget.callback.is_(True)).label("callbacks"),
                    func.count()
                    .filter(CampaignTarget.site_visit_booked.is_(True))
                    .label("site_visits"),
                ).where(CampaignTarget.campaign_id == campaign_id)
            )
        ).one()

        connected = int(row.connected or 0)
        site_visits = int(row.site_visits or 0)
        return {
            "total_leads": int(row.total or 0),
            "attempted": int(row.attempted or 0),
            "connected": connected,
            "interested": int(row.interested or 0),
            "callbacks": int(row.callbacks or 0),
            "site_visits": site_visits,
            "conversion_rate": round(site_visits / connected * 100, 1) if connected else 0.0,
            "status_breakdown": counts,
        }
