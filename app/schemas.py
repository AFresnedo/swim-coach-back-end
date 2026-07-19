from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.enums import CourseLiteral, DeactivationReasonLiteral, SexLiteral, StrokeLiteral, UnitPreferenceLiteral


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
    sex: SexLiteral
    unit_preference: UnitPreferenceLiteral = "metric"


class ProfileOut(ProfileIn):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int


class UserCountOut(BaseModel):
    user_count: int


class SwimCountOut(BaseModel):
    swim_count: int


class GoalIn(BaseModel):
    text: str = Field(min_length=1, max_length=2_000)


class GoalOut(GoalIn):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    is_active: bool
    deactivation_reason: DeactivationReasonLiteral | None
    created_at: datetime


class GoalDeactivateReason(BaseModel):
    reason: DeactivationReasonLiteral


class SwimTimeIn(BaseModel):
    date: date
    stroke: StrokeLiteral
    course: CourseLiteral
    length: int = Field(gt=0)
    attempt_number: int = Field(gt=0, default=1)
    time_seconds: float = Field(gt=0)
    is_official: bool = False
    notes: str | None = Field(default=None, max_length=2_000)


class SwimTimeOut(SwimTimeIn):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    created_at: datetime


class SwimTimePage(BaseModel):
    items: list[SwimTimeOut]
    next_cursor: str | None


class TrainingAskIn(BaseModel):
    question: str = Field(min_length=1, max_length=2_000)


class TrainingAskOut(BaseModel):
    answer: str
    answered_from_knowledge_base: bool
    sources: list[str]
