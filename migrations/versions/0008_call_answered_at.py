"""add call.answered_at (real pickup time for accurate duration / answer-rate)

Revision ID: 0008_call_answered
Revises: 0007_call_recording
Create Date: 2026-07-07
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0008_call_answered"
down_revision = "0007_call_recording"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "calls",
        sa.Column("answered_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("calls", "answered_at")
