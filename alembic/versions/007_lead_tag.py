"""Add tag column to leads

Revision ID: 007
Revises: 006
Create Date: 2026-05-08
"""
from alembic import op
import sqlalchemy as sa

revision = "007"
down_revision = "006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing = {c["name"] for c in inspector.get_columns("leads")}
    if "tag" not in existing:
        op.add_column("leads", sa.Column("tag", sa.String(255), nullable=True))


def downgrade() -> None:
    op.drop_column("leads", "tag")
