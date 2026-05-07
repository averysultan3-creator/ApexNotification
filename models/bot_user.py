"""BotUser — panel access accounts with roles."""
from datetime import datetime, timezone

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from database import Base

ROLES = ("super_admin", "client_admin", "client_viewer", "manager")


class BotUser(Base):
    __tablename__ = "bot_users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    telegram_user_id: Mapped[int] = mapped_column(
        BigInteger, unique=True, nullable=False, index=True
    )
    telegram_username: Mapped[str | None] = mapped_column(String(100), nullable=True)
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="client_admin")
    # client_id is set for client_admin / client_viewer / manager roles
    client_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("clients.id", ondelete="SET NULL"), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    notes: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )
