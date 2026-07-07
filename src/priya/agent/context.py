"""Per-call runtime context shared with function tools.

Holds the conversation tracker, latency tracker, DB identifiers and the
pluggable service adapters (CRM, calendar, WhatsApp, knowledge). Stored as
`AgentSession.userdata` so tools can access it via `RunContext`.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime

from priya.agent.state import ConversationTracker
from priya.analytics.latency import LatencyTracker
from priya.calendar.base import CalendarProvider
from priya.crm.base import CRMAdapter
from priya.knowledge.base import KnowledgeRetriever
from priya.whatsapp.base import FollowUpService


@dataclass
class CallContext:
    call_id: uuid.UUID
    room_name: str
    direction: str  # inbound | outbound
    caller_number: str | None
    tracker: ConversationTracker
    latency: LatencyTracker

    # Pluggable services (selected by factories from env)
    crm: CRMAdapter
    calendar: CalendarProvider
    whatsapp: FollowUpService
    knowledge: KnowledgeRetriever

    lead_id: uuid.UUID | None = None
    tenant_id: uuid.UUID | None = None
    campaign_id: uuid.UUID | None = None
    finalized: bool = False
    # Answer tracking. `answered` flips true the moment the callee actually picks
    # up (SIP callStatus -> active) or the first real user speech arrives.
    # `answered_at` anchors the billable duration; NULL => never answered.
    answered: bool = False
    answered_at: datetime | None = None
    # Guards the goodbye + call-teardown path in finalize_call_tool so a second
    # tool invocation can't speak a second goodbye or shut the session down twice.
    shutdown_initiated: bool = False
    # Set by booking tools during the call; folded into the campaign target at
    # finalize (campaign reconciliation source of truth).
    site_visit_booked: bool = False
    callback_booked: bool = False
    transcript: list[dict] = field(default_factory=list)
