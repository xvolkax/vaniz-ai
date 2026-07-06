"""campaign_target reconciliation columns

Adds the reconciled-outcome fields populated by the agent's finalize_call so
CampaignTarget becomes the source of truth for campaign analytics.

Revision ID: 0006_target_recon
Revises: 0005_campaigns
Create Date: 2026-07-07
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0006_target_recon"
down_revision = "0005_campaigns"
branch_labels = None
depends_on = None

# Reuse the existing calloutcome enum type (created in 0001); do not recreate it.
_call_outcome = postgresql.ENUM(
    "completed", "not_interested", "callback_requested", "transfer_requested",
    "no_answer", "failed", "voicemail",
    name="calloutcome",
    create_type=False,
)


def upgrade() -> None:
    op.add_column(
        "campaign_targets",
        sa.Column("connected", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column("campaign_targets", sa.Column("outcome", _call_outcome, nullable=True))
    op.add_column(
        "campaign_targets", sa.Column("qualification_score", sa.Integer(), nullable=True)
    )
    op.add_column("campaign_targets", sa.Column("interested", sa.Boolean(), nullable=True))
    op.add_column(
        "campaign_targets",
        sa.Column("callback", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "campaign_targets",
        sa.Column("site_visit_booked", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    for col in (
        "site_visit_booked", "callback", "interested", "qualification_score",
        "outcome", "connected",
    ):
        op.drop_column("campaign_targets", col)
