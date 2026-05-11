from __future__ import annotations
import enum
from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database import Base


class PrelandLinkStatus(str, enum.Enum):
    active = "active"
    paused = "paused"
    archived = "archived"


class PrelandLink(Base):
    __tablename__ = "preland_links"
    __table_args__ = (UniqueConstraint("slug", name="uq_preland_links_slug"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    site_id: Mapped[int] = mapped_column(
        ForeignKey("preland_sites.id", ondelete="CASCADE"), nullable=False, index=True
    )
    display_name: Mapped[str] = mapped_column(String(300), nullable=False)
    slug: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    country: Mapped[str | None] = mapped_column(String(10), nullable=True)
    placement: Mapped[str | None] = mapped_column(String(50), nullable=True)
    audience: Mapped[str | None] = mapped_column(String(100), nullable=True)
    angle: Mapped[str | None] = mapped_column(String(100), nullable=True)
    final_url: Mapped[str] = mapped_column(String(600), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), default=PrelandLinkStatus.active.value, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    site: Mapped["PrelandSite"] = relationship("PrelandSite", back_populates="links", lazy="selectin")
    events: Mapped[list["PrelandEvent"]] = relationship(
        "PrelandEvent", back_populates="link", cascade="all, delete-orphan", lazy="noload"
    )

    def __repr__(self) -> str:
        return f"<PrelandLink id={self.id} slug={self.slug!r}>"
