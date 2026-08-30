from fastapi import APIRouter

from app.database import DbDep
from app.deps import CurrentUserDep
from app.rag.drill import generate_drill
from app.rag.plan import generate_plan
from app.rag.schema import DrillAskIn, DrillAskOut, PlanAskIn, PlanAskOut, TrainingAskIn, TrainingAskOut
from app.rag.training import ask_training

router = APIRouter(prefix="/training", tags=["training"])


@router.post("/ask", response_model=TrainingAskOut)
def ask(payload: TrainingAskIn, current_user: CurrentUserDep, db: DbDep) -> TrainingAskOut:
    result = ask_training(db, user_id=current_user.id, raw_question=payload.question)
    return TrainingAskOut(
        answer=result.answer,
        answered_from_knowledge_base=result.answered_from_knowledge_base,
        sources=result.sources,
    )


# POC-only endpoints below (personalized plans + custom drills generator demo
# pages) - temporary, no retrieval/grounding, no persistence.


@router.post("/plan", response_model=PlanAskOut)
def plan(payload: PlanAskIn, current_user: CurrentUserDep, db: DbDep) -> PlanAskOut:
    return generate_plan(db, user_id=current_user.id, weeks=payload.weeks, sessions_per_week=payload.sessions_per_week)


@router.post("/drill", response_model=DrillAskOut)
def drill(payload: DrillAskIn, current_user: CurrentUserDep) -> DrillAskOut:
    return generate_drill(stroke=payload.stroke, focus=payload.focus, skill_level=payload.skill_level)
