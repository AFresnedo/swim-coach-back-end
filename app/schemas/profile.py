from pydantic import BaseModel, ConfigDict, Field

from app.enums import SexLiteral, UnitPreferenceLiteral


class ProfileIn(BaseModel):
    age: int = Field(ge=5, le=120)
    height_cm: float = Field(ge=50, le=280)
    weight_kg: float = Field(ge=20, le=400)
    sex: SexLiteral
    unit_preference: UnitPreferenceLiteral = "metric"


class ProfileOut(ProfileIn):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
