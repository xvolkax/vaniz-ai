"""DB-backed calendar (Phase 1 default).

Conflict detection queries the `appointments` table. No external dependency —
works out of the box and keeps latency low. Interface-compatible with the
Google Calendar provider.
"""
from __future__ import annotations

from priya.calendar.base import BookingResult, CalendarProvider, TimeSlot
from priya.db.database import session_scope
from priya.db.repositories import AppointmentRepository
from priya.utils.logging import get_logger

log = get_logger(__name__)


class DBCalendarProvider(CalendarProvider):
    name = "db"

    async def is_available(self, slot: TimeSlot) -> bool:
        if not self.within_working_hours(slot):
            return False
        async with session_scope() as session:
            repo = AppointmentRepository(session)
            existing = await repo.list_between(slot.start, slot.end)
            for appt in existing:
                other = self.slot_from(appt.scheduled_at, appt.duration_minutes)
                if slot.overlaps(other):
                    return False
        return True

    async def book(
        self,
        slot: TimeSlot,
        title: str,
        description: str | None = None,
        location: str | None = None,
    ) -> BookingResult:
        if not self.within_working_hours(slot):
            return BookingResult(
                success=False, message="Outside working hours (9 AM – 8 PM IST)."
            )
        if not await self.is_available(slot):
            return BookingResult(success=False, conflict=True, message="Time slot already booked.")
        # Actual appointment row is created by the caller (with lead linkage).
        log.info("calendar.db.slot_free", start=slot.start.isoformat())
        return BookingResult(success=True, event_id=None)
