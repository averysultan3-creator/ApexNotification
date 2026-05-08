from __future__ import annotations
import enum
from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database import Base


class FacebookLeadFormStatus(str, enum.Enum):
    active = "active"
    inactive = "inactive"


class FacebookLeadForm(Base):
    __tablename__ = "facebook_lead_forms"
    __table_args__ = (UniqueConstraint("fb_form_id", name="uq_facebook_lead_forms_fb_form_id"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    fb_page_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    fb_form_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True)
    offer_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), default=FacebookLeadFormStatus.active.value, nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    client: Mapped["Client"] = relationship("Client", back_populates="facebook_forms", lazy="selectin")
    leads: Mapped[list["Lead"]] = relationship("Lead", back_populates="form", lazy="selectin")

    def __repr__(self) -> str:
        return f"<FacebookLeadForm id={self.id} fb_form_id={self.fb_form_id!r}>"
