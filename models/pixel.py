"""Pixel — external/internal pixel / tag configuration."""
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from database import Base

PIXEL_TYPES = ("meta", "google", "tiktok", "telegram")
PIXEL_EVENTS_ALL = (
    "bot_started",
    "form_viewed",
    "form_started",
    "form_completed",
    "lead_created",
    "approved",
)
PIXEL_SCOPES = ("global", "client", "offer", "form", "ref")
_DEFAULT_EVENTS = "bot_started,form_started,lead_created,approved"

PIXEL_TYPE_ICONS = {
    "meta": "📘",
    "google": "🔵",
    "tiktok": "🎵",
    "telegram": "✈️",
}
PIXEL_TYPE_LABELS = {
    "meta": "Meta Pixel",
    "google": "Google Tag",
    "tiktok": "TikTok Pixel",
    "telegram": "Telegram only",
}


class Pixel(Base):
    __tablename__ = "pixels"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    pixel_type: Mapped[str] = mapped_column(String(20), nullable=False)
    pixel_value: Mapped[str | None] = mapped_column(String(200), nullable=True)
    scope_type: Mapped[str] = mapped_column(String(20), nullable=False, default="global")
    scope_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    events: Mapped[str] = mapped_column(Text, nullable=False, default=_DEFAULT_EVENTS)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )

    @property
    def events_list(self) -> list[str]:
        return [e.strip() for e in self.events.split(",") if e.strip()]

    @property
    def type_icon(self) -> str:
        return PIXEL_TYPE_ICONS.get(self.pixel_type, "📡")

    @property
    def type_label(self) -> str:
        return PIXEL_TYPE_LABELS.get(self.pixel_type, self.pixel_type)
