"""add call.recording_key (store object key only; private bucket + presigned URLs)

Revision ID: 0009_call_recording_key
Revises: 0008_call_answered
Create Date: 2026-07-08
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0009_call_recording_key"
down_revision = "0008_call_answered"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("calls", sa.Column("recording_key", sa.String(500), nullable=True))


def downgrade() -> None:
    op.drop_column("calls", "recording_key")
