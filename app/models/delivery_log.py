from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class DeliveryChannel(str, enum.Enum):
    admin_telegram = "admin_telegram"
    client_telegram = "client_telegram"
    email = "email"
    google_sheet = "google_sheet"
    rule = "rule"


class DeliveryStatus(str, enum.Enum):
    success = "success"
    error = "error"
    skipped = "skipped"


class DeliveryLog(Base):
    __tablename__ = "delivery_logs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    lead_id: Mapped[int] = mapped_column(ForeignKey("leads.id", ondelete="CASCADE"), nullable=False, index=True)
    channel: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    recipient: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False, index=True)

    lead: Mapped["Lead"] = relationship("Lead", back_populates="delivery_logs", lazy="selectin")

    def __repr__(self) -> str:
        return f"<DeliveryLog id={self.id} channel={self.channel!r} status={self.status!r}>"
