"""015 — fix preland_events: make preland_id nullable in SQLite.

Migration 014 intentionally skipped this for SQLite. This migration
uses batch_alter_table to recreate the table with preland_id as nullable.

Revision ID: 015
Revises: 014
Create Date: 2026-05-12
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect


def _is_sqlite() -> bool:
    bind = op.get_bind()
    return bind.dialect.name == "sqlite"


def _preland_id_notnull() -> bool:
    bind = op.get_bind()
    insp = inspect(bind)
    for col in insp.get_columns("preland_events"):
        if col["name"] == "preland_id":
            return not col.get("nullable", True)
    return False


revision = "015"
down_revision = "014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if not _is_sqlite():
        # Non-SQLite: standard ALTER COLUMN
        with op.batch_alter_table("preland_events") as batch_op:
            batch_op.alter_column(
                "preland_id",
                existing_type=sa.Integer(),
                nullable=True,
            )
        return

    if not _preland_id_notnull():
        # Already nullable, nothing to do
        return

    # SQLite: recreate the table with preland_id nullable
    with op.batch_alter_table("preland_events", recreate="always") as batch_op:
        batch_op.alter_column(
            "preland_id",
            existing_type=sa.Integer(),
            nullable=True,
        )


def downgrade() -> None:
    pass  # Do not restore NOT NULL - too risky for existing data
