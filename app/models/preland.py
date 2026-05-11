from __future__ import annotations
import enum
from datetime import datetime
from sqlalchemy import DateTime, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database import Base


class PrelandStatus(str, enum.Enum):
    active = "active"
    inactive = "inactive"
    archived = "archived"


class Preland(Base):
    __tablename__ = "prelands"
    __table_args__ = (UniqueConstraint("slug", name="uq_prelands_slug"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(300), nullable=True)
    slug: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default=PrelandStatus.active.value, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    events: Mapped[list["PrelandEvent"]] = relationship(
        "PrelandEvent",
        primaryjoin="foreign(PrelandEvent.preland_id) == Preland.id",
        cascade="all, delete-orphan",
        lazy="selectin",
        overlaps="link",
    )

    def __repr__(self) -> str:
        return f"<Preland id={self.id} slug={self.slug!r}>"
