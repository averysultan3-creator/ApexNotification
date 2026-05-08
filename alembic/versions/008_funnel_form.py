"""FunnelForm + ClientRecipient - new architecture

Revision ID: 008
Revises: 007
Create Date: 2026-05-08
"""
from alembic import op
import sqlalchemy as sa

revision = "008"
down_revision = "007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    # 1. funnel_forms
    if "funnel_forms" not in tables:
        op.create_table(
            "funnel_forms",
            sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
            sa.Column("form_name", sa.String(255), nullable=False),
            sa.Column("client_label", sa.String(255), nullable=True),
            sa.Column("offer_name", sa.String(255), nullable=True),
            sa.Column("tag", sa.String(255), nullable=True),
            sa.Column("fb_form_id", sa.String(100), nullable=False, unique=True),
            sa.Column("fb_page_id", sa.String(100), nullable=True),
            sa.Column("verify_token", sa.String(100), nullable=False, unique=True),
            sa.Column("join_code", sa.String(100), nullable=False, unique=True),
            sa.Column("google_sheet_id", sa.String(200), nullable=True),
            sa.Column("google_sheet_name", sa.String(200), nullable=False, server_default="Leads"),
            sa.Column("apps_script_web_app_url", sa.String(500), nullable=True),
            sa.Column("status", sa.String(20), nullable=False, server_default="active"),
            sa.Column("created_at", sa.DateTime, server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime, server_default=sa.func.now(), nullable=False),
        )
        op.create_index("ix_funnel_forms_fb_form_id", "funnel_forms", ["fb_form_id"])
        op.create_index("ix_funnel_forms_verify_token", "funnel_forms", ["verify_token"])
        op.create_index("ix_funnel_forms_status", "funnel_forms", ["status"])

    # 2. client_recipients
    if "client_recipients" not in tables:
        op.create_table(
            "client_recipients",
            sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
            sa.Column("funnel_form_id", sa.Integer, sa.ForeignKey("funnel_forms.id", ondelete="CASCADE"), nullable=False),
            sa.Column("telegram_user_id", sa.BigInteger, nullable=False),
            sa.Column("telegram_username", sa.String(255), nullable=True),
            sa.Column("first_name", sa.String(255), nullable=True),
            sa.Column("status", sa.String(20), nullable=False, server_default="active"),
            sa.Column("joined_at", sa.DateTime, server_default=sa.func.now(), nullable=False),
            sa.Column("last_sent_lead_id", sa.Integer, nullable=True),
        )
        op.create_index("ix_client_recipients_funnel_form_id", "client_recipients", ["funnel_form_id"])
        op.create_index("ix_client_recipients_telegram_user_id", "client_recipients", ["telegram_user_id"])

    # 3. Update leads table — add new columns (old ones stay, SQLite-safe)
    if "leads" in tables:
        existing_cols = {c["name"] for c in inspector.get_columns("leads")}
        new_cols = {
            "funnel_form_id": sa.Column("funnel_form_id", sa.Integer, nullable=True),
            "fb_form_id": sa.Column("fb_form_id", sa.String(100), nullable=True),
            "fb_page_id": sa.Column("fb_page_id", sa.String(100), nullable=True),
            "delivered_admin": sa.Column("delivered_admin", sa.Boolean, nullable=False, server_default="0"),
            "delivered_clients": sa.Column("delivered_clients", sa.Boolean, nullable=False, server_default="0"),
        }
        for col_name, col_def in new_cols.items():
            if col_name not in existing_cols:
                op.add_column("leads", col_def)
        # Create index on funnel_form_id if not exists
        try:
            op.create_index("ix_leads_funnel_form_id", "leads", ["funnel_form_id"])
        except Exception:
            pass
        try:
            op.create_index("ix_leads_fb_form_id", "leads", ["fb_form_id"])
        except Exception:
            pass


def downgrade() -> None:
    op.drop_table("client_recipients")
    op.drop_table("funnel_forms")
