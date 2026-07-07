"""add call.recording_url

Revision ID: 0007_call_recording
Revises: 0006_target_recon
Create Date: 2026-07-07
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0007_call_recording"
down_revision = "0006_target_recon"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("calls", sa.Column("recording_url", sa.String(500), nullable=True))


def downgrade() -> None:
    op.drop_column("calls", "recording_url")
