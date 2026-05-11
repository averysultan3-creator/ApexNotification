"""Add lead_delivery_history table

Revision ID: 010
Revises: 009
Create Date: 2026-05-08
"""
from alembic import op
import sqlalchemy as sa

revision = "010"
down_revision = "009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if "lead_delivery_history" not in tables:
        op.create_table(
            "lead_delivery_history",
            sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
            sa.Column(
                "lead_id", sa.Integer,
                sa.ForeignKey("leads.id", ondelete="CASCADE"), nullable=False,
            ),
            sa.Column("recipient_telegram_id", sa.BigInteger, nullable=False),
            sa.Column("delivery_type", sa.String(20), nullable=False),
            sa.Column("status", sa.String(20), nullable=False),
            sa.Column("error_message", sa.Text, nullable=True),
            sa.Column("created_at", sa.DateTime, server_default=sa.func.now(), nullable=False),
            sa.UniqueConstraint(
                "lead_id", "recipient_telegram_id", "delivery_type",
                name="uq_ldh_lead_recip_type",
            ),
        )
        op.create_index("ix_ldh_lead_id", "lead_delivery_history", ["lead_id"])
        op.create_index(
            "ix_ldh_recipient_telegram_id", "lead_delivery_history", ["recipient_telegram_id"]
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "lead_delivery_history" in set(inspector.get_table_names()):
        op.drop_index("ix_ldh_recipient_telegram_id", table_name="lead_delivery_history")
        op.drop_index("ix_ldh_lead_id", table_name="lead_delivery_history")
        op.drop_table("lead_delivery_history")
