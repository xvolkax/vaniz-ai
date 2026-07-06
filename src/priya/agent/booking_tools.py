"""Appointment / booking function tools.

Site visit scheduling, callback scheduling, and agent-transfer requests. All
bookings run conflict detection through the configured CalendarProvider before
persisting an Appointment row.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Annotated, Literal

from livekit.agents import RunContext, function_tool
from pydantic import Field

from priya.agent.context import CallContext
from priya.agent.state import ConversationState
from priya.agent.tools import _persist_lead
from priya.analytics import metrics as m
from priya.db.database import session_scope
from priya.db.models import (
    AppointmentStatus,
    AppointmentType,
    LeadStatus,
)
from priya.db.repositories import AppointmentRepository, AuditRepository, LeadRepository
from priya.utils.logging import get_logger

log = get_logger(__name__)

# IST offset for interpreting naive datetimes spoken by callers.
_IST = timezone(timedelta(hours=5, minutes=30))


def _parse_when(when: str) -> datetime | None:
    """Parse an ISO-8601 datetime; assume IST if timezone missing."""
    try:
        dt = datetime.fromisoformat(when.replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=_IST)
    return dt


async def _ensure_lead(ctx: CallContext):
    if ctx.lead_id is None:
        await _persist_lead(ctx)
    return ctx.lead_id


@function_tool()
async def schedule_site_visit(
    context: RunContext[CallContext],
    when: Annotated[
        str, Field(description="Preferred date-time in ISO 8601, e.g. 2026-07-06T16:00:00")
    ],
    location: Annotated[str | None, Field(description="Project/site location")] = None,
    duration_minutes: Annotated[int, Field(description="Visit duration")] = 45,
) -> str:
    """Site visit book karo. Pehle caller se preferred din aur time confirm karo,
    phir ye tool call karo. Conflict hone par doosra time offer karega."""
    ctx = context.userdata
    m.TOOL_CALLS.labels(tool="schedule_site_visit").inc()

    dt = _parse_when(when)
    if dt is None:
        return "Time samajh nahi aaya. Kripya din aur time dobara batayein."
    if dt < datetime.now(_IST):
        return "Ye samay to beet chuka hai. Kripya aane wale kisi din aur time batayein."

    slot = ctx.calendar.slot_from(dt, duration_minutes)
    if not await ctx.calendar.is_available(slot):
        alt = dt + timedelta(hours=1)
        return (
            f"Us time slot par availability nahi hai. "
            f"Kya {alt.strftime('%d %b %I:%M %p')} theek rahega?"
        )

    booking = await ctx.calendar.book(
        slot,
        title=f"Site Visit - {ctx.tracker.lead.name or ctx.caller_number}",
        description=f"Property: {ctx.tracker.lead.property_type}, "
        f"Location: {ctx.tracker.lead.preferred_location}",
        location=location or ctx.tracker.lead.preferred_location,
    )
    if not booking.success:
        return booking.message or "Booking abhi possible nahi. Callback schedule karein?"

    lead_id = await _ensure_lead(ctx)
    async with session_scope() as session:
        appt_repo = AppointmentRepository(session)
        await appt_repo.create(
            lead_id=lead_id,
            tenant_id=ctx.tenant_id,
            type=AppointmentType.site_visit,
            status=AppointmentStatus.scheduled,
            scheduled_at=dt,
            duration_minutes=duration_minutes,
            location=location or ctx.tracker.lead.preferred_location,
            external_calendar_event_id=booking.event_id,
        )
        if lead_id:
            await LeadRepository(session).set_status(lead_id, LeadStatus.booked)
        await AuditRepository(session).log(
            "appointment.site_visit", entity_type="lead", entity_id=str(lead_id)
        )

    ctx.tracker.lead.site_visit_interest = True
    ctx.site_visit_booked = True
    ctx.tracker.advance_to(ConversationState.SUMMARY)
    m.APPOINTMENTS_BOOKED.labels(type="site_visit").inc()
    log.info("tool.schedule_site_visit", call_id=str(ctx.call_id), when=dt.isoformat())
    return f"Site visit confirmed for {dt.strftime('%d %b, %I:%M %p')}. Confirm this to the caller."


@function_tool()
async def schedule_callback(
    context: RunContext[CallContext],
    when: Annotated[str, Field(description="Preferred callback date-time in ISO 8601")],
    reason: Annotated[str | None, Field(description="Why the callback is needed")] = None,
) -> str:
    """Callback schedule karo — jab caller abhi baat nahi kar sakta ya baad mein
    chahta hai, ya human agent se baat karna chahta hai."""
    ctx = context.userdata
    m.TOOL_CALLS.labels(tool="schedule_callback").inc()

    dt = _parse_when(when)
    if dt is None:
        return "Callback time samajh nahi aaya. Kripya din aur time batayein."
    if dt < datetime.now(_IST):
        return "Ye samay beet chuka hai. Kripya aane wale kisi din aur time batayein."

    lead_id = await _ensure_lead(ctx)
    async with session_scope() as session:
        await AppointmentRepository(session).create(
            lead_id=lead_id,
            tenant_id=ctx.tenant_id,
            type=AppointmentType.callback,
            status=AppointmentStatus.scheduled,
            scheduled_at=dt,
            duration_minutes=15,
            notes=reason,
        )
        await AuditRepository(session).log(
            "appointment.callback", entity_type="lead", entity_id=str(lead_id)
        )

    ctx.callback_booked = True
    ctx.tracker.advance_to(ConversationState.SUMMARY)
    m.APPOINTMENTS_BOOKED.labels(type="callback").inc()
    log.info("tool.schedule_callback", call_id=str(ctx.call_id), when=dt.isoformat())
    return f"Callback scheduled for {dt.strftime('%d %b, %I:%M %p')}. Confirm this to the caller."

@function_tool()
async def request_agent_transfer(
    context: RunContext[CallContext],
    reason: Annotated[str | None, Field(description="Why a human agent is needed")] = None,
) -> str:
    """Human agent transfer request banao. Agar live transfer possible nahi to
    jaldi callback schedule karega."""
    ctx = context.userdata
    m.TOOL_CALLS.labels(tool="request_agent_transfer").inc()

    when = datetime.now(_IST) + timedelta(minutes=30)
    lead_id = await _ensure_lead(ctx)
    async with session_scope() as session:
        await AppointmentRepository(session).create(
            lead_id=lead_id,
            tenant_id=ctx.tenant_id,
            type=AppointmentType.agent_transfer,
            status=AppointmentStatus.scheduled,
            scheduled_at=when,
            duration_minutes=15,
            notes=reason or "Caller requested human agent",
        )
        await AuditRepository(session).log(
            "appointment.agent_transfer", entity_type="lead", entity_id=str(lead_id)
        )

    m.APPOINTMENTS_BOOKED.labels(type="agent_transfer").inc()
    log.info("tool.request_agent_transfer", call_id=str(ctx.call_id))
    return (
        "Human agent request noted. Ek senior agent thodi der mein call karega. "
        "Confirm this warmly to the caller."
    )
