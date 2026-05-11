"""Cleanup legacy CRM schema leftovers

Revision ID: 011
Revises: 010
Create Date: 2026-05-08
"""
from alembic import op
import sqlalchemy as sa

revision = "011"
down_revision = "010"
branch_labels = None
depends_on = None


LEGACY_TABLES = (
    "recipient_delivery_logs",
    "delivery_logs",
    "delivery_rules",
    "facebook_lead_forms",
    "clients",
    "bot_users",
    "pixels",
    "site_events",
    "referral_source_stats_daily",
    "tracking_sessions",
    "tracking_events",
    "referral_sources",
    "lead_form_questions",
    "lead_forms",
    "offers",
)


def _table_names() -> set[str]:
    return set(sa.inspect(op.get_bind()).get_table_names())


def _columns(table_name: str) -> set[str]:
    return {c["name"] for c in sa.inspect(op.get_bind()).get_columns(table_name)}


def _drop_table_if_exists(table_name: str) -> None:
    if table_name in _table_names():
        op.drop_table(table_name)


def _copy_expr(source_cols: set[str], column_name: str, fallback: str = "NULL") -> str:
    return column_name if column_name in source_cols else fallback


def _rebuild_leads() -> None:
    if "leads" not in _table_names():
        return

    source_cols = _columns("leads")
    op.execute("DROP TABLE IF EXISTS leads_new")
    op.create_table(
        "leads_new",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("funnel_form_id", sa.Integer, sa.ForeignKey("funnel_forms.id", ondelete="SET NULL"), nullable=True),
        sa.Column("external_lead_id", sa.String(100), nullable=True),
        sa.Column("fb_lead_id", sa.String(100), nullable=True),
        sa.Column("fb_form_id", sa.String(100), nullable=True),
        sa.Column("fb_page_id", sa.String(100), nullable=True),
        sa.Column("form_name", sa.String(255), nullable=True),
        sa.Column("full_name", sa.String(255), nullable=True),
        sa.Column("phone", sa.String(100), nullable=True),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("telegram", sa.String(255), nullable=True),
        sa.Column("tag", sa.String(255), nullable=True),
        sa.Column("lead_created_time", sa.DateTime, nullable=True),
        sa.Column("raw_data_json", sa.Text, nullable=True),
        sa.Column("delivered_admin", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("delivered_telegram", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("delivered_clients", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("delivered_sheet", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("delivered_recipients_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("delivery_error", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("fb_lead_id", name="uq_leads_fb_lead_id"),
    )

    target_cols = [
        "id",
        "funnel_form_id",
        "external_lead_id",
        "fb_lead_id",
        "fb_form_id",
        "fb_page_id",
        "form_name",
        "full_name",
        "phone",
        "email",
        "telegram",
        "tag",
        "lead_created_time",
        "raw_data_json",
        "delivered_admin",
        "delivered_telegram",
        "delivered_clients",
        "delivered_sheet",
        "delivered_recipients_count",
        "delivery_error",
        "created_at",
    ]
    defaults = {
        "delivered_admin": "0",
        "delivered_telegram": "0",
        "delivered_clients": "0",
        "delivered_sheet": "0",
        "delivered_recipients_count": "0",
        "created_at": "CURRENT_TIMESTAMP",
    }
    select_exprs = [
        _copy_expr(source_cols, col, defaults.get(col, "NULL"))
        for col in target_cols
    ]
    op.execute(
        f"INSERT INTO leads_new ({', '.join(target_cols)}) "
        f"SELECT {', '.join(select_exprs)} FROM leads"
    )
    op.drop_table("leads")
    op.rename_table("leads_new", "leads")
    op.create_index("ix_leads_created_at", "leads", ["created_at"])
    op.create_index("ix_leads_external_lead_id", "leads", ["external_lead_id"])
    op.create_index("ix_leads_fb_form_id", "leads", ["fb_form_id"])
    op.create_index("ix_leads_fb_lead_id", "leads", ["fb_lead_id"])
    op.create_index("ix_leads_funnel_form_id", "leads", ["funnel_form_id"])
    op.create_index("ix_leads_funnel_external", "leads", ["funnel_form_id", "external_lead_id"], unique=True)


def upgrade() -> None:
    op.execute("PRAGMA foreign_keys=OFF")
    _rebuild_leads()
    for table_name in LEGACY_TABLES:
        _drop_table_if_exists(table_name)
    op.execute("PRAGMA foreign_keys=ON")


def downgrade() -> None:
    # Legacy CRM tables intentionally are not recreated.
    pass
