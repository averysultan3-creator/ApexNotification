"""003 — site_events table for prelanding analytics

Revision ID: 003
Revises: 002
Create Date: 2026-05-07 00:00:00
"""
from alembic import op
import sqlalchemy as sa

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "site_events",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("event_type", sa.String(20), nullable=False),
        sa.Column("session_id", sa.String(36), nullable=False),
        sa.Column("site_id", sa.String(100), nullable=True),
        sa.Column("ref_code", sa.String(100), nullable=True),
        sa.Column("time_spent", sa.Integer, nullable=True),
        sa.Column("ua_hash", sa.String(8), nullable=True),
        sa.Column("date", sa.String(10), nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=False),
    )
    op.create_index("ix_site_events_session", "site_events", ["session_id"])
    op.create_index("ix_site_events_site_id", "site_events", ["site_id"])
    op.create_index("ix_site_events_date", "site_events", ["date"])
    op.create_index("ix_site_event_type_date", "site_events", ["event_type", "date"])
    op.create_index("ix_site_event_site_date", "site_events", ["site_id", "date"])


def downgrade() -> None:
    op.drop_table("site_events")
