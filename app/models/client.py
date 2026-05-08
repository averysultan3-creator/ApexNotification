from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class ClientStatus(str, enum.Enum):
    active = "active"
    inactive = "inactive"


class Client(Base):
    __tablename__ = "clients"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    telegram_ids_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    emails_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default=ClientStatus.active.value, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    facebook_forms: Mapped[list["FacebookLeadForm"]] = relationship(
        "FacebookLeadForm", back_populates="client", lazy="selectin"
    )
    leads: Mapped[list["Lead"]] = relationship("Lead", back_populates="client", lazy="selectin")
    delivery_rules: Mapped[list["DeliveryRule"]] = relationship(
        "DeliveryRule", back_populates="client", lazy="selectin"
    )
    prelands: Mapped[list["Preland"]] = relationship("Preland", back_populates="client", lazy="selectin")

    def __repr__(self) -> str:
        return f"<Client id={self.id} name={self.name!r}>"
