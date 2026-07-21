from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import StandardBase, UTCDateTime
from app.goal.enums import DEACTIVATION_REASONS, DeactivationReasonLiteral
from app.model_utils import enum_column, utcnow


class Goal(StandardBase):
    __tablename__ = "goals"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    text: Mapped[str] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    deactivation_reason: Mapped[DeactivationReasonLiteral | None] = mapped_column(
        enum_column(*DEACTIVATION_REASONS, name="ck_goals_deactivation_reason", length=25), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
