import enum
from datetime import datetime

from sqlalchemy import String, Text, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class ClientStatus(str, enum.Enum):
    active = "active"
    inactive = "inactive"


class Client(Base):
    __tablename__ = "clients"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    telegram_username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default=ClientStatus.active.value, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    offers: Mapped[list["Offer"]] = relationship(
        "Offer", back_populates="client", cascade="all, delete-orphan", lazy="selectin"
    )
    lead_forms: Mapped[list["LeadForm"]] = relationship(
        "LeadForm", back_populates="client", cascade="all, delete-orphan", lazy="selectin"
    )
    leads: Mapped[list["Lead"]] = relationship("Lead", back_populates="client")

    def __repr__(self) -> str:
        return f"<Client id={self.id} name={self.name!r}>"
