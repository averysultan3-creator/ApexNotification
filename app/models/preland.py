from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class PrelandStatus(str, enum.Enum):
    active = "active"
    inactive = "inactive"


class Preland(Base):
    __tablename__ = "prelands"
    __table_args__ = (UniqueConstraint("slug", name="uq_prelands_slug"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    client_id: Mapped[int | None] = mapped_column(
        ForeignKey("clients.id", ondelete="SET NULL"), nullable=True, index=True
    )
    offer_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default=PrelandStatus.active.value, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    client: Mapped["Client | None"] = relationship("Client", back_populates="prelands", lazy="selectin")
    events: Mapped[list["PrelandEvent"]] = relationship(
        "PrelandEvent", back_populates="preland", cascade="all, delete-orphan", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<Preland id={self.id} slug={self.slug!r}>"
