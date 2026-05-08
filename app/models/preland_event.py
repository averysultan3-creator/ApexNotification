from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class PrelandEventType(str, enum.Enum):
    page_view = "page_view"
    button_click = "button_click"


class PrelandEvent(Base):
    __tablename__ = "preland_events"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    preland_id: Mapped[int] = mapped_column(ForeignKey("prelands.id", ondelete="CASCADE"), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    button_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    visitor_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    ip_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(500), nullable=True)
    referer: Mapped[str | None] = mapped_column(String(500), nullable=True)
    utm_source: Mapped[str | None] = mapped_column(String(255), nullable=True)
    utm_campaign: Mapped[str | None] = mapped_column(String(255), nullable=True)
    utm_content: Mapped[str | None] = mapped_column(String(255), nullable=True)
    metadata_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False, index=True)

    preland: Mapped["Preland"] = relationship("Preland", back_populates="events", lazy="selectin")

    def __repr__(self) -> str:
        return f"<PrelandEvent id={self.id} type={self.event_type!r}>"
