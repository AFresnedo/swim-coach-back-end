from datetime import date, datetime

from sqlalchemy import Boolean, CheckConstraint, Date, Float, ForeignKey, Index, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import StandardBase, UTCDateTime
from app.enums import COURSES, STROKES, CourseLiteral, StrokeLiteral
from app.model_utils import enum_column, utcnow


class SwimTime(StandardBase):
    __tablename__ = "swim_times"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    date: Mapped[date] = mapped_column(Date)
    stroke: Mapped[StrokeLiteral] = mapped_column(enum_column(*STROKES, name="ck_swim_times_stroke", length=20))
    course: Mapped[CourseLiteral] = mapped_column(enum_column(*COURSES, name="ck_swim_times_course", length=3))
    length: Mapped[int] = mapped_column(Integer)
    attempt_number: Mapped[int] = mapped_column(Integer, default=1)
    time_seconds: Mapped[float] = mapped_column(Float)
    is_official: Mapped[bool] = mapped_column(Boolean, default=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)

    __table_args__ = (
        CheckConstraint("length > 0", name="ck_swim_times_length_positive"),
        CheckConstraint("time_seconds > 0", name="ck_swim_times_time_positive"),
        CheckConstraint("attempt_number > 0", name="ck_swim_times_attempt_number_positive"),
        Index("ix_swim_times_user_id_date_created_at_id", "user_id", "date", "created_at", "id"),
        Index("ix_swim_times_user_id_stroke", "user_id", "stroke"),
        Index("ix_swim_times_user_id_course", "user_id", "course"),
        Index("ix_swim_times_user_id_length", "user_id", "length"),
        Index("ix_swim_times_user_id_is_official", "user_id", "is_official"),
    )
