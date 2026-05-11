from __future__ import annotations
import enum
from datetime import datetime
from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database import Base


class FunnelFormStatus(str, enum.Enum):
    active = "active"
    disabled = "disabled"
    archived = "archived"


class FunnelForm(Base):
    __tablename__ = "funnel_forms"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    form_name: Mapped[str] = mapped_column(String(255), nullable=False)
    client_label: Mapped[str | None] = mapped_column(String(255), nullable=True)
    offer_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    tag: Mapped[str | None] = mapped_column(String(255), nullable=True)
    fb_form_id: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    fb_page_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    verify_token: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    join_code: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    google_sheet_id: Mapped[str | None] = mapped_column(String(200), nullable=True)
    google_sheet_name: Mapped[str] = mapped_column(String(200), nullable=False, default="Leads")
    apps_script_web_app_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), default=FunnelFormStatus.active.value, nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    recipients: Mapped[list["ClientRecipient"]] = relationship(
        "ClientRecipient", back_populates="funnel_form", lazy="selectin",
        foreign_keys="ClientRecipient.funnel_form_id"
    )
    leads: Mapped[list["Lead"]] = relationship(
        "Lead", back_populates="funnel_form", lazy="selectin",
        foreign_keys="Lead.funnel_form_id"
    )

    def __repr__(self) -> str:
        return f"<FunnelForm id={self.id} form_name={self.form_name!r}>"
