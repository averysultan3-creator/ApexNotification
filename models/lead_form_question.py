import enum
from datetime import datetime

from sqlalchemy import String, Text, Integer, Boolean, ForeignKey, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class QuestionType(str, enum.Enum):
    text = "text"
    single_choice = "single_choice"
    multi_choice = "multi_choice"
    phone = "phone"
    telegram_username = "telegram_username"
    number = "number"
    date = "date"
    comment = "comment"


CHOICE_TYPES = {QuestionType.single_choice.value, QuestionType.multi_choice.value}


class LeadFormQuestion(Base):
    __tablename__ = "lead_form_questions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    form_id: Mapped[int] = mapped_column(
        ForeignKey("lead_forms.id", ondelete="CASCADE"), nullable=False, index=True
    )
    position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    question_type: Mapped[str] = mapped_column(
        String(50), default=QuestionType.text.value, nullable=False
    )
    # JSON-encoded list of option strings for single_choice / multi_choice
    options_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_required: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    form: Mapped["LeadForm"] = relationship("LeadForm", back_populates="questions")

    def __repr__(self) -> str:
        return f"<LeadFormQuestion id={self.id} type={self.question_type!r} pos={self.position}>"
