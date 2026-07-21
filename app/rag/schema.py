from pydantic import BaseModel, Field


class TrainingAskIn(BaseModel):
    question: str = Field(min_length=1, max_length=2_000)


class TrainingAskOut(BaseModel):
    answer: str
    answered_from_knowledge_base: bool
    sources: list[str]
