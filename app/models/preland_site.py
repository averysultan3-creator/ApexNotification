from __future__ import annotations
import enum
from datetime import datetime
from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database import Base


class PrelandSiteStatus(str, enum.Enum):
    active = "active"
    archived = "archived"


class PrelandSite(Base):
    __tablename__ = "preland_sites"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    base_url: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), default=PrelandSiteStatus.active.value, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    links: Mapped[list["PrelandLink"]] = relationship(
        "PrelandLink", back_populates="site", cascade="all, delete-orphan", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<PrelandSite id={self.id} name={self.name!r}>"
