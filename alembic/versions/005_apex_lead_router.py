"""simplify to Apex Lead Router

Revision ID: 005
Revises: 004
Create Date: 2026-05-08 00:00:00
"""
from alembic import op
import sqlalchemy as sa

revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None


def _drop_if_exists(table_name: str) -> None:
    bind = op.get_bind()
    if table_name in sa.inspect(bind).get_table_names():
        op.drop_table(table_name)


def upgrade() -> None:
    for table_name in [
        "preland_events",
        "prelands",
        "delivery_logs",
        "delivery_rules",
        "leads",
        "facebook_lead_forms",
        "pixels",
        "bot_users",
        "site_events",
        "referral_source_stats_daily",
        "tracking_sessions",
        "tracking_events",
        "referral_sources",
        "lead_form_questions",
        "lead_forms",
        "offers",
        "clients",
    ]:
        _drop_if_exists(table_name)

    op.create_table(
        "clients",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("telegram_ids_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("emails_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_clients_name", "clients", ["name"])
    op.create_index("ix_clients_status", "clients", ["status"])

    op.create_table(
        "facebook_lead_forms",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("fb_page_id", sa.String(100), nullable=False),
        sa.Column("fb_form_id", sa.String(100), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("client_id", sa.Integer(), sa.ForeignKey("clients.id", ondelete="CASCADE"), nullable=False),
        sa.Column("offer_name", sa.String(255), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("fb_form_id", name="uq_facebook_lead_forms_fb_form_id"),
    )
    op.create_index("ix_facebook_lead_forms_client_id", "facebook_lead_forms", ["client_id"])
    op.create_index("ix_facebook_lead_forms_fb_form_id", "facebook_lead_forms", ["fb_form_id"])
    op.create_index("ix_facebook_lead_forms_fb_page_id", "facebook_lead_forms", ["fb_page_id"])
    op.create_index("ix_facebook_lead_forms_status", "facebook_lead_forms", ["status"])

    op.create_table(
        "leads",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("source_type", sa.String(50), nullable=False, server_default="facebook_lead_form"),
        sa.Column("fb_lead_id", sa.String(100), nullable=True),
        sa.Column("fb_page_id", sa.String(100), nullable=True),
        sa.Column("fb_form_id", sa.String(100), nullable=True),
        sa.Column("client_id", sa.Integer(), sa.ForeignKey("clients.id", ondelete="SET NULL"), nullable=True),
        sa.Column("form_id", sa.Integer(), sa.ForeignKey("facebook_lead_forms.id", ondelete="SET NULL"), nullable=True),
        sa.Column("raw_data_json", sa.Text(), nullable=True),
        sa.Column("normalized_data_json", sa.Text(), nullable=True),
        sa.Column("full_name", sa.String(255), nullable=True),
        sa.Column("phone", sa.String(100), nullable=True),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("telegram", sa.String(255), nullable=True),
        sa.Column("status", sa.String(30), nullable=False, server_default="new"),
        sa.Column("delivered_telegram", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("delivered_email", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("delivered_sheet", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("fb_lead_id", name="uq_leads_fb_lead_id"),
    )
    op.create_index("ix_leads_client_id", "leads", ["client_id"])
    op.create_index("ix_leads_fb_form_id", "leads", ["fb_form_id"])
    op.create_index("ix_leads_fb_lead_id", "leads", ["fb_lead_id"])
    op.create_index("ix_leads_fb_page_id", "leads", ["fb_page_id"])
    op.create_index("ix_leads_form_id", "leads", ["form_id"])
    op.create_index("ix_leads_source_type", "leads", ["source_type"])
    op.create_index("ix_leads_status", "leads", ["status"])

    op.create_table(
        "delivery_rules",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("source_type", sa.String(50), nullable=False),
        sa.Column("source_id", sa.Integer(), nullable=False),
        sa.Column("client_id", sa.Integer(), sa.ForeignKey("clients.id", ondelete="CASCADE"), nullable=False),
        sa.Column("send_to_admin", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("telegram_ids_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("emails_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("google_sheet_id", sa.String(255), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("source_type", "source_id", name="uq_delivery_rules_source"),
    )
    op.create_index("ix_delivery_rules_client_id", "delivery_rules", ["client_id"])
    op.create_index("ix_delivery_rules_source_id", "delivery_rules", ["source_id"])
    op.create_index("ix_delivery_rules_source_type", "delivery_rules", ["source_type"])
    op.create_index("ix_delivery_rules_status", "delivery_rules", ["status"])

    op.create_table(
        "delivery_logs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("lead_id", sa.Integer(), sa.ForeignKey("leads.id", ondelete="CASCADE"), nullable=False),
        sa.Column("channel", sa.String(50), nullable=False),
        sa.Column("recipient", sa.String(255), nullable=True),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_delivery_logs_channel", "delivery_logs", ["channel"])
    op.create_index("ix_delivery_logs_created_at", "delivery_logs", ["created_at"])
    op.create_index("ix_delivery_logs_lead_id", "delivery_logs", ["lead_id"])
    op.create_index("ix_delivery_logs_status", "delivery_logs", ["status"])

    op.create_table(
        "prelands",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(100), nullable=False),
        sa.Column("url", sa.String(500), nullable=True),
        sa.Column("client_id", sa.Integer(), sa.ForeignKey("clients.id", ondelete="SET NULL"), nullable=True),
        sa.Column("offer_name", sa.String(255), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("slug", name="uq_prelands_slug"),
    )
    op.create_index("ix_prelands_client_id", "prelands", ["client_id"])
    op.create_index("ix_prelands_slug", "prelands", ["slug"])
    op.create_index("ix_prelands_status", "prelands", ["status"])

    op.create_table(
        "preland_events",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("preland_id", sa.Integer(), sa.ForeignKey("prelands.id", ondelete="CASCADE"), nullable=False),
        sa.Column("event_type", sa.String(30), nullable=False),
        sa.Column("button_id", sa.String(100), nullable=True),
        sa.Column("visitor_id", sa.String(100), nullable=True),
        sa.Column("ip_hash", sa.String(64), nullable=True),
        sa.Column("user_agent", sa.String(500), nullable=True),
        sa.Column("referer", sa.String(500), nullable=True),
        sa.Column("utm_source", sa.String(255), nullable=True),
        sa.Column("utm_campaign", sa.String(255), nullable=True),
        sa.Column("utm_content", sa.String(255), nullable=True),
        sa.Column("metadata_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_preland_events_button_id", "preland_events", ["button_id"])
    op.create_index("ix_preland_events_created_at", "preland_events", ["created_at"])
    op.create_index("ix_preland_events_event_type", "preland_events", ["event_type"])
    op.create_index("ix_preland_events_preland_id", "preland_events", ["preland_id"])
    op.create_index("ix_preland_events_visitor_id", "preland_events", ["visitor_id"])


def downgrade() -> None:
    for table_name in [
        "preland_events",
        "prelands",
        "delivery_logs",
        "delivery_rules",
        "leads",
        "facebook_lead_forms",
        "clients",
    ]:
        _drop_if_exists(table_name)
