from sqlalchemy import Float, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.database import StandardBase
from app.model_utils import enum_column
from app.profile.enums import SEXES, UNIT_PREFERENCES, SexLiteral, UnitPreferenceLiteral


class Profile(StandardBase):
    __tablename__ = "profiles"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True, index=True)
    age: Mapped[int] = mapped_column(Integer)
    height_cm: Mapped[float] = mapped_column(Float)
    weight_kg: Mapped[float] = mapped_column(Float)
    sex: Mapped[SexLiteral] = mapped_column(enum_column(*SEXES, name="ck_profiles_sex", length=20))
    unit_preference: Mapped[UnitPreferenceLiteral] = mapped_column(
        enum_column(*UNIT_PREFERENCES, name="ck_profiles_unit_preference", length=10), default="metric"
    )
