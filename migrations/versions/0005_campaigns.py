"""campaigns + campaign_targets

Revision ID: 0005_campaigns
Revises: 0004_analytics_idx
Create Date: 2026-07-07
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import ENUM
from sqlalchemy.dialects.postgresql import UUID as PGUUID

revision = "0005_campaigns"
down_revision = "0004_analytics_idx"
branch_labels = None
depends_on = None

# create_type=False: created explicitly (idempotent) below; create_table must
# not re-emit CREATE TYPE for these named enums.
campaign_status = ENUM(
    "draft", "running", "paused", "completed", "failed",
    name="campaignstatus", create_type=False,
)
target_status = ENUM(
    "pending", "calling", "completed", "failed", "skipped",
    name="targetstatus", create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    campaign_status.create(bind, checkfirst=True)
    target_status.create(bind, checkfirst=True)

    op.create_table(
        "campaigns",
        sa.Column("id", PGUUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", PGUUID(as_uuid=True),
                  sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("status", campaign_status, nullable=False, server_default="draft"),
        sa.Column("concurrency", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("max_attempts", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("retry_delay_minutes", sa.Integer(), nullable=False, server_default="60"),
        sa.Column("working_hours_start", sa.Integer(), nullable=False, server_default="10"),
        sa.Column("working_hours_end", sa.Integer(), nullable=False, server_default="19"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_campaigns_tenant_id", "campaigns", ["tenant_id"])
    op.create_index("ix_campaigns_status", "campaigns", ["status"])
    op.create_index("ix_campaigns_tenant_status", "campaigns", ["tenant_id", "status"])

    op.create_table(
        "campaign_targets",
        sa.Column("id", PGUUID(as_uuid=True), primary_key=True),
        sa.Column("campaign_id", PGUUID(as_uuid=True),
                  sa.ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False),
        sa.Column("tenant_id", PGUUID(as_uuid=True),
                  sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("lead_id", PGUUID(as_uuid=True),
                  sa.ForeignKey("leads.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", target_status, nullable=False, server_default="pending"),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_attempt_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_call_id", PGUUID(as_uuid=True), nullable=True),
        sa.Column("last_error", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_campaign_targets_campaign_id", "campaign_targets", ["campaign_id"])
    op.create_index("ix_campaign_targets_tenant_id", "campaign_targets", ["tenant_id"])
    op.create_index("ix_campaign_targets_lead_id", "campaign_targets", ["lead_id"])
    op.create_index("ix_campaign_targets_status", "campaign_targets", ["status"])
    op.create_index(
        "ix_campaign_targets_campaign_status", "campaign_targets", ["campaign_id", "status"]
    )
    op.create_index(
        "uq_campaign_lead", "campaign_targets", ["campaign_id", "lead_id"], unique=True
    )


def downgrade() -> None:
    op.drop_table("campaign_targets")
    op.drop_table("campaigns")
    bind = op.get_bind()
    target_status.drop(bind, checkfirst=True)
    campaign_status.drop(bind, checkfirst=True)
