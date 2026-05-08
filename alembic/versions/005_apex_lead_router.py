"""005_apex_lead_router

Revision ID: 005
Revises: 004
Create Date: 2026-05-08
"""
from alembic import op
import sqlalchemy as sa

revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "clients",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("telegram_ids_json", sa.Text, server_default="[]"),
        sa.Column("emails_json", sa.Text, server_default="[]"),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("status", sa.String(20), server_default="active"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )

    op.create_table(
        "facebook_lead_forms",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("fb_page_id", sa.String(100), nullable=False),
        sa.Column("fb_form_id", sa.String(100), nullable=False, unique=True),
        sa.Column("client_id", sa.Integer, sa.ForeignKey("clients.id", ondelete="SET NULL"), nullable=True),
        sa.Column("offer_name", sa.String(255), nullable=True),
        sa.Column("status", sa.String(20), server_default="active"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )

    op.create_table(
        "leads",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("source_type", sa.String(50), server_default="facebook"),
        sa.Column("fb_lead_id", sa.String(100), nullable=True, unique=True),
        sa.Column("fb_page_id", sa.String(100), nullable=True),
        sa.Column("fb_form_id", sa.String(100), nullable=True),
        sa.Column("client_id", sa.Integer, sa.ForeignKey("clients.id", ondelete="SET NULL"), nullable=True),
        sa.Column("form_id", sa.Integer, sa.ForeignKey("facebook_lead_forms.id", ondelete="SET NULL"), nullable=True),
        sa.Column("raw_data_json", sa.Text, nullable=True),
        sa.Column("normalized_data_json", sa.Text, nullable=True),
        sa.Column("full_name", sa.String(255), nullable=True),
        sa.Column("phone", sa.String(50), nullable=True),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("telegram", sa.String(100), nullable=True),
        sa.Column("status", sa.String(30), server_default="new"),
        sa.Column("delivered_telegram", sa.Boolean, server_default="0"),
        sa.Column("delivered_email", sa.Boolean, server_default="0"),
        sa.Column("delivered_sheet", sa.Boolean, server_default="0"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )

    op.create_table(
        "delivery_rules",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("source_type", sa.String(50), server_default="facebook_form"),
        sa.Column("source_id", sa.Integer, nullable=False),
        sa.Column("client_id", sa.Integer, sa.ForeignKey("clients.id", ondelete="SET NULL"), nullable=True),
        sa.Column("send_to_admin", sa.Boolean, server_default="1"),
        sa.Column("telegram_ids_json", sa.Text, server_default="[]"),
        sa.Column("emails_json", sa.Text, server_default="[]"),
        sa.Column("google_sheet_id", sa.String(255), nullable=True),
        sa.Column("status", sa.String(20), server_default="active"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )

    op.create_table(
        "delivery_logs",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("lead_id", sa.Integer, sa.ForeignKey("leads.id", ondelete="CASCADE"), nullable=False),
        sa.Column("channel", sa.String(50), nullable=False),
        sa.Column("recipient", sa.String(255), nullable=True),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    op.create_table(
        "prelands",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(100), nullable=False, unique=True),
        sa.Column("url", sa.String(500), nullable=True),
        sa.Column("client_id", sa.Integer, sa.ForeignKey("clients.id", ondelete="SET NULL"), nullable=True),
        sa.Column("offer_name", sa.String(255), nullable=True),
        sa.Column("status", sa.String(20), server_default="active"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )

    op.create_table(
        "preland_events",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("preland_id", sa.Integer, sa.ForeignKey("prelands.id", ondelete="CASCADE"), nullable=False),
        sa.Column("event_type", sa.String(50), nullable=False),
        sa.Column("button_id", sa.String(100), nullable=True),
        sa.Column("visitor_id", sa.String(100), nullable=True),
        sa.Column("ip_hash", sa.String(64), nullable=True),
        sa.Column("user_agent", sa.String(500), nullable=True),
        sa.Column("referer", sa.String(500), nullable=True),
        sa.Column("utm_source", sa.String(100), nullable=True),
        sa.Column("utm_campaign", sa.String(100), nullable=True),
        sa.Column("utm_content", sa.String(100), nullable=True),
        sa.Column("metadata_json", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("preland_events")
    op.drop_table("prelands")
    op.drop_table("delivery_logs")
    op.drop_table("delivery_rules")
    op.drop_table("leads")
    op.drop_table("facebook_lead_forms")
    op.drop_table("clients")
