from pydantic import BaseModel, Field

from app.enums import StrokeLiteral


class TrainingAskIn(BaseModel):
    question: str = Field(min_length=1, max_length=2_000)


class TrainingAskOut(BaseModel):
    answer: str
    answered_from_knowledge_base: bool
    sources: list[str]


# POC-only schemas below (personalized plans + custom drills generator demo
# pages) - temporary, pure generation, no retrieval/grounding, no persistence.


class PlanAskIn(BaseModel):
    weeks: int = Field(ge=1, le=12)
    sessions_per_week: int = Field(ge=1, le=7)


class PlanSet(BaseModel):
    description: str
    distance_meters: int | None
    reps: int | None
    rest_seconds: int | None


class PlanSession(BaseModel):
    focus: str
    sets: list[PlanSet]


class PlanWeek(BaseModel):
    week_number: int
    sessions: list[PlanSession]


class PlanAskOut(BaseModel):
    summary: str
    weeks: list[PlanWeek]


class DrillAskIn(BaseModel):
    stroke: StrokeLiteral
    focus: str = Field(min_length=1, max_length=200)
    skill_level: str = Field(min_length=1, max_length=50)


class DrillSet(BaseModel):
    reps: int | None
    distance_meters: int | None
    rest_seconds: int | None


class DrillAskOut(BaseModel):
    name: str
    motivation: str
    benefit: str
    steps: list[str]
    set: DrillSet
