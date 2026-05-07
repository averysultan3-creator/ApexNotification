import enum
from datetime import datetime

from sqlalchemy import String, Text, BigInteger, Integer, ForeignKey, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class EventType(str, enum.Enum):
    link_clicked = "link_clicked"
    bot_started = "bot_started"
    form_viewed = "form_viewed"
    form_started = "form_started"
    question_viewed = "question_viewed"
    question_answered = "question_answered"
    form_completed = "form_completed"
    lead_created = "lead_created"
    duplicate_detected = "duplicate_detected"
    lead_status_changed = "lead_status_changed"
    export_created = "export_created"


class TrackingEvent(Base):
    __tablename__ = "tracking_events"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)

    client_id: Mapped[int | None] = mapped_column(
        ForeignKey("clients.id", ondelete="SET NULL"), nullable=True, index=True
    )
    offer_id: Mapped[int | None] = mapped_column(
        ForeignKey("offers.id", ondelete="SET NULL"), nullable=True, index=True
    )
    form_id: Mapped[int | None] = mapped_column(
        ForeignKey("lead_forms.id", ondelete="SET NULL"), nullable=True, index=True
    )
    referral_source_id: Mapped[int | None] = mapped_column(
        ForeignKey("referral_sources.id", ondelete="SET NULL"), nullable=True, index=True
    )
    lead_id: Mapped[int | None] = mapped_column(
        ForeignKey("leads.id", ondelete="SET NULL"), nullable=True
    )

    telegram_user_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, index=True)
    telegram_username: Mapped[str | None] = mapped_column(String(255), nullable=True)

    session_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    question_id: Mapped[int | None] = mapped_column(
        ForeignKey("lead_form_questions.id", ondelete="SET NULL"), nullable=True
    )
    step_number: Mapped[int | None] = mapped_column(Integer, nullable=True)

    metadata_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False, index=True
    )

    def __repr__(self) -> str:
        return f"<TrackingEvent id={self.id} type={self.event_type!r} session={self.session_id!r}>"
