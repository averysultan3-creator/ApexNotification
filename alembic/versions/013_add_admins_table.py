"""Add admins table for DB-based admin management

Revision ID: 013
Revises: 012
Create Date: 2026-05-09
"""
from alembic import op
import sqlalchemy as sa

revision = "013"
down_revision = "012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "admins",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("telegram_user_id", sa.BigInteger, nullable=False, unique=True),
        sa.Column("username", sa.String(255), nullable=True),
        sa.Column("first_name", sa.String(255), nullable=True),
        sa.Column("added_by_command", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_admins_telegram_user_id", "admins", ["telegram_user_id"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_admins_telegram_user_id", table_name="admins")
    op.drop_table("admins")
