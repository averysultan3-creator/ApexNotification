"""Add unique constraint on client_recipients(funnel_form_id, telegram_user_id)

Revision ID: 012
Revises: 011
Create Date: 2026-05-09
"""
from alembic import op

revision = "012"
down_revision = "011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("client_recipients") as batch_op:
        batch_op.create_unique_constraint(
            "uq_client_recipients_form_user",
            ["funnel_form_id", "telegram_user_id"],
        )


def downgrade() -> None:
    with op.batch_alter_table("client_recipients") as batch_op:
        batch_op.drop_constraint("uq_client_recipients_form_user", type_="unique")
