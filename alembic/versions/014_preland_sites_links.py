"""Add preland_sites, preland_links tables; update preland_events

Revision ID: 014
Revises: 013
Create Date: 2026-05-10
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "014"
down_revision = "013"
branch_labels = None
depends_on = None


def _column_exists(table: str, column: str) -> bool:
    bind = op.get_bind()
    insp = inspect(bind)
    return column in {c["name"] for c in insp.get_columns(table)}


def _table_exists(table: str) -> bool:
    bind = op.get_bind()
    insp = inspect(bind)
    return table in insp.get_table_names()


def upgrade() -> None:
    # --- preland_sites --------------------------------------------------
    if not _table_exists("preland_sites"):
        op.create_table(
            "preland_sites",
            sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
            sa.Column("name", sa.String(255), nullable=False),
            sa.Column("base_url", sa.String(500), nullable=False),
            sa.Column("status", sa.String(20), nullable=False, server_default="active"),
            sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        )

    # --- preland_links --------------------------------------------------
    if not _table_exists("preland_links"):
        op.create_table(
            "preland_links",
            sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
            sa.Column("site_id", sa.Integer, sa.ForeignKey("preland_sites.id", ondelete="CASCADE"),
                      nullable=False),
            sa.Column("display_name", sa.String(300), nullable=False),
            sa.Column("slug", sa.String(120), nullable=False, unique=True),
            sa.Column("country", sa.String(10), nullable=True),
            sa.Column("placement", sa.String(50), nullable=True),
            sa.Column("audience", sa.String(100), nullable=True),
            sa.Column("angle", sa.String(100), nullable=True),
            sa.Column("final_url", sa.String(600), nullable=False),
            sa.Column("status", sa.String(20), nullable=False, server_default="active"),
            sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        )
        op.create_index("ix_preland_links_slug", "preland_links", ["slug"], unique=True)
        op.create_index("ix_preland_links_site_id", "preland_links", ["site_id"])

    # --- preland_events: add new columns --------------------------------
    if not _column_exists("preland_events", "link_id"):
        # SQLite doesn't support ALTER TABLE ADD COLUMN with FK constraint.
        # Add as plain Integer (FK is declared in the ORM model; SQLite doesn't enforce FKs by default).
        op.add_column("preland_events", sa.Column("link_id", sa.Integer, nullable=True))
        op.create_index("ix_preland_events_link_id", "preland_events", ["link_id"])

    if not _column_exists("preland_events", "slug"):
        op.add_column("preland_events",
                      sa.Column("slug", sa.String(120), nullable=True))
        op.create_index("ix_preland_events_slug", "preland_events", ["slug"])

    if not _column_exists("preland_events", "referrer"):
        op.add_column("preland_events",
                      sa.Column("referrer", sa.String(500), nullable=True))

    # Make preland_id nullable (was NOT NULL)
    # SQLite doesn't support ALTER COLUMN, so we skip for sqlite
    # (the column is already nullable in new schema; existing rows keep their value)

    # --- preland_events: add visitor_id if somehow missing --------------
    if not _column_exists("preland_events", "visitor_id"):
        op.add_column("preland_events",
                      sa.Column("visitor_id", sa.String(64), nullable=True))

    # --- prelands: add display_name if somehow missing ------------------
    if not _column_exists("prelands", "display_name"):
        op.add_column("prelands",
                      sa.Column("display_name", sa.String(300), nullable=True))


def downgrade() -> None:
    # Drop new tables (events FK will cascade or be gone)
    if _table_exists("preland_links"):
        op.drop_index("ix_preland_links_slug", table_name="preland_links")
        op.drop_index("ix_preland_links_site_id", table_name="preland_links")
        op.drop_table("preland_links")
    if _table_exists("preland_sites"):
        op.drop_table("preland_sites")
