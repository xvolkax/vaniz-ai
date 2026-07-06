"""Shared helpers for dashboard/analytics time windows.

All boundaries are computed in IST (the product's operating timezone) and are
timezone-aware, so comparisons against the UTC-stored `timestamptz` columns are
correct regardless of storage timezone.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

IST = timezone(timedelta(hours=5, minutes=30))


def now_ist() -> datetime:
    return datetime.now(IST)


def day_start(dt: datetime) -> datetime:
    return dt.replace(hour=0, minute=0, second=0, microsecond=0)


def month_start(dt: datetime) -> datetime:
    return dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def period(days: int) -> tuple[datetime, datetime]:
    """Return (start, end) window ending now (IST), spanning `days` days."""
    end = now_ist()
    start = day_start(end) - timedelta(days=days - 1)
    return start, end + timedelta(seconds=1)
