from __future__ import annotations
import enum
from datetime import datetime
from sqlalchemy import BigInteger, DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database import Base


class RecipientStatus(str, enum.Enum):
    active = "active"
    disabled = "disabled"


class ClientRecipient(Base):
    __tablename__ = "client_recipients"
    __table_args__ = (
        UniqueConstraint("funnel_form_id", "telegram_user_id", name="uq_client_recipients_form_user"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    funnel_form_id: Mapped[int] = mapped_column(
        ForeignKey("funnel_forms.id", ondelete="CASCADE"), nullable=False, index=True
    )
    telegram_user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    telegram_username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    first_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), default=RecipientStatus.active.value, nullable=False
    )
    joined_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    last_sent_lead_id: Mapped[int | None] = mapped_column(nullable=True)

    funnel_form: Mapped["FunnelForm"] = relationship(
        "FunnelForm", back_populates="recipients", lazy="selectin",
        foreign_keys=[funnel_form_id]
    )

    def __repr__(self) -> str:
        return f"<ClientRecipient id={self.id} tg={self.telegram_user_id}>"
