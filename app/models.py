from datetime import date, datetime

from sqlalchemy import Boolean, CheckConstraint, Date, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import StandardBase, UTCDateTime
from app.enums import COURSES, DEACTIVATION_REASONS, SEXES, STROKES, UNIT_PREFERENCES
from app.model_utils import nullable_sql_in_clause, sql_in_clause, utcnow


class User(StandardBase):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    token_valid_after: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)


class Profile(StandardBase):
    __tablename__ = "profiles"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True, index=True)
    age: Mapped[int] = mapped_column(Integer)
    height_cm: Mapped[float] = mapped_column(Float)
    weight_kg: Mapped[float] = mapped_column(Float)
    sex: Mapped[str] = mapped_column(String(20))
    unit_preference: Mapped[str] = mapped_column(String(10), default="metric")

    __table_args__ = (
        CheckConstraint(sql_in_clause("unit_preference", UNIT_PREFERENCES), name="ck_profiles_unit_preference"),
        CheckConstraint(sql_in_clause("sex", SEXES), name="ck_profiles_sex"),
    )


class Goal(StandardBase):
    __tablename__ = "goals"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    text: Mapped[str] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    deactivation_reason: Mapped[str | None] = mapped_column(String(25), nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)

    __table_args__ = (
        CheckConstraint(
            nullable_sql_in_clause("deactivation_reason", DEACTIVATION_REASONS),
            name="ck_goals_deactivation_reason",
        ),
    )


class SwimTime(StandardBase):
    __tablename__ = "swim_times"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    date: Mapped[date] = mapped_column(Date)
    stroke: Mapped[str] = mapped_column(String(20))
    course: Mapped[str] = mapped_column(String(3))
    length: Mapped[int] = mapped_column(Integer)
    attempt_number: Mapped[int] = mapped_column(Integer, default=1)
    time_seconds: Mapped[float] = mapped_column(Float)
    is_official: Mapped[bool] = mapped_column(Boolean, default=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)

    __table_args__ = (
        CheckConstraint(sql_in_clause("stroke", STROKES), name="ck_swim_times_stroke"),
        CheckConstraint(sql_in_clause("course", COURSES), name="ck_swim_times_course"),
        CheckConstraint("length > 0", name="ck_swim_times_length_positive"),
        CheckConstraint("time_seconds > 0", name="ck_swim_times_time_positive"),
        CheckConstraint("attempt_number > 0", name="ck_swim_times_attempt_number_positive"),
        Index("ix_swim_times_user_id_date_created_at_id", "user_id", "date", "created_at", "id"),
        Index("ix_swim_times_user_id_stroke", "user_id", "stroke"),
        Index("ix_swim_times_user_id_course", "user_id", "course"),
        Index("ix_swim_times_user_id_length", "user_id", "length"),
        Index("ix_swim_times_user_id_is_official", "user_id", "is_official"),
    )
