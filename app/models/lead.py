from __future__ import annotations
from datetime import datetime
from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database import Base


class Lead(Base):
    __tablename__ = "leads"
    __table_args__ = (UniqueConstraint("fb_lead_id", name="uq_leads_fb_lead_id"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    funnel_form_id: Mapped[int | None] = mapped_column(
        ForeignKey("funnel_forms.id", ondelete="SET NULL"), nullable=True, index=True
    )
    fb_lead_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    fb_form_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    fb_page_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(100), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    tag: Mapped[str | None] = mapped_column(String(255), nullable=True)
    raw_data_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    delivered_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    delivered_clients: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    delivered_sheet: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    delivery_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False, index=True
    )

    funnel_form: Mapped["FunnelForm | None"] = relationship(
        "FunnelForm", back_populates="leads", lazy="selectin",
        foreign_keys=[funnel_form_id]
    )

    def __repr__(self) -> str:
        return f"<Lead id={self.id} fb_lead_id={self.fb_lead_id!r}>"
