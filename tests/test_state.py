"""Tests for the conversation state machine + qualification scoring."""
from __future__ import annotations

from priya.agent.state import (
    ConversationState,
    ConversationTracker,
    LeadProfile,
)


def test_state_advances_in_order() -> None:
    t = ConversationTracker()
    assert t.state == ConversationState.GREETING
    assert t.advance() == ConversationState.QUALIFICATION
    assert t.advance() == ConversationState.PROPERTY_REQUIREMENTS
    assert t.state_changes == 2


def test_advance_to_specific_state() -> None:
    t = ConversationTracker()
    t.advance_to(ConversationState.BUDGET_COLLECTION)
    assert t.state == ConversationState.BUDGET_COLLECTION
    # Advancing to the same state doesn't increment counter.
    changes = t.state_changes
    t.advance_to(ConversationState.BUDGET_COLLECTION)
    assert t.state_changes == changes


def test_completion_state_is_terminal() -> None:
    t = ConversationTracker()
    t.advance_to(ConversationState.CALL_COMPLETION)
    assert t.next_state() == ConversationState.CALL_COMPLETION


def test_missing_core_fields() -> None:
    lead = LeadProfile(name="Rahul", city="Bengaluru")
    missing = lead.missing_core_fields()
    assert "property_type" in missing
    assert "name" not in missing


def test_qualification_scoring_hot_lead() -> None:
    lead = LeadProfile(
        name="Rahul",
        city="Bengaluru",
        property_type="apartment",
        budget_max=9000000,
        preferred_location="Whitefield",
        buying_timeline="immediate",
        site_visit_interest=True,
        interested=True,
    )
    assert lead.qualification_score() >= 70
    assert lead.qualification_band() == "hot"


def test_qualification_scoring_unqualified() -> None:
    lead = LeadProfile()
    assert lead.qualification_band() == "unqualified"
