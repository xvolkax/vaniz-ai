"""API request/response models."""
from __future__ import annotations

import re
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from priya.db.models import (
    AppointmentStatus,
    AppointmentType,
    CallDirection,
    CallOutcome,
    CampaignStatus,
    LeadSource,
    LeadStatus,
    PropertyType,
    UserRole,
)

_E164 = re.compile(r"^\+?[1-9]\d{7,14}$")


class OutboundCallRequest(BaseModel):
    phone_number: str = Field(..., description="Destination number in E.164, e.g. +9198XXXXXXXX")
    lead_name: str | None = Field(default=None, max_length=160)

    @field_validator("phone_number")
    @classmethod
    def _validate_phone(cls, v: str) -> str:
        v = v.strip().replace(" ", "")
        if not _E164.match(v):
            raise ValueError("phone_number must be valid E.164 format")
        return v


class OutboundCallResponse(BaseModel):
    room_name: str
    phone_number: str
    participant_id: str | None = None
    status: str


class HealthResponse(BaseModel):
    status: str
    version: str
    db: str
    region: str


# --------------------------------------------------------------------------- #
# Auth
# --------------------------------------------------------------------------- #
class RegisterRequest(BaseModel):
    """Tenant self-signup: creates a Tenant + its first owner User."""

    tenant_name: str = Field(..., min_length=2, max_length=160)
    tenant_slug: str = Field(..., min_length=2, max_length=80)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    full_name: str | None = Field(default=None, max_length=160)

    @field_validator("tenant_slug")
    @classmethod
    def _slug(cls, v: str) -> str:
        v = v.strip().lower()
        if not re.match(r"^[a-z0-9][a-z0-9-]{1,79}$", v):
            raise ValueError("slug must be lowercase alphanumeric/hyphen")
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=1, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds


# --------------------------------------------------------------------------- #
# Tenants
# --------------------------------------------------------------------------- #
class TenantResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    slug: str
    is_active: bool
    phone_number: str | None = None
    builder_name: str | None = None
    region: str | None = None
    created_at: datetime


class TenantUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=160)
    phone_number: str | None = Field(default=None, max_length=20)
    builder_name: str | None = Field(default=None, max_length=160)
    builder_description: str | None = None
    region: str | None = Field(default=None, max_length=255)
    years_in_business: str | None = Field(default=None, max_length=80)
    completed_projects: str | None = Field(default=None, max_length=255)
    track_record: str | None = None
    penalty_clause: str | None = None
    site_visit_contact: str | None = Field(default=None, max_length=40)
    whatsapp_number: str | None = Field(default=None, max_length=40)
    brochure_available: bool | None = None
    loan_banks: list[str] | None = None
    emi_estimate: str | None = None
    knowledge_extra: dict | None = None


# --------------------------------------------------------------------------- #
# Users
# --------------------------------------------------------------------------- #
class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    full_name: str | None = Field(default=None, max_length=160)
    role: UserRole = UserRole.agent


class UserUpdate(BaseModel):
    full_name: str | None = Field(default=None, max_length=160)
    role: UserRole | None = None
    is_active: bool | None = None
    password: str | None = Field(default=None, min_length=8, max_length=128)


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    email: str
    full_name: str | None = None
    role: UserRole
    is_active: bool
    created_at: datetime


# --------------------------------------------------------------------------- #
# Properties
# --------------------------------------------------------------------------- #
class PropertyBase(BaseModel):
    project_name: str = Field(..., max_length=200)
    slug: str | None = Field(default=None, max_length=120)
    property_type: PropertyType = PropertyType.apartment
    location: str | None = Field(default=None, max_length=200)
    price: str | None = Field(default=None, max_length=255)
    total_cost: str | None = Field(default=None, max_length=255)
    possession: str | None = Field(default=None, max_length=120)
    carpet_area: str | None = Field(default=None, max_length=200)
    parking: str | None = Field(default=None, max_length=200)
    maintenance: str | None = Field(default=None, max_length=200)
    construction_status: str | None = Field(default=None, max_length=120)
    rera: str | None = Field(default=None, max_length=120)
    connectivity: str | None = None
    road_width: str | None = Field(default=None, max_length=120)
    amenities: list[str] = Field(default_factory=list)
    price_min: float | None = None
    price_max: float | None = None
    is_active: bool = True


class PropertyCreate(PropertyBase):
    pass


class PropertyUpdate(BaseModel):
    project_name: str | None = Field(default=None, max_length=200)
    slug: str | None = Field(default=None, max_length=120)
    property_type: PropertyType | None = None
    location: str | None = Field(default=None, max_length=200)
    price: str | None = Field(default=None, max_length=255)
    total_cost: str | None = Field(default=None, max_length=255)
    possession: str | None = Field(default=None, max_length=120)
    carpet_area: str | None = Field(default=None, max_length=200)
    parking: str | None = Field(default=None, max_length=200)
    maintenance: str | None = Field(default=None, max_length=200)
    construction_status: str | None = Field(default=None, max_length=120)
    rera: str | None = Field(default=None, max_length=120)
    connectivity: str | None = None
    road_width: str | None = Field(default=None, max_length=120)
    amenities: list[str] | None = None
    price_min: float | None = None
    price_max: float | None = None
    is_active: bool | None = None


class PropertyResponse(PropertyBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    created_at: datetime
    updated_at: datetime


# --------------------------------------------------------------------------- #
# Leads
# --------------------------------------------------------------------------- #
class LeadBase(BaseModel):
    name: str | None = Field(default=None, max_length=160)
    city: str | None = Field(default=None, max_length=120)
    property_type: PropertyType | None = None
    budget_min: float | None = None
    budget_max: float | None = None
    preferred_location: str | None = Field(default=None, max_length=200)
    buying_timeline: str | None = Field(default=None, max_length=120)
    purpose: str | None = Field(default=None, max_length=40)
    loan_required: bool | None = None
    site_visit_interest: bool | None = None
    preferred_language: str | None = Field(default=None, max_length=8)


class LeadCreate(LeadBase):
    phone_number: str = Field(..., description="E.164 phone number")
    status: LeadStatus = LeadStatus.new
    source: LeadSource = LeadSource.manual
    qualification_score: int | None = Field(default=None, ge=0, le=100)

    @field_validator("phone_number")
    @classmethod
    def _phone(cls, v: str) -> str:
        v = v.strip().replace(" ", "")
        if not _E164.match(v):
            raise ValueError("phone_number must be valid E.164 format")
        return v


class LeadUpdate(LeadBase):
    phone_number: str | None = Field(default=None, max_length=20)
    status: LeadStatus | None = None
    source: LeadSource | None = None
    qualification_score: int | None = Field(default=None, ge=0, le=100)


class LeadResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID | None = None
    name: str | None = None
    phone_number: str
    city: str | None = None
    property_type: PropertyType | None = None
    budget_min: float | None = None
    budget_max: float | None = None
    preferred_location: str | None = None
    buying_timeline: str | None = None
    purpose: str | None = None
    loan_required: bool | None = None
    site_visit_interest: bool | None = None
    preferred_language: str
    status: LeadStatus
    source: LeadSource
    qualification_score: int | None = None
    crm_external_id: str | None = None
    created_at: datetime
    updated_at: datetime


class LeadListResponse(BaseModel):
    """Paginated envelope for the leads list endpoint."""

    items: list[LeadResponse]
    total: int
    limit: int
    offset: int


class CallSummaryItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    direction: CallDirection
    outcome: CallOutcome | None = None
    started_at: datetime
    ended_at: datetime | None = None
    duration_seconds: float | None = None


class AppointmentItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    type: AppointmentType
    status: AppointmentStatus
    scheduled_at: datetime
    duration_minutes: int
    location: str | None = None
    notes: str | None = None


class LeadDetailResponse(LeadResponse):
    """Full lead view including related calls and appointments."""

    calls: list[CallSummaryItem] = Field(default_factory=list)
    appointments: list[AppointmentItem] = Field(default_factory=list)


class LeadImportError(BaseModel):
    row: int
    error: str


class LeadImportResult(BaseModel):
    created: int
    updated: int
    skipped: int
    errors: list[LeadImportError] = Field(default_factory=list)


# --------------------------------------------------------------------------- #
# Calls
# --------------------------------------------------------------------------- #
class CallListItem(BaseModel):
    """Compact row for the calls list (dashboard table)."""

    id: uuid.UUID
    lead_id: uuid.UUID | None = None
    lead_name: str | None = None
    phone_number: str | None = None
    direction: CallDirection
    call_date: datetime  # started_at
    duration_seconds: float | None = None
    outcome: CallOutcome | None = None
    qualification_score: int | None = None
    # True when a recording exists. The signed URL is fetched on demand from
    # GET /calls/{id}/recording — never a raw storage URL here.
    has_recording: bool = False


class ActiveCallItem(BaseModel):
    id: uuid.UUID
    lead_id: uuid.UUID | None = None
    lead_name: str | None = None
    phone_number: str | None = None
    direction: CallDirection
    started_at: datetime


class ActiveCallsResponse(BaseModel):
    items: list[ActiveCallItem]


class ListenTokenResponse(BaseModel):
    url: str
    token: str
    room: str


class RecordingUrlResponse(BaseModel):
    """Short-lived presigned URL for playing/downloading a call recording."""

    url: str
    expires_in: int  # seconds until the presigned URL expires


class CallListResponse(BaseModel):
    items: list[CallListItem]
    total: int
    limit: int
    offset: int


class LatencyMetrics(BaseModel):
    avg_stt_latency_ms: float | None = None
    avg_llm_latency_ms: float | None = None
    avg_tts_latency_ms: float | None = None
    avg_e2e_latency_ms: float | None = None
    user_interruptions: int = 0


class CallDetailResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID | None = None
    lead_id: uuid.UUID | None = None
    lead_name: str | None = None
    phone_number: str | None = None
    campaign_id: uuid.UUID | None = None
    direction: CallDirection
    room_name: str | None = None
    from_number: str | None = None
    to_number: str | None = None
    started_at: datetime
    ended_at: datetime | None = None
    duration_seconds: float | None = None
    outcome: CallOutcome | None = None
    final_state: str | None = None
    # True when a recording exists. Fetch the playable URL from
    # GET /calls/{id}/recording (short-lived presigned URL).
    has_recording: bool = False

    # Conversation intelligence (from ConversationSummary)
    transcript: list | None = None
    summary: str | None = None
    key_requirements: str | None = None
    qualification_score: int | None = None
    recommended_next_action: str | None = None
    follow_up_recommendation: str | None = None

    # Appointment linkage (via the call's lead)
    appointments: list[AppointmentItem] = Field(default_factory=list)

    # Latency / quality metrics
    latency: LatencyMetrics


# --------------------------------------------------------------------------- #
# Dashboard summary
# --------------------------------------------------------------------------- #
class RecentAppointmentItem(BaseModel):
    id: uuid.UUID
    lead_id: uuid.UUID | None = None
    lead_name: str | None = None
    type: AppointmentType
    status: AppointmentStatus
    scheduled_at: datetime
    location: str | None = None


class DashboardSummary(BaseModel):
    # KPI counters
    calls_today: int
    calls_this_month: int
    answered_calls: int          # this month
    interested_leads: int        # current pipeline
    site_visits_booked: int      # this month
    callback_requests: int       # this month
    hot_leads: int               # current (score >= 70)
    conversion_rate: float       # site visits / answered calls (this month), %

    # Recent activity feeds
    recent_calls: list[CallListItem] = Field(default_factory=list)
    recent_appointments: list[RecentAppointmentItem] = Field(default_factory=list)
    recent_hot_leads: list[LeadResponse] = Field(default_factory=list)


# --------------------------------------------------------------------------- #
# Analytics
# --------------------------------------------------------------------------- #
class AnalyticsOverview(BaseModel):
    period_days: int
    total_calls: int
    answered_calls: int
    answer_rate: float
    avg_call_duration_seconds: float | None = None
    avg_e2e_latency_ms: float | None = None
    total_leads: int
    qualified_leads: int
    hot_leads: int
    avg_qualification_score: float | None = None
    site_visits: int
    callbacks: int
    conversion_rate: float


class BreakdownItem(BaseModel):
    key: str
    count: int
    percentage: float


class BreakdownResponse(BaseModel):
    period_days: int
    total: int
    items: list[BreakdownItem]


class ConversionTrendPoint(BaseModel):
    date: str  # YYYY-MM-DD
    calls: int
    answered: int
    site_visits: int
    new_leads: int


class ConversionTrendsResponse(BaseModel):
    period_days: int
    points: list[ConversionTrendPoint]


# --------------------------------------------------------------------------- #
# Campaigns
# --------------------------------------------------------------------------- #
class CampaignConfig(BaseModel):
    concurrency: int = Field(default=1, ge=1, le=50)
    max_attempts: int = Field(default=3, ge=1, le=10)
    retry_delay_minutes: int = Field(default=60, ge=1, le=1440)
    working_hours_start: int = Field(default=10, ge=0, le=23)
    working_hours_end: int = Field(default=19, ge=0, le=23)


class CampaignCreate(CampaignConfig):
    name: str = Field(..., min_length=1, max_length=160)
    lead_ids: list[uuid.UUID] = Field(default_factory=list)


class AddLeadsRequest(BaseModel):
    lead_ids: list[uuid.UUID] = Field(..., min_length=1)


class CampaignResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    status: CampaignStatus
    concurrency: int
    max_attempts: int
    retry_delay_minutes: int
    working_hours_start: int
    working_hours_end: int
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None


class CampaignListResponse(BaseModel):
    items: list[CampaignResponse]
    total: int
    limit: int
    offset: int


class AddLeadsResponse(BaseModel):
    added: int
    total_targets: int


class CampaignAnalytics(BaseModel):
    campaign_id: uuid.UUID
    total_leads: int
    attempted: int
    connected: int
    interested: int
    callbacks: int
    site_visits: int
    conversion_rate: float
    status_breakdown: dict[str, int] = Field(default_factory=dict)
