"""005 — fix preland_events: make preland_id nullable."""
import sqlalchemy as sa
from alembic import op

revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # SQLite does not support ALTER COLUMN, so we recreate the table.
    # The original table had preland_id NOT NULL (from migration 001).
    # We need it to be nullable so events can be saved without a preland/link.
    with op.batch_alter_table("preland_events", recreate="always") as batch_op:
        batch_op.alter_column(
            "preland_id",
            existing_type=sa.Integer(),
            nullable=True,
        )


def downgrade() -> None:
    with op.batch_alter_table("preland_events", recreate="always") as batch_op:
        batch_op.alter_column(
            "preland_id",
            existing_type=sa.Integer(),
            nullable=False,
        )
