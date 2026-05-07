"""initial schema

Revision ID: 001
Revises: 
Create Date: 2024-01-01 00:00:00
"""
from alembic import op
import sqlalchemy as sa

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "clients",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("telegram_username", sa.String(255), nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "offers",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("client_id", sa.Integer, sa.ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("geo", sa.String(100), nullable=True),
        sa.Column("language", sa.String(50), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "lead_forms",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("client_id", sa.Integer, sa.ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("offer_id", sa.Integer, sa.ForeignKey("offers.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(100), unique=True, nullable=False, index=True),
        sa.Column("language", sa.String(50), nullable=False, server_default="ru"),
        sa.Column("welcome_text", sa.Text, nullable=True),
        sa.Column("success_text", sa.Text, nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "lead_form_questions",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("form_id", sa.Integer, sa.ForeignKey("lead_forms.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("position", sa.Integer, nullable=False, server_default="0"),
        sa.Column("question_text", sa.Text, nullable=False),
        sa.Column("question_type", sa.String(50), nullable=False, server_default="text"),
        sa.Column("options_json", sa.Text, nullable=True),
        sa.Column("is_required", sa.Boolean, nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "referral_sources",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("form_id", sa.Integer, sa.ForeignKey("lead_forms.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("code", sa.String(100), unique=True, nullable=False, index=True),
        sa.Column("source_type", sa.String(50), nullable=False, server_default="other"),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "leads",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("client_id", sa.Integer, sa.ForeignKey("clients.id", ondelete="SET NULL"), nullable=True, index=True),
        sa.Column("offer_id", sa.Integer, sa.ForeignKey("offers.id", ondelete="SET NULL"), nullable=True, index=True),
        sa.Column("form_id", sa.Integer, sa.ForeignKey("lead_forms.id", ondelete="SET NULL"), nullable=True, index=True),
        sa.Column("referral_source_id", sa.Integer, sa.ForeignKey("referral_sources.id", ondelete="SET NULL"), nullable=True, index=True),
        sa.Column("telegram_user_id", sa.BigInteger, nullable=False, index=True),
        sa.Column("telegram_username", sa.String(255), nullable=True),
        sa.Column("first_name", sa.String(255), nullable=True),
        sa.Column("last_name", sa.String(255), nullable=True),
        sa.Column("answers_json", sa.Text, nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="new", index=True),
        sa.Column("admin_notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("leads")
    op.drop_table("referral_sources")
    op.drop_table("lead_form_questions")
    op.drop_table("lead_forms")
    op.drop_table("offers")
    op.drop_table("clients")
