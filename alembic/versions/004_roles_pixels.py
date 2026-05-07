"""004 — bot_users and pixels tables."""
import sqlalchemy as sa
from alembic import op

revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "bot_users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("telegram_user_id", sa.BigInteger(), nullable=False),
        sa.Column("telegram_username", sa.String(100), nullable=True),
        sa.Column(
            "role", sa.String(20), nullable=False, server_default="client_admin"
        ),
        sa.Column(
            "client_id",
            sa.Integer(),
            sa.ForeignKey("clients.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "is_active", sa.Boolean(), nullable=False, server_default=sa.true()
        ),
        sa.Column("notes", sa.String(500), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_bot_user_tg_id", "bot_users", ["telegram_user_id"], unique=True
    )

    op.create_table(
        "pixels",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("pixel_type", sa.String(20), nullable=False),
        sa.Column("pixel_value", sa.String(200), nullable=True),
        sa.Column(
            "scope_type", sa.String(20), nullable=False, server_default="global"
        ),
        sa.Column("scope_id", sa.Integer(), nullable=True),
        sa.Column(
            "events",
            sa.Text(),
            nullable=False,
            server_default="bot_started,form_started,lead_created,approved",
        ),
        sa.Column(
            "is_active", sa.Boolean(), nullable=False, server_default=sa.true()
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )


def downgrade() -> None:
    op.drop_table("pixels")
    op.drop_index("ix_bot_user_tg_id", table_name="bot_users")
    op.drop_table("bot_users")
