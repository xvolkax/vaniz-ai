"""Tests for call-completion helpers (pure functions, no I/O)."""
from __future__ import annotations

from priya.agent.completion import (
    _build_key_requirements,
    _format_budget,
    _recommended_next_action,
)
from priya.agent.state import LeadProfile


def test_format_budget_crore() -> None:
    lead = LeadProfile(budget_min=9000000, budget_max=15000000)
    assert _format_budget(lead) == "90 L - 1.5 Cr"


def test_format_budget_only_max() -> None:
    lead = LeadProfile(budget_max=5500000)
    assert _format_budget(lead) == "55 L"


def test_format_budget_none() -> None:
    assert _format_budget(LeadProfile()) is None


def test_key_requirements() -> None:
    lead = LeadProfile(
        property_type="villa",
        preferred_location="Sarjapur",
        city="Bengaluru",
        budget_max=15000000,
        purpose="investment",
        loan_required=True,
    )
    reqs = _build_key_requirements(lead)
    assert "villa" in reqs
    assert "Sarjapur" in reqs
    assert "loan needed" in reqs


def test_recommended_action_not_interested() -> None:
    lead = LeadProfile(interested=False)
    assert "not interested" in _recommended_next_action(lead).lower()


def test_recommended_action_site_visit() -> None:
    lead = LeadProfile(interested=True, site_visit_interest=True)
    assert "site visit" in _recommended_next_action(lead).lower()
