import enum
from datetime import datetime

from sqlalchemy import String, Text, BigInteger, ForeignKey, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class LeadStatus(str, enum.Enum):
    new = "new"
    contacted = "contacted"
    qualified = "qualified"
    rejected = "rejected"
    duplicate = "duplicate"
    approved = "approved"


LEAD_STATUS_LABELS = {
    "new": "🆕 Новый",
    "contacted": "📞 Связались",
    "qualified": "✅ Квалифицирован",
    "rejected": "❌ Отклонён",
    "duplicate": "🔁 Дубль",
    "approved": "🎯 Одобрен",
}


class Lead(Base):
    __tablename__ = "leads"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    client_id: Mapped[int | None] = mapped_column(
        ForeignKey("clients.id", ondelete="SET NULL"), nullable=True, index=True
    )
    offer_id: Mapped[int | None] = mapped_column(
        ForeignKey("offers.id", ondelete="SET NULL"), nullable=True, index=True
    )
    form_id: Mapped[int | None] = mapped_column(
        ForeignKey("lead_forms.id", ondelete="SET NULL"), nullable=True, index=True
    )
    referral_source_id: Mapped[int | None] = mapped_column(
        ForeignKey("referral_sources.id", ondelete="SET NULL"), nullable=True, index=True
    )
    telegram_user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    telegram_username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    first_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # JSON-encoded dict: {question_id: answer}
    answers_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), default=LeadStatus.new.value, nullable=False, index=True
    )
    admin_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    client: Mapped["Client | None"] = relationship("Client", back_populates="leads", lazy="selectin")
    offer: Mapped["Offer | None"] = relationship("Offer", back_populates="leads", lazy="selectin")
    form: Mapped["LeadForm | None"] = relationship("LeadForm", back_populates="leads", lazy="selectin")
    referral_source: Mapped["ReferralSource | None"] = relationship(
        "ReferralSource", back_populates="leads", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<Lead id={self.id} tg_user={self.telegram_user_id}>"
