"""MVP cleanup - simplified schema

Revision ID: 006
Revises: 005
Create Date: 2026-05-08
"""
from alembic import op
import sqlalchemy as sa

revision = "006"
down_revision = "005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    # 1. Drop tables we no longer need
    for t in ("delivery_logs", "delivery_rules"):
        if t in tables:
            op.drop_table(t)

    # 2. clients: add google_sheet_id/name, drop emails_json/notes/updated_at
    if "clients" in tables:
        existing = {c["name"] for c in inspector.get_columns("clients")}
        add_sheet = "google_sheet_id" not in existing
        drop_cols = [c for c in ("emails_json", "notes", "updated_at") if c in existing]
        with op.batch_alter_table("clients") as batch_op:
            if add_sheet:
                batch_op.add_column(sa.Column("google_sheet_id", sa.String(200), nullable=True))
                batch_op.add_column(sa.Column("google_sheet_name", sa.String(200), nullable=True))
            for col in drop_cols:
                batch_op.drop_column(col)

    # 3. facebook_lead_forms: drop updated_at
    if "facebook_lead_forms" in tables:
        existing = {c["name"] for c in inspector.get_columns("facebook_lead_forms")}
        drop_cols = [c for c in ("updated_at",) if c in existing]
        if drop_cols:
            with op.batch_alter_table("facebook_lead_forms") as batch_op:
                for col in drop_cols:
                    batch_op.drop_column(col)

    # 4. leads: full recreate (column rename form_id→facebook_form_id + schema change)
    if "leads" in tables:
        op.drop_table("leads")
    op.create_table(
        "leads",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("client_id", sa.Integer(),
                  sa.ForeignKey("clients.id", ondelete="SET NULL"), nullable=True),
        sa.Column("facebook_form_id", sa.Integer(),
                  sa.ForeignKey("facebook_lead_forms.id", ondelete="SET NULL"), nullable=True),
        sa.Column("fb_lead_id", sa.String(100), nullable=True),
        sa.Column("full_name", sa.String(255), nullable=True),
        sa.Column("phone", sa.String(100), nullable=True),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("raw_data_json", sa.Text(), nullable=True),
        sa.Column("delivered_telegram", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("delivered_sheet", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("delivery_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("fb_lead_id", name="uq_leads_fb_lead_id"),
    )
    op.create_index("ix_leads_client_id", "leads", ["client_id"])
    op.create_index("ix_leads_facebook_form_id", "leads", ["facebook_form_id"])
    op.create_index("ix_leads_fb_lead_id", "leads", ["fb_lead_id"])
    op.create_index("ix_leads_created_at", "leads", ["created_at"])

    # 5. prelands: drop client_id, offer_name, updated_at
    if "prelands" in tables:
        existing = {c["name"] for c in inspector.get_columns("prelands")}
        drop_cols = [c for c in ("client_id", "offer_name", "updated_at") if c in existing]
        if drop_cols:
            indexes = {idx["name"] for idx in inspector.get_indexes("prelands")}
            if "ix_prelands_client_id" in indexes:
                op.drop_index("ix_prelands_client_id", table_name="prelands")
            with op.batch_alter_table("prelands") as batch_op:
                for col in drop_cols:
                    batch_op.drop_column(col)

    # 6. preland_events: full recreate (simplified columns)
    if "preland_events" in tables:
        op.drop_table("preland_events")
    op.create_table(
        "preland_events",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("preland_id", sa.Integer(),
                  sa.ForeignKey("prelands.id", ondelete="CASCADE"), nullable=False),
        sa.Column("event_type", sa.String(30), nullable=False),
        sa.Column("button_id", sa.String(100), nullable=True),
        sa.Column("utm_source", sa.String(255), nullable=True),
        sa.Column("utm_campaign", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_preland_events_preland_id", "preland_events", ["preland_id"])
    op.create_index("ix_preland_events_event_type", "preland_events", ["event_type"])
    op.create_index("ix_preland_events_created_at", "preland_events", ["created_at"])
    op.create_index("ix_preland_events_button_id", "preland_events", ["button_id"])


def downgrade() -> None:
    pass
