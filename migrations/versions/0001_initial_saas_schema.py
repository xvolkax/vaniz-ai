"""initial SaaS multi-tenant schema

Creates the full schema: tenants, users, properties (multi-tenant control-plane)
plus the operational tables (leads, calls, conversation_summaries, appointments,
audit_logs), all tenant-scoped.

Revision ID: 0001_initial_saas
Revises:
Create Date: 2026-07-06
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.dialects.postgresql import UUID as PGUUID

revision = "0001_initial_saas"
down_revision = None
branch_labels = None
depends_on = None

# Enum type definitions (created once, reused across tables).
call_direction = sa.Enum("inbound", "outbound", name="calldirection")
call_outcome = sa.Enum(
    "completed", "not_interested", "callback_requested", "transfer_requested",
    "no_answer", "failed", "voicemail", name="calloutcome",
)
lead_status = sa.Enum(
    "new", "qualifying", "qualified", "unqualified", "booked", "lost", name="leadstatus"
)
property_type = sa.Enum(
    "apartment", "villa", "plot", "commercial", "other", name="propertytype"
)
appointment_type = sa.Enum(
    "site_visit", "callback", "agent_transfer", name="appointmenttype"
)
appointment_status = sa.Enum(
    "scheduled", "confirmed", "cancelled", "completed", name="appointmentstatus"
)
user_role = sa.Enum("owner", "admin", "agent", "viewer", name="userrole")


def upgrade() -> None:
    bind = op.get_bind()
    for enum in (
        call_direction, call_outcome, lead_status, property_type,
        appointment_type, appointment_status, user_role,
    ):
        enum.create(bind, checkfirst=True)

    # ---- tenants ----
    op.create_table(
        "tenants",
        sa.Column("id", PGUUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("slug", sa.String(80), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("phone_number", sa.String(20), nullable=True),
        sa.Column("builder_name", sa.String(160), nullable=True),
        sa.Column("builder_description", sa.Text(), nullable=True),
        sa.Column("region", sa.String(255), nullable=True),
        sa.Column("years_in_business", sa.String(80), nullable=True),
        sa.Column("completed_projects", sa.String(255), nullable=True),
        sa.Column("track_record", sa.Text(), nullable=True),
        sa.Column("penalty_clause", sa.Text(), nullable=True),
        sa.Column("site_visit_contact", sa.String(40), nullable=True),
        sa.Column("whatsapp_number", sa.String(40), nullable=True),
        sa.Column("brochure_available", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("loan_banks", JSON(), nullable=True),
        sa.Column("emi_estimate", sa.Text(), nullable=True),
        sa.Column("knowledge_extra", JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_tenants_slug", "tenants", ["slug"], unique=True)
    op.create_index("ix_tenants_phone_number", "tenants", ["phone_number"])

    # ---- users ----
    op.create_table(
        "users",
        sa.Column("id", PGUUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", PGUUID(as_uuid=True),
                  sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(160), nullable=True),
        sa.Column("role", user_role, nullable=False, server_default="agent"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_index("ix_users_tenant_id", "users", ["tenant_id"])

    # ---- properties ----
    op.create_table(
        "properties",
        sa.Column("id", PGUUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", PGUUID(as_uuid=True),
                  sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("slug", sa.String(120), nullable=True),
        sa.Column("project_name", sa.String(200), nullable=False),
        sa.Column("property_type", property_type, nullable=False, server_default="apartment"),
        sa.Column("location", sa.String(200), nullable=True),
        sa.Column("price", sa.String(255), nullable=True),
        sa.Column("total_cost", sa.String(255), nullable=True),
        sa.Column("possession", sa.String(120), nullable=True),
        sa.Column("carpet_area", sa.String(200), nullable=True),
        sa.Column("parking", sa.String(200), nullable=True),
        sa.Column("maintenance", sa.String(200), nullable=True),
        sa.Column("construction_status", sa.String(120), nullable=True),
        sa.Column("rera", sa.String(120), nullable=True),
        sa.Column("connectivity", sa.Text(), nullable=True),
        sa.Column("road_width", sa.String(120), nullable=True),
        sa.Column("amenities", JSON(), nullable=True),
        sa.Column("price_min", sa.Float(), nullable=True),
        sa.Column("price_max", sa.Float(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_properties_tenant_id", "properties", ["tenant_id"])
    op.create_index("ix_properties_slug", "properties", ["slug"])
    op.create_index("ix_properties_property_type", "properties", ["property_type"])
    op.create_index("ix_properties_location", "properties", ["location"])
    op.create_index("ix_properties_is_active", "properties", ["is_active"])

    # ---- leads ----
    op.create_table(
        "leads",
        sa.Column("id", PGUUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", PGUUID(as_uuid=True),
                  sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=True),
        sa.Column("name", sa.String(160), nullable=True),
        sa.Column("phone_number", sa.String(20), nullable=False),
        sa.Column("city", sa.String(120), nullable=True),
        sa.Column("property_type", property_type, nullable=True),
        sa.Column("budget_min", sa.Float(), nullable=True),
        sa.Column("budget_max", sa.Float(), nullable=True),
        sa.Column("preferred_location", sa.String(200), nullable=True),
        sa.Column("buying_timeline", sa.String(120), nullable=True),
        sa.Column("purpose", sa.String(40), nullable=True),
        sa.Column("loan_required", sa.Boolean(), nullable=True),
        sa.Column("site_visit_interest", sa.Boolean(), nullable=True),
        sa.Column("preferred_language", sa.String(8), nullable=False, server_default="hi"),
        sa.Column("status", lead_status, nullable=False, server_default="new"),
        sa.Column("qualification_score", sa.Integer(), nullable=True),
        sa.Column("extra", JSON(), nullable=True),
        sa.Column("crm_external_id", sa.String(120), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_leads_tenant_id", "leads", ["tenant_id"])
    op.create_index("ix_leads_phone_number", "leads", ["phone_number"])
    op.create_index("ix_leads_status", "leads", ["status"])

    # ---- calls ----
    op.create_table(
        "calls",
        sa.Column("id", PGUUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", PGUUID(as_uuid=True),
                  sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=True),
        sa.Column("lead_id", PGUUID(as_uuid=True),
                  sa.ForeignKey("leads.id", ondelete="SET NULL"), nullable=True),
        sa.Column("room_name", sa.String(160), nullable=True),
        sa.Column("direction", call_direction, nullable=False),
        sa.Column("from_number", sa.String(20), nullable=True),
        sa.Column("to_number", sa.String(20), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_seconds", sa.Float(), nullable=True),
        sa.Column("outcome", call_outcome, nullable=True),
        sa.Column("final_state", sa.String(40), nullable=True),
        sa.Column("user_interruptions", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("avg_stt_latency_ms", sa.Float(), nullable=True),
        sa.Column("avg_llm_latency_ms", sa.Float(), nullable=True),
        sa.Column("avg_tts_latency_ms", sa.Float(), nullable=True),
        sa.Column("avg_e2e_latency_ms", sa.Float(), nullable=True),
    )
    op.create_index("ix_calls_tenant_id", "calls", ["tenant_id"])
    op.create_index("ix_calls_lead_id", "calls", ["lead_id"])
    op.create_index("ix_calls_room_name", "calls", ["room_name"])

    # ---- conversation_summaries ----
    op.create_table(
        "conversation_summaries",
        sa.Column("id", PGUUID(as_uuid=True), primary_key=True),
        sa.Column("call_id", PGUUID(as_uuid=True),
                  sa.ForeignKey("calls.id", ondelete="CASCADE"), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("key_requirements", sa.Text(), nullable=True),
        sa.Column("qualification_score", sa.Integer(), nullable=True),
        sa.Column("recommended_next_action", sa.Text(), nullable=True),
        sa.Column("follow_up_recommendation", sa.Text(), nullable=True),
        sa.Column("transcript", JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index(
        "ix_conversation_summaries_call_id", "conversation_summaries", ["call_id"], unique=True
    )

    # ---- appointments ----
    op.create_table(
        "appointments",
        sa.Column("id", PGUUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", PGUUID(as_uuid=True),
                  sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=True),
        sa.Column("lead_id", PGUUID(as_uuid=True),
                  sa.ForeignKey("leads.id", ondelete="CASCADE"), nullable=False),
        sa.Column("type", appointment_type, nullable=False),
        sa.Column("status", appointment_status, nullable=False, server_default="scheduled"),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("duration_minutes", sa.Integer(), nullable=False, server_default="45"),
        sa.Column("location", sa.String(255), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("external_calendar_event_id", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_appointments_tenant_id", "appointments", ["tenant_id"])
    op.create_index("ix_appointments_lead_id", "appointments", ["lead_id"])

    # ---- audit_logs ----
    op.create_table(
        "audit_logs",
        sa.Column("id", PGUUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", PGUUID(as_uuid=True),
                  sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=True),
        sa.Column("actor", sa.String(80), nullable=False, server_default="agent"),
        sa.Column("action", sa.String(120), nullable=False),
        sa.Column("entity_type", sa.String(80), nullable=True),
        sa.Column("entity_id", sa.String(80), nullable=True),
        sa.Column("payload", JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_audit_logs_tenant_id", "audit_logs", ["tenant_id"])
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"])


def downgrade() -> None:
    for table in (
        "audit_logs", "appointments", "conversation_summaries", "calls",
        "leads", "properties", "users", "tenants",
    ):
        op.drop_table(table)
    bind = op.get_bind()
    for enum in (
        user_role, appointment_status, appointment_type, property_type,
        lead_status, call_outcome, call_direction,
    ):
        enum.drop(bind, checkfirst=True)
