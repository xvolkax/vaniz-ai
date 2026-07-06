"""Outbound campaign execution engine.

Drives bulk outbound calling on top of the existing single-call engine
(`priya.telephony.outbound.place_outbound_call`), with configurable concurrency,
retry logic + backoff, and working-hours gating. All work is tenant-scoped.
"""
from __future__ import annotations

from priya.campaigns.engine import engine

__all__ = ["engine"]
