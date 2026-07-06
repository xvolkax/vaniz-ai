"""Google Calendar provider.

Uses a service account for server-to-server access. Activated when
GOOGLE_CALENDAR_ENABLED=true and the `calendar` extra is installed. Performs
free/busy conflict detection via the Google Calendar API before booking.

Requires (Phase 1 optional): pip install '.[calendar]'
"""
from __future__ import annotations

from priya.calendar.base import BookingResult, CalendarProvider, TimeSlot
from priya.config import settings
from priya.utils.logging import get_logger

log = get_logger(__name__)


class GoogleCalendarProvider(CalendarProvider):
    name = "google"

    def __init__(self) -> None:
        self.calendar_id = settings.google_calendar_id
        self._service = None  # lazily built

    def _client(self):
        if self._service is not None:
            return self._service
        try:
            from google.oauth2 import service_account  # type: ignore
            from googleapiclient.discovery import build  # type: ignore
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError(
                "Google Calendar extras not installed. Run: pip install '.[calendar]'"
            ) from exc

        creds = service_account.Credentials.from_service_account_file(
            settings.google_service_account_json,
            scopes=["https://www.googleapis.com/auth/calendar"],
        )
        self._service = build("calendar", "v3", credentials=creds, cache_discovery=False)
        return self._service

    async def is_available(self, slot: TimeSlot) -> bool:
        if not self.within_working_hours(slot):
            return False
        # freebusy.query is blocking; run it in a thread to keep the loop free.
        import asyncio

        def _query() -> bool:
            body = {
                "timeMin": slot.start.isoformat(),
                "timeMax": slot.end.isoformat(),
                "items": [{"id": self.calendar_id}],
            }
            resp = self._client().freebusy().query(body=body).execute()
            busy = resp["calendars"][self.calendar_id].get("busy", [])
            return len(busy) == 0

        try:
            return await asyncio.to_thread(_query)
        except Exception as exc:  # pragma: no cover
            log.error("calendar.google.freebusy_error", error=str(exc))
            return False

    async def book(
        self,
        slot: TimeSlot,
        title: str,
        description: str | None = None,
        location: str | None = None,
    ) -> BookingResult:
        if not await self.is_available(slot):
            return BookingResult(success=False, conflict=True, message="Slot unavailable.")

        import asyncio

        def _insert() -> str:
            event = {
                "summary": title,
                "description": description or "",
                "location": location or "",
                "start": {"dateTime": slot.start.isoformat(), "timeZone": "Asia/Kolkata"},
                "end": {"dateTime": slot.end.isoformat(), "timeZone": "Asia/Kolkata"},
            }
            created = self._client().events().insert(calendarId=self.calendar_id, body=event).execute()
            return created["id"]

        try:
            event_id = await asyncio.to_thread(_insert)
            return BookingResult(success=True, event_id=event_id)
        except Exception as exc:  # pragma: no cover
            log.error("calendar.google.book_error", error=str(exc))
            return BookingResult(success=False, message=str(exc))
