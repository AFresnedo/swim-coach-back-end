from fastapi import APIRouter

from app.database import DbDep
from app.deps import CurrentUserDep
from app.rag.schema import TrainingAskIn, TrainingAskOut
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
