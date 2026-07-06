from datetime import UTC, date, datetime

from sqlalchemy import Boolean, CheckConstraint, Date, DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class Profile(Base):
    __tablename__ = "profiles"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True, index=True)
    age: Mapped[int] = mapped_column(Integer)
    height_cm: Mapped[float] = mapped_column(Float)
    weight_kg: Mapped[float] = mapped_column(Float)
    sex: Mapped[str] = mapped_column(String(20))
    unit_preference: Mapped[str] = mapped_column(String(10), default="metric")

    __table_args__ = (CheckConstraint("unit_preference IN ('metric', 'imperial')", name="ck_profiles_unit_preference"),)


class Goal(Base):
    __tablename__ = "goals"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    text: Mapped[str] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    deactivation_reason: Mapped[str | None] = mapped_column(String(25), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class SwimTime(Base):
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
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    __table_args__ = (
        CheckConstraint(
            "stroke IN ('freestyle', 'backstroke', 'breaststroke', 'butterfly', 'individual_medley')",
            name="ck_swim_times_stroke",
        ),
        CheckConstraint("course IN ('scy', 'scm', 'lcm')", name="ck_swim_times_course"),
        CheckConstraint("length > 0", name="ck_swim_times_length_positive"),
        CheckConstraint("time_seconds > 0", name="ck_swim_times_time_positive"),
        CheckConstraint("attempt_number > 0", name="ck_swim_times_attempt_number_positive"),
        Index("ix_swim_times_user_id_date_created_at_id", "user_id", "date", "created_at", "id"),
    )
