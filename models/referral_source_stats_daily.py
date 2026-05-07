from datetime import datetime

from sqlalchemy import String, Integer, ForeignKey, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class ReferralSourceStatsDaily(Base):
    __tablename__ = "referral_source_stats_daily"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    date: Mapped[str] = mapped_column(String(10), nullable=False, index=True)  # YYYY-MM-DD

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

    clicks: Mapped[int] = mapped_column(Integer, default=0)
    bot_starts: Mapped[int] = mapped_column(Integer, default=0)
    form_views: Mapped[int] = mapped_column(Integer, default=0)
    form_starts: Mapped[int] = mapped_column(Integer, default=0)
    form_completions: Mapped[int] = mapped_column(Integer, default=0)
    leads_created: Mapped[int] = mapped_column(Integer, default=0)
    duplicates: Mapped[int] = mapped_column(Integer, default=0)

    contacted: Mapped[int] = mapped_column(Integer, default=0)
    qualified: Mapped[int] = mapped_column(Integer, default=0)
    rejected: Mapped[int] = mapped_column(Integer, default=0)
    approved: Mapped[int] = mapped_column(Integer, default=0)

    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return (
            f"<ReferralSourceStatsDaily id={self.id} date={self.date!r} "
            f"ref_id={self.referral_source_id}>"
        )
