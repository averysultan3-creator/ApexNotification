import enum
from datetime import datetime

from sqlalchemy import String, BigInteger, Integer, Boolean, ForeignKey, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class SessionStatus(str, enum.Enum):
    started = "started"
    in_progress = "in_progress"
    completed = "completed"
    abandoned = "abandoned"
    duplicate = "duplicate"
    error = "error"


class TrackingSession(Base):
    __tablename__ = "tracking_sessions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False, index=True
    )

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

    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default=SessionStatus.started.value
    )
    current_step: Mapped[int] = mapped_column(Integer, default=0)
    total_steps: Mapped[int] = mapped_column(Integer, default=0)
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False)
    is_duplicate: Mapped[bool] = mapped_column(Boolean, default=False)

    started_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_event_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return f"<TrackingSession id={self.id} session_id={self.session_id!r} status={self.status!r}>"
