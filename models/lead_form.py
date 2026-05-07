import enum
from datetime import datetime

from sqlalchemy import String, Text, ForeignKey, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class LeadFormStatus(str, enum.Enum):
    active = "active"
    inactive = "inactive"


class LeadForm(Base):
    __tablename__ = "lead_forms"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    client_id: Mapped[int] = mapped_column(
        ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True
    )
    offer_id: Mapped[int] = mapped_column(
        ForeignKey("offers.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    language: Mapped[str] = mapped_column(String(50), default="ru", nullable=False)
    welcome_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    success_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default=LeadFormStatus.active.value, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    client: Mapped["Client"] = relationship("Client", back_populates="lead_forms", lazy="selectin")
    offer: Mapped["Offer"] = relationship("Offer", back_populates="lead_forms", lazy="selectin")
    questions: Mapped[list["LeadFormQuestion"]] = relationship(
        "LeadFormQuestion",
        back_populates="form",
        order_by="LeadFormQuestion.position",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    referral_sources: Mapped[list["ReferralSource"]] = relationship(
        "ReferralSource",
        back_populates="form",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    leads: Mapped[list["Lead"]] = relationship("Lead", back_populates="form")

    def __repr__(self) -> str:
        return f"<LeadForm id={self.id} slug={self.slug!r}>"
