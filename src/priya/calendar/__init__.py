"""Calendar package — booking with conflict detection.

Phase 1 ships a DB-backed calendar (conflict detection against the appointments
table). Google Calendar is wired behind the same interface and activated via
GOOGLE_CALENDAR_ENABLED.
"""
from priya.calendar.base import CalendarProvider, TimeSlot
from priya.calendar.factory import get_calendar_provider

__all__ = ["CalendarProvider", "TimeSlot", "get_calendar_provider"]
