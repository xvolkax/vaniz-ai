"""Explicit conversation state machine + in-call lead profile.

The state machine keeps the conversation goal-directed and prevents the LLM
from wandering or re-asking answered questions. Transitions are advanced by the
function tools as data is collected.
"""
from __future__ import annotations

import enum
from datetime import datetime, timezone

from pydantic import BaseModel, Field


class ConversationState(str, enum.Enum):
    GREETING = "greeting"
    QUALIFICATION = "qualification"
    PROPERTY_REQUIREMENTS = "property_requirements"
    BUDGET_COLLECTION = "budget_collection"
    TIMELINE_COLLECTION = "timeline_collection"
    APPOINTMENT_BOOKING = "appointment_booking"
    SUMMARY = "summary"
    CALL_COMPLETION = "call_completion"


# Ordered flow used to compute "next" state and progress.
STATE_ORDER: list[ConversationState] = [
    ConversationState.GREETING,
    ConversationState.QUALIFICATION,
    ConversationState.PROPERTY_REQUIREMENTS,
    ConversationState.BUDGET_COLLECTION,
    ConversationState.TIMELINE_COLLECTION,
    ConversationState.APPOINTMENT_BOOKING,
    ConversationState.SUMMARY,
    ConversationState.CALL_COMPLETION,
]


class LeadProfile(BaseModel):
    """Mutable lead data collected during the call."""

    name: str | None = None
    phone_number: str | None = None
    city: str | None = None
    property_type: str | None = None
    budget_min: float | None = None
    budget_max: float | None = None
    preferred_location: str | None = None
    buying_timeline: str | None = None
    purpose: str | None = None  # self_use | investment
    loan_required: bool | None = None
    site_visit_interest: bool | None = None
    preferred_language: str = "hi"
    interested: bool | None = None  # False => not interested, end politely

    def collected_fields(self) -> dict[str, object]:
        return {k: v for k, v in self.model_dump().items() if v is not None}

    def missing_core_fields(self) -> list[str]:
        core = [
            "name",
            "city",
            "property_type",
            "budget_max",
            "preferred_location",
            "buying_timeline",
        ]
        return [f for f in core if getattr(self, f) is None]

    def qualification_score(self) -> int:
        """Heuristic 0-100 score used for lead prioritisation."""
        score = 0
        if self.interested:
            score += 15
        if self.name:
            score += 8
        if self.city:
            score += 8
        if self.property_type:
            score += 10
        if self.budget_max:
            score += 18
        if self.preferred_location:
            score += 10
        if self.buying_timeline:
            score += 12
            # Sooner timeline => hotter
            tl = self.buying_timeline.lower()
            if any(w in tl for w in ("immediate", "1 month", "month", "urgent", "abhi", "turant")):
                score += 8
        if self.site_visit_interest:
            score += 11
        return min(score, 100)

    def qualification_band(self) -> str:
        s = self.qualification_score()
        if s >= 70:
            return "hot"
        if s >= 45:
            return "warm"
        if s >= 20:
            return "cold"
        return "unqualified"


class ConversationTracker(BaseModel):
    """Tracks current state + timestamps for a single call."""

    state: ConversationState = ConversationState.GREETING
    lead: LeadProfile = Field(default_factory=LeadProfile)
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    state_changes: int = 0

    def advance_to(self, new_state: ConversationState) -> None:
        if new_state != self.state:
            self.state = new_state
            self.state_changes += 1

    def next_state(self) -> ConversationState:
        idx = STATE_ORDER.index(self.state)
        return STATE_ORDER[min(idx + 1, len(STATE_ORDER) - 1)]

    def advance(self) -> ConversationState:
        self.advance_to(self.next_state())
        return self.state
