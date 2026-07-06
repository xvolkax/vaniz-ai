"""Calendar provider interface + shared conflict logic."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timedelta


@dataclass(slots=True)
class TimeSlot:
    start: datetime
    end: datetime

    def overlaps(self, other: "TimeSlot") -> bool:
        return self.start < other.end and other.start < self.end


@dataclass(slots=True)
class BookingResult:
    success: bool
    event_id: str | None = None
    conflict: bool = False
    message: str | None = None


class CalendarProvider(ABC):
    """Stable calendar interface used by appointment tools."""

    name: str = "base"
    working_hours: tuple[int, int] = (9, 20)  # 9 AM – 8 PM IST

    @abstractmethod
    async def is_available(self, slot: TimeSlot) -> bool:
        """Return True if slot has no conflict and is within working hours."""

    @abstractmethod
    async def book(
        self, slot: TimeSlot, title: str, description: str | None = None, location: str | None = None
    ) -> BookingResult:
        ...

    def within_working_hours(self, slot: TimeSlot) -> bool:
        start_h, end_h = self.working_hours
        return start_h <= slot.start.hour < end_h and slot.end.hour <= end_h

    @staticmethod
    def slot_from(start: datetime, duration_minutes: int) -> TimeSlot:
        return TimeSlot(start=start, end=start + timedelta(minutes=duration_minutes))

    async def aclose(self) -> None:
        return None
