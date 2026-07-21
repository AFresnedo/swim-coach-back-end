from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.enums import CourseLiteral, StrokeLiteral


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
