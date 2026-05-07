import enum
from datetime import datetime

from sqlalchemy import String, Text, ForeignKey, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class OfferStatus(str, enum.Enum):
    active = "active"
    inactive = "inactive"


class Offer(Base):
    __tablename__ = "offers"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    client_id: Mapped[int] = mapped_column(
        ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    geo: Mapped[str | None] = mapped_column(String(100), nullable=True)
    language: Mapped[str | None] = mapped_column(String(50), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default=OfferStatus.active.value, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    client: Mapped["Client"] = relationship("Client", back_populates="offers", lazy="selectin")
    lead_forms: Mapped[list["LeadForm"]] = relationship(
        "LeadForm", back_populates="offer", cascade="all, delete-orphan", lazy="selectin"
    )
    leads: Mapped[list["Lead"]] = relationship("Lead", back_populates="offer")

    def __repr__(self) -> str:
        return f"<Offer id={self.id} name={self.name!r}>"
