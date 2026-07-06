"""add future-safe call.campaign_id column

Revision ID: 0003_call_campaign
Revises: 0002_lead_source
Create Date: 2026-07-07
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID as PGUUID

revision = "0003_call_campaign"
down_revision = "0002_lead_source"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("calls", sa.Column("campaign_id", PGUUID(as_uuid=True), nullable=True))
    op.create_index("ix_calls_campaign_id", "calls", ["campaign_id"])


def downgrade() -> None:
    op.drop_index("ix_calls_campaign_id", table_name="calls")
    op.drop_column("calls", "campaign_id")
