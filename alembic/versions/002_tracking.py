"""002 — Tracking tables + UTM fields on referral_sources

Revision ID: 002
Revises: 001
Create Date: 2026-05-07 00:00:00
"""
from alembic import op
import sqlalchemy as sa

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── referral_sources: UTM fields ──────────────────────────────────────────
    op.add_column("referral_sources", sa.Column("traffic_source", sa.String(100), nullable=True))
    op.add_column("referral_sources", sa.Column("campaign_name", sa.String(255), nullable=True))
    op.add_column("referral_sources", sa.Column("ad_account", sa.String(255), nullable=True))
    op.add_column("referral_sources", sa.Column("creative_name", sa.String(255), nullable=True))
    op.add_column("referral_sources", sa.Column("placement", sa.String(255), nullable=True))
    op.add_column("referral_sources", sa.Column("utm_geo", sa.String(100), nullable=True))

    # ── tracking_events ───────────────────────────────────────────────────────
    op.create_table(
        "tracking_events",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("event_type", sa.String(50), nullable=False, index=True),
        sa.Column("client_id", sa.Integer,
                  sa.ForeignKey("clients.id", ondelete="SET NULL"), nullable=True, index=True),
        sa.Column("offer_id", sa.Integer,
                  sa.ForeignKey("offers.id", ondelete="SET NULL"), nullable=True, index=True),
        sa.Column("form_id", sa.Integer,
                  sa.ForeignKey("lead_forms.id", ondelete="SET NULL"), nullable=True, index=True),
        sa.Column("referral_source_id", sa.Integer,
                  sa.ForeignKey("referral_sources.id", ondelete="SET NULL"), nullable=True, index=True),
        sa.Column("lead_id", sa.Integer,
                  sa.ForeignKey("leads.id", ondelete="SET NULL"), nullable=True),
        sa.Column("telegram_user_id", sa.BigInteger, nullable=True, index=True),
        sa.Column("telegram_username", sa.String(255), nullable=True),
        sa.Column("session_id", sa.String(100), nullable=False, index=True),
        sa.Column("question_id", sa.Integer,
                  sa.ForeignKey("lead_form_questions.id", ondelete="SET NULL"), nullable=True),
        sa.Column("step_number", sa.Integer, nullable=True),
        sa.Column("metadata_json", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now(),
                  index=True),
    )

    # ── tracking_sessions ─────────────────────────────────────────────────────
    op.create_table(
        "tracking_sessions",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("session_id", sa.String(100), unique=True, nullable=False, index=True),
        sa.Column("client_id", sa.Integer,
                  sa.ForeignKey("clients.id", ondelete="SET NULL"), nullable=True, index=True),
        sa.Column("offer_id", sa.Integer,
                  sa.ForeignKey("offers.id", ondelete="SET NULL"), nullable=True, index=True),
        sa.Column("form_id", sa.Integer,
                  sa.ForeignKey("lead_forms.id", ondelete="SET NULL"), nullable=True, index=True),
        sa.Column("referral_source_id", sa.Integer,
                  sa.ForeignKey("referral_sources.id", ondelete="SET NULL"), nullable=True, index=True),
        sa.Column("lead_id", sa.Integer,
                  sa.ForeignKey("leads.id", ondelete="SET NULL"), nullable=True),
        sa.Column("telegram_user_id", sa.BigInteger, nullable=True, index=True),
        sa.Column("telegram_username", sa.String(255), nullable=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="started"),
        sa.Column("current_step", sa.Integer, nullable=False, server_default="0"),
        sa.Column("total_steps", sa.Integer, nullable=False, server_default="0"),
        sa.Column("is_completed", sa.Boolean, nullable=False, server_default="0"),
        sa.Column("is_duplicate", sa.Boolean, nullable=False, server_default="0"),
        sa.Column("started_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime, nullable=True),
        sa.Column("last_event_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )

    # ── referral_source_stats_daily ───────────────────────────────────────────
    op.create_table(
        "referral_source_stats_daily",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("date", sa.String(10), nullable=False, index=True),
        sa.Column("client_id", sa.Integer,
                  sa.ForeignKey("clients.id", ondelete="SET NULL"), nullable=True, index=True),
        sa.Column("offer_id", sa.Integer,
                  sa.ForeignKey("offers.id", ondelete="SET NULL"), nullable=True, index=True),
        sa.Column("form_id", sa.Integer,
                  sa.ForeignKey("lead_forms.id", ondelete="SET NULL"), nullable=True, index=True),
        sa.Column("referral_source_id", sa.Integer,
                  sa.ForeignKey("referral_sources.id", ondelete="SET NULL"), nullable=True, index=True),
        sa.Column("clicks", sa.Integer, nullable=False, server_default="0"),
        sa.Column("bot_starts", sa.Integer, nullable=False, server_default="0"),
        sa.Column("form_views", sa.Integer, nullable=False, server_default="0"),
        sa.Column("form_starts", sa.Integer, nullable=False, server_default="0"),
        sa.Column("form_completions", sa.Integer, nullable=False, server_default="0"),
        sa.Column("leads_created", sa.Integer, nullable=False, server_default="0"),
        sa.Column("duplicates", sa.Integer, nullable=False, server_default="0"),
        sa.Column("contacted", sa.Integer, nullable=False, server_default="0"),
        sa.Column("qualified", sa.Integer, nullable=False, server_default="0"),
        sa.Column("rejected", sa.Integer, nullable=False, server_default="0"),
        sa.Column("approved", sa.Integer, nullable=False, server_default="0"),
        sa.Column("updated_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("referral_source_stats_daily")
    op.drop_table("tracking_sessions")
    op.drop_table("tracking_events")
    op.drop_column("referral_sources", "utm_geo")
    op.drop_column("referral_sources", "placement")
    op.drop_column("referral_sources", "creative_name")
    op.drop_column("referral_sources", "ad_account")
    op.drop_column("referral_sources", "campaign_name")
    op.drop_column("referral_sources", "traffic_source")
