"""SQLAlchemy 2.0 ORM models (async).

Schema covers: leads, calls, conversation summaries, appointments, audit logs.
Uses declarative typed mappings. All timestamps are timezone-aware UTC.
"""
from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


def _uuid() -> uuid.UUID:
    return uuid.uuid4()


# --------------------------------------------------------------------------- #
# Enums
# --------------------------------------------------------------------------- #
class CallDirection(str, enum.Enum):
    inbound = "inbound"
    outbound = "outbound"


class CallOutcome(str, enum.Enum):
    completed = "completed"
    not_interested = "not_interested"
    callback_requested = "callback_requested"
    transfer_requested = "transfer_requested"
    no_answer = "no_answer"
    failed = "failed"
    voicemail = "voicemail"


class LeadStatus(str, enum.Enum):
    new = "new"
    qualifying = "qualifying"
    qualified = "qualified"
    unqualified = "unqualified"
    booked = "booked"
    lost = "lost"


class LeadSource(str, enum.Enum):
    """How the lead entered the system (used for filtering/attribution)."""

    inbound_call = "inbound_call"
    outbound_call = "outbound_call"
    manual = "manual"
    csv_import = "csv_import"
    api = "api"
    other = "other"


class PropertyType(str, enum.Enum):
    apartment = "apartment"
    villa = "villa"
    plot = "plot"
    commercial = "commercial"
    other = "other"


class AppointmentType(str, enum.Enum):
    site_visit = "site_visit"
    callback = "callback"
    agent_transfer = "agent_transfer"


class AppointmentStatus(str, enum.Enum):
    scheduled = "scheduled"
    confirmed = "confirmed"
    cancelled = "cancelled"
    completed = "completed"


class CampaignStatus(str, enum.Enum):
    draft = "draft"
    running = "running"
    paused = "paused"
    completed = "completed"
    failed = "failed"


class TargetStatus(str, enum.Enum):
    pending = "pending"
    calling = "calling"
    completed = "completed"
    failed = "failed"
    skipped = "skipped"


class UserRole(str, enum.Enum):
    """Role-based access control tiers (highest to lowest privilege).

    owner  : tenant owner — full control incl. billing/user management.
    admin  : manage properties, users, leads, calls, campaigns.
    agent  : work leads/calls/appointments; read-only on config.
    viewer : read-only dashboard access.
    """

    owner = "owner"
    admin = "admin"
    agent = "agent"
    viewer = "viewer"


# --------------------------------------------------------------------------- #
# Multi-tenancy: Tenant (broker/organization) + Users
# --------------------------------------------------------------------------- #
class Tenant(Base):
    """A broker / real-estate organization. The root of data isolation.

    Also carries the builder-level ("Tier 1") facts that previously lived in
    project.yaml, so the agent prompt can be rendered per-tenant from the DB.
    """

    __tablename__ = "tenants"

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(160))
    slug: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Telephony: inbound calls to this number route to this tenant.
    phone_number: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)

    # Builder / company facts (Tier 1 — shared across all this tenant's projects)
    builder_name: Mapped[str | None] = mapped_column(String(160), nullable=True)
    builder_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    region: Mapped[str | None] = mapped_column(String(255), nullable=True)
    years_in_business: Mapped[str | None] = mapped_column(String(80), nullable=True)
    completed_projects: Mapped[str | None] = mapped_column(String(255), nullable=True)
    track_record: Mapped[str | None] = mapped_column(Text, nullable=True)
    penalty_clause: Mapped[str | None] = mapped_column(Text, nullable=True)
    site_visit_contact: Mapped[str | None] = mapped_column(String(40), nullable=True)
    whatsapp_number: Mapped[str | None] = mapped_column(String(40), nullable=True)
    brochure_available: Mapped[bool] = mapped_column(Boolean, default=False)
    loan_banks: Mapped[list] = mapped_column(JSON, default=list)
    emi_estimate: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Free-form shared blocks (cost_breakup, legal, plot_info, market_note...)
    knowledge_extra: Mapped[dict] = mapped_column(JSON, default=dict)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    users: Mapped[list[User]] = relationship(back_populates="tenant", cascade="all, delete-orphan")
    properties: Mapped[list[Property]] = relationship(
        back_populates="tenant", cascade="all, delete-orphan"
    )


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=_uuid)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), index=True
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str | None] = mapped_column(String(160), nullable=True)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), default=UserRole.agent)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    tenant: Mapped[Tenant] = relationship(back_populates="users")


class Property(Base):
    """A project/property owned by a tenant. Replaces project.yaml projects.

    The agent reads these dynamically per call, so dashboard edits are visible
    on the next call without a process restart.
    """

    __tablename__ = "properties"

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=_uuid)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), index=True
    )
    # Human/stable external identifier (e.g. "danapur_greens").
    slug: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    project_name: Mapped[str] = mapped_column(String(200))
    property_type: Mapped[PropertyType] = mapped_column(
        Enum(PropertyType), default=PropertyType.apartment, index=True
    )
    location: Mapped[str | None] = mapped_column(String(200), nullable=True, index=True)
    price: Mapped[str | None] = mapped_column(String(255), nullable=True)
    total_cost: Mapped[str | None] = mapped_column(String(255), nullable=True)
    possession: Mapped[str | None] = mapped_column(String(120), nullable=True)
    carpet_area: Mapped[str | None] = mapped_column(String(200), nullable=True)
    parking: Mapped[str | None] = mapped_column(String(200), nullable=True)
    maintenance: Mapped[str | None] = mapped_column(String(200), nullable=True)
    construction_status: Mapped[str | None] = mapped_column(String(120), nullable=True)
    rera: Mapped[str | None] = mapped_column(String(120), nullable=True)
    connectivity: Mapped[str | None] = mapped_column(Text, nullable=True)
    road_width: Mapped[str | None] = mapped_column(String(120), nullable=True)
    amenities: Mapped[list] = mapped_column(JSON, default=list)

    # Numeric price band (INR, absolute) for structured budget matching.
    price_min: Mapped[float | None] = mapped_column(Float, nullable=True)
    price_max: Mapped[float | None] = mapped_column(Float, nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    tenant: Mapped[Tenant] = relationship(back_populates="properties")


# --------------------------------------------------------------------------- #
# Tables
# --------------------------------------------------------------------------- #
class Lead(Base):
    __tablename__ = "leads"
    __table_args__ = (
        # Dashboard/analytics access paths (all tenant-scoped).
        Index("ix_leads_tenant_created", "tenant_id", "created_at"),
        Index("ix_leads_tenant_status", "tenant_id", "status"),
        Index("ix_leads_tenant_source", "tenant_id", "source"),
        Index("ix_leads_tenant_score", "tenant_id", "qualification_score"),
    )

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=_uuid)
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=True, index=True
    )
    name: Mapped[str | None] = mapped_column(String(160), nullable=True)
    phone_number: Mapped[str] = mapped_column(String(20), index=True)
    city: Mapped[str | None] = mapped_column(String(120), nullable=True)
    property_type: Mapped[PropertyType | None] = mapped_column(Enum(PropertyType), nullable=True)
    budget_min: Mapped[float | None] = mapped_column(Float, nullable=True)
    budget_max: Mapped[float | None] = mapped_column(Float, nullable=True)
    preferred_location: Mapped[str | None] = mapped_column(String(200), nullable=True)
    buying_timeline: Mapped[str | None] = mapped_column(String(120), nullable=True)
    purpose: Mapped[str | None] = mapped_column(String(40), nullable=True)  # self_use | investment
    loan_required: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    site_visit_interest: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    preferred_language: Mapped[str] = mapped_column(String(8), default="hi")

    status: Mapped[LeadStatus] = mapped_column(Enum(LeadStatus), default=LeadStatus.new, index=True)
    qualification_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source: Mapped[LeadSource] = mapped_column(
        Enum(LeadSource), default=LeadSource.other, index=True
    )

    # Free-form extra attributes (RAG/CRM extensibility, no schema migration needed)
    extra: Mapped[dict] = mapped_column(JSON, default=dict)
    crm_external_id: Mapped[str | None] = mapped_column(String(120), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    calls: Mapped[list[Call]] = relationship(back_populates="lead", cascade="all, delete-orphan")
    appointments: Mapped[list[Appointment]] = relationship(
        back_populates="lead", cascade="all, delete-orphan"
    )


class Call(Base):
    __tablename__ = "calls"
    __table_args__ = (
        # Time-series & filter access paths for the dashboard (tenant-scoped).
        Index("ix_calls_tenant_started", "tenant_id", "started_at"),
        Index("ix_calls_tenant_outcome", "tenant_id", "outcome"),
        Index("ix_calls_tenant_campaign", "tenant_id", "campaign_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=_uuid)
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=True, index=True
    )
    lead_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("leads.id", ondelete="SET NULL"), nullable=True, index=True
    )
    # Future-safe: links a call to an outbound campaign (campaigns table TBD).
    # No FK yet so the column is usable before the campaigns feature ships.
    campaign_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), nullable=True, index=True
    )
    room_name: Mapped[str | None] = mapped_column(String(160), nullable=True, index=True)
    direction: Mapped[CallDirection] = mapped_column(Enum(CallDirection))
    from_number: Mapped[str | None] = mapped_column(String(20), nullable=True)
    to_number: Mapped[str | None] = mapped_column(String(20), nullable=True)

    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    # When the callee actually picked up (SIP status -> active). NULL means the
    # call was never answered (rang out / busy / declined / voicemail). Duration
    # is measured from this moment, not from started_at (the dial/connect time).
    answered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)

    outcome: Mapped[CallOutcome | None] = mapped_column(Enum(CallOutcome), nullable=True)
    final_state: Mapped[str | None] = mapped_column(String(40), nullable=True)
    user_interruptions: Mapped[int] = mapped_column(Integer, default=0)
    # Legacy full URL (pre-private-bucket). No longer written; kept for old rows.
    recording_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    # Object key of the recording in the (private) storage bucket, e.g.
    # "recordings/<call_id>.mp4". We store ONLY the key — never a public URL or a
    # presigned URL. Playback is served via short-lived presigned URLs minted
    # on demand by GET /calls/{id}/recording.
    recording_key: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Aggregated latency metrics (ms)
    avg_stt_latency_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    avg_llm_latency_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    avg_tts_latency_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    avg_e2e_latency_ms: Mapped[float | None] = mapped_column(Float, nullable=True)

    lead: Mapped[Lead | None] = relationship(back_populates="calls")
    summary: Mapped[ConversationSummary | None] = relationship(
        back_populates="call", cascade="all, delete-orphan", uselist=False
    )


class ConversationSummary(Base):
    __tablename__ = "conversation_summaries"

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=_uuid)
    call_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("calls.id", ondelete="CASCADE"), unique=True, index=True
    )
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    key_requirements: Mapped[str | None] = mapped_column(Text, nullable=True)
    qualification_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    recommended_next_action: Mapped[str | None] = mapped_column(Text, nullable=True)
    follow_up_recommendation: Mapped[str | None] = mapped_column(Text, nullable=True)
    transcript: Mapped[list | None] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    call: Mapped[Call] = relationship(back_populates="summary")


class Appointment(Base):
    __tablename__ = "appointments"
    __table_args__ = (
        Index("ix_appointments_tenant_type", "tenant_id", "type"),
        Index("ix_appointments_tenant_created", "tenant_id", "created_at"),
        Index("ix_appointments_tenant_scheduled", "tenant_id", "scheduled_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=_uuid)
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=True, index=True
    )
    lead_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("leads.id", ondelete="CASCADE"), index=True
    )
    type: Mapped[AppointmentType] = mapped_column(Enum(AppointmentType))
    status: Mapped[AppointmentStatus] = mapped_column(
        Enum(AppointmentStatus), default=AppointmentStatus.scheduled
    )
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    duration_minutes: Mapped[int] = mapped_column(Integer, default=45)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    external_calendar_event_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    lead: Mapped[Lead] = relationship(back_populates="appointments")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=_uuid)
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=True, index=True
    )
    actor: Mapped[str] = mapped_column(String(80), default="agent")
    action: Mapped[str] = mapped_column(String(120), index=True)
    entity_type: Mapped[str | None] = mapped_column(String(80), nullable=True)
    entity_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


# --------------------------------------------------------------------------- #
# Campaigns (outbound bulk calling)
# --------------------------------------------------------------------------- #
class Campaign(Base):
    __tablename__ = "campaigns"
    __table_args__ = (
        Index("ix_campaigns_tenant_status", "tenant_id", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=_uuid)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(160))
    status: Mapped[CampaignStatus] = mapped_column(
        Enum(CampaignStatus), default=CampaignStatus.draft, index=True
    )

    # Execution engine configuration
    concurrency: Mapped[int] = mapped_column(Integer, default=1)
    max_attempts: Mapped[int] = mapped_column(Integer, default=3)
    retry_delay_minutes: Mapped[int] = mapped_column(Integer, default=60)
    # Working hours (IST, 24h). Calls are only placed within [start, end).
    working_hours_start: Mapped[int] = mapped_column(Integer, default=10)
    working_hours_end: Mapped[int] = mapped_column(Integer, default=19)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    targets: Mapped[list[CampaignTarget]] = relationship(
        back_populates="campaign", cascade="all, delete-orphan"
    )


class CampaignTarget(Base):
    __tablename__ = "campaign_targets"
    __table_args__ = (
        Index("ix_campaign_targets_campaign_status", "campaign_id", "status"),
        Index("uq_campaign_lead", "campaign_id", "lead_id", unique=True),
    )

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=_uuid)
    campaign_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("campaigns.id", ondelete="CASCADE"), index=True
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), index=True
    )
    lead_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("leads.id", ondelete="CASCADE"), index=True
    )
    status: Mapped[TargetStatus] = mapped_column(
        Enum(TargetStatus), default=TargetStatus.pending, index=True
    )
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    last_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # When set, the target is not eligible for (re)dialing until this time.
    next_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_call_id: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    last_error: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # --- Reconciled outcome (source of truth for campaign analytics) ---
    # Populated by the agent's finalize_call() once the conversation completes.
    connected: Mapped[bool] = mapped_column(Boolean, default=False)
    outcome: Mapped[CallOutcome | None] = mapped_column(Enum(CallOutcome), nullable=True)
    qualification_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    interested: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    callback: Mapped[bool] = mapped_column(Boolean, default=False)
    site_visit_booked: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    campaign: Mapped[Campaign] = relationship(back_populates="targets")
