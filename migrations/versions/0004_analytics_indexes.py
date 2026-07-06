"""composite indexes for dashboard/analytics aggregate queries

Revision ID: 0004_analytics_idx
Revises: 0003_call_campaign
Create Date: 2026-07-07
"""
from __future__ import annotations

from alembic import op

revision = "0004_analytics_idx"
down_revision = "0003_call_campaign"
branch_labels = None
depends_on = None

_INDEXES = [
    ("ix_calls_tenant_started", "calls", ["tenant_id", "started_at"]),
    ("ix_calls_tenant_outcome", "calls", ["tenant_id", "outcome"]),
    ("ix_calls_tenant_campaign", "calls", ["tenant_id", "campaign_id"]),
    ("ix_leads_tenant_created", "leads", ["tenant_id", "created_at"]),
    ("ix_leads_tenant_status", "leads", ["tenant_id", "status"]),
    ("ix_leads_tenant_source", "leads", ["tenant_id", "source"]),
    ("ix_leads_tenant_score", "leads", ["tenant_id", "qualification_score"]),
    ("ix_appointments_tenant_type", "appointments", ["tenant_id", "type"]),
    ("ix_appointments_tenant_created", "appointments", ["tenant_id", "created_at"]),
    ("ix_appointments_tenant_scheduled", "appointments", ["tenant_id", "scheduled_at"]),
]


def upgrade() -> None:
    for name, table, cols in _INDEXES:
        op.create_index(name, table, cols)


def downgrade() -> None:
    for name, table, _ in reversed(_INDEXES):
        op.drop_index(name, table_name=table)
