from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.goal.enums import DeactivationReasonLiteral


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
