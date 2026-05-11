from __future__ import annotations
import enum
from datetime import datetime
from sqlalchemy import BigInteger, DateTime, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column
from database import Base


class DeliveryType(str, enum.Enum):
    new = "new"           # real-time new lead
    backfill = "backfill"  # admin/client requested old leads


class DeliveryStatus(str, enum.Enum):
    sent = "sent"
    failed = "failed"


class LeadDeliveryHistory(Base):
    __tablename__ = "lead_delivery_history"
    __table_args__ = (
        UniqueConstraint(
            "lead_id", "recipient_telegram_id", "delivery_type",
            name="uq_ldh_lead_recip_type",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    lead_id: Mapped[int] = mapped_column(
        ForeignKey("leads.id", ondelete="CASCADE"), nullable=False, index=True
    )
    recipient_telegram_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    delivery_type: Mapped[str] = mapped_column(String(20), nullable=False)  # new | backfill
    status: Mapped[str] = mapped_column(String(20), nullable=False)          # sent | failed
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return (
            f"<LeadDeliveryHistory id={self.id} lead={self.lead_id} "
            f"recip={self.recipient_telegram_id} type={self.delivery_type!r} "
            f"status={self.status!r}>"
        )
