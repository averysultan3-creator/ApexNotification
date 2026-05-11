"""Google Sheet lead bridge columns

Revision ID: 009
Revises: 008
Create Date: 2026-05-08
"""
from alembic import op
import sqlalchemy as sa

revision = "009"
down_revision = "008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    lead_cols = {c["name"] for c in inspector.get_columns("leads")}

    columns = [
        ("external_lead_id", sa.Column("external_lead_id", sa.String(100), nullable=True)),
        ("telegram", sa.Column("telegram", sa.String(255), nullable=True)),
        ("form_name", sa.Column("form_name", sa.String(255), nullable=True)),
        ("lead_created_time", sa.Column("lead_created_time", sa.DateTime, nullable=True)),
        ("delivered_recipients_count", sa.Column(
            "delivered_recipients_count", sa.Integer, nullable=False, server_default="0"
        )),
    ]
    for name, column in columns:
        if name not in lead_cols:
            op.add_column("leads", column)

    existing_indexes = {idx["name"] for idx in inspector.get_indexes("leads")}
    if "ix_leads_external_lead_id" not in existing_indexes:
        op.create_index("ix_leads_external_lead_id", "leads", ["external_lead_id"])
    if "ix_leads_funnel_external" not in existing_indexes:
        op.create_index(
            "ix_leads_funnel_external",
            "leads",
            ["funnel_form_id", "external_lead_id"],
            unique=True,
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    lead_cols = {c["name"] for c in inspector.get_columns("leads")}
    indexes = {idx["name"] for idx in inspector.get_indexes("leads")}

    for idx in ("ix_leads_funnel_external", "ix_leads_external_lead_id"):
        if idx in indexes:
            op.drop_index(idx, table_name="leads")

    for col in ("external_lead_id", "telegram", "form_name", "lead_created_time", "delivered_recipients_count"):
        if col in lead_cols:
            op.drop_column("leads", col)
