import enum
from datetime import datetime

from sqlalchemy import String, Text, ForeignKey, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class SourceType(str, enum.Enum):
    facebook = "facebook"
    instagram = "instagram"
    tiktok = "tiktok"
    telegram = "telegram"
    google = "google"
    manual = "manual"
    other = "other"


class ReferralStatus(str, enum.Enum):
    active = "active"
    inactive = "inactive"


class ReferralSource(Base):
    __tablename__ = "referral_sources"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    form_id: Mapped[int] = mapped_column(
        ForeignKey("lead_forms.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    source_type: Mapped[str] = mapped_column(
        String(50), default=SourceType.other.value, nullable=False
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default=ReferralStatus.active.value, nullable=False)

    # UTM / traffic metadata
    traffic_source: Mapped[str | None] = mapped_column(String(100), nullable=True)
    campaign_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    ad_account: Mapped[str | None] = mapped_column(String(255), nullable=True)
    creative_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    placement: Mapped[str | None] = mapped_column(String(255), nullable=True)
    utm_geo: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    form: Mapped["LeadForm"] = relationship("LeadForm", back_populates="referral_sources", lazy="selectin")
    leads: Mapped[list["Lead"]] = relationship("Lead", back_populates="referral_source")

    def __repr__(self) -> str:
        return f"<ReferralSource id={self.id} code={self.code!r}>"
