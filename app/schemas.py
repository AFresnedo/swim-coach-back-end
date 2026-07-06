from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: EmailStr
    created_at: datetime


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class ProfileIn(BaseModel):
    age: int = Field(ge=5, le=120)
    height_cm: float = Field(ge=50, le=280)
    weight_kg: float = Field(ge=20, le=400)
    sex: Literal["male", "female", "prefer_not_to_say"]
    unit_preference: Literal["metric", "imperial"] = "metric"


class ProfileOut(ProfileIn):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int


class UserCountOut(BaseModel):
    user_count: int


class GoalIn(BaseModel):
    text: str = Field(min_length=1, max_length=2_000)


class GoalOut(GoalIn):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    is_active: bool
    deactivation_reason: Literal["reached", "abandoned", "other"] | None
    created_at: datetime


class GoalDeactivateReason(BaseModel):
    reason: Literal["reached", "abandoned", "other"]
