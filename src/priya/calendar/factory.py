"""Calendar provider factory."""
from __future__ import annotations

from functools import lru_cache

from priya.calendar.base import CalendarProvider
from priya.calendar.db_calendar import DBCalendarProvider
from priya.config import settings
from priya.utils.logging import get_logger

log = get_logger(__name__)


@lru_cache(maxsize=1)
def get_calendar_provider() -> CalendarProvider:
    if settings.google_calendar_enabled:
        from priya.calendar.google_calendar import GoogleCalendarProvider

        log.info("calendar.provider.google")
        return GoogleCalendarProvider()
    log.info("calendar.provider.db")
    return DBCalendarProvider()
