"""Vendor-neutral CRM data contracts (Pydantic).

These decouple our domain model from any specific CRM field naming. Adapters
translate between these and vendor payloads.
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class LeadQualification(str, Enum):
    hot = "hot"
    warm = "warm"
    cold = "cold"
    unqualified = "unqualified"


class CRMLead(BaseModel):
    external_id: str | None = None
    name: str | None = None
    phone_number: str
    email: str | None = None
    city: str | None = None
    property_type: str | None = None
    budget_min: float | None = None
    budget_max: float | None = None
    preferred_location: str | None = None
    buying_timeline: str | None = None
    purpose: str | None = None
    loan_required: bool | None = None
    qualification: LeadQualification | None = None
    qualification_score: int | None = None
    notes: str | None = None
    source: str = "priya_voice_agent"
    extra: dict = Field(default_factory=dict)


class CRMAppointment(BaseModel):
    external_id: str | None = None
    lead_external_id: str | None = None
    lead_phone: str
    type: str
    scheduled_at: datetime
    duration_minutes: int = 45
    location: str | None = None
    notes: str | None = None


class CRMResult(BaseModel):
    success: bool
    external_id: str | None = None
    message: str | None = None
