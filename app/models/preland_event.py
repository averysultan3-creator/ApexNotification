from __future__ import annotations
import enum
from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database import Base


class PrelandEventType(str, enum.Enum):
    page_view = "page_view"
    button_click = "button_click"


class PrelandEvent(Base):
    __tablename__ = "preland_events"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    # New FK to preland_links (nullable for backward compat with old preland_id rows)
    link_id: Mapped[int | None] = mapped_column(
        ForeignKey("preland_links.id", ondelete="CASCADE"), nullable=True, index=True
    )
    # Legacy FK kept as nullable so old rows aren't broken
    preland_id: Mapped[int | None] = mapped_column(
        ForeignKey("prelands.id", ondelete="CASCADE"), nullable=True, index=True
    )
    # Denormalised slug for fast lookup without join
    slug: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    event_type: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    button_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    visitor_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    utm_source: Mapped[str | None] = mapped_column(String(255), nullable=True)
    utm_campaign: Mapped[str | None] = mapped_column(String(255), nullable=True)
    referrer: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False, index=True
    )

    link: Mapped["PrelandLink | None"] = relationship(
        "PrelandLink", back_populates="events", lazy="noload"
    )

    def __repr__(self) -> str:
        return f"<PrelandEvent id={self.id} type={self.event_type!r} slug={self.slug!r}>"

