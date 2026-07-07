"""add lead.source column for attribution/filtering

Revision ID: 0002_lead_source
Revises: 0001_initial_saas
Create Date: 2026-07-07
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import ENUM

revision = "0002_lead_source"
down_revision = "0001_initial_saas"
branch_labels = None
depends_on = None

# create_type=False: created explicitly (idempotent) below; add_column must not
# re-emit CREATE TYPE.
lead_source = ENUM(
    "inbound_call", "outbound_call", "manual", "csv_import", "api", "other",
    name="leadsource", create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    lead_source.create(bind, checkfirst=True)
    op.add_column(
        "leads",
        sa.Column("source", lead_source, nullable=False, server_default="other"),
    )
    op.create_index("ix_leads_source", "leads", ["source"])


def downgrade() -> None:
    op.drop_index("ix_leads_source", table_name="leads")
    op.drop_column("leads", "source")
    lead_source.drop(op.get_bind(), checkfirst=True)
