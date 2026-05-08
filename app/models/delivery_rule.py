from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class DeliveryRuleStatus(str, enum.Enum):
    active = "active"
    inactive = "inactive"


class DeliveryRule(Base):
    __tablename__ = "delivery_rules"
    __table_args__ = (UniqueConstraint("source_type", "source_id", name="uq_delivery_rules_source"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    source_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    source_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True)
    send_to_admin: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    telegram_ids_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    emails_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    google_sheet_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default=DeliveryRuleStatus.active.value, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    client: Mapped["Client"] = relationship("Client", back_populates="delivery_rules", lazy="selectin")

    def __repr__(self) -> str:
        return f"<DeliveryRule id={self.id} source={self.source_type}:{self.source_id}>"
