"""Orchestrates the /training endpoint's retrieval-and-answer flow (see the
"Hybrid RAG training-coach endpoint" Trello card)."""

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.config import settings
from app.profile.model import Profile
from app.rag.answer import answer_from_knowledge
from app.rag.embeddings import embed_query
from app.rag.query import clean_question
from app.rag.retrieval import RetrievedChunk, fetch_active_goals, search_swim_knowledge
from app.rag.sharpen import sharpen_question
from app.rag.sharpen_flag import is_sharpen_enabled

_NO_MATCH_ANSWER = "I don't have enough information in the knowledge base to answer this confidently."


@dataclass(frozen=True)
class TrainingAnswer:
    answer: str
    answered_from_knowledge_base: bool
    sources: list[str]


def _is_hit(results: list[RetrievedChunk]) -> bool:
    return bool(results) and results[0].similarity >= settings.similarity_threshold


def ask_training(db: Session, *, user_id: int, raw_question: str) -> TrainingAnswer:
    question = clean_question(raw_question)
    query_vector = embed_query(question)
    results = search_swim_knowledge(db, query_vector)

    if not _is_hit(results) and is_sharpen_enabled():
        profile = db.query(Profile).filter(Profile.user_id == user_id).first()
        goals = fetch_active_goals(db, user_id)
        question = sharpen_question(question, profile=profile, goals=goals)
        query_vector = embed_query(question)
        results = search_swim_knowledge(db, query_vector)

    if _is_hit(results):
        answer = answer_from_knowledge(question, results)
        sources = [result.chunk.source_url for result in results]
        return TrainingAnswer(answer=answer, answered_from_knowledge_base=True, sources=sources)

    return TrainingAnswer(answer=_NO_MATCH_ANSWER, answered_from_knowledge_base=False, sources=[])
