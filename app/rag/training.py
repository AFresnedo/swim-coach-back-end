"""Orchestrates the /training endpoint's retrieval-and-answer flow (see the
"Hybrid RAG training-coach endpoint" Trello card)."""

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.config import settings
from app.profile.model import Profile
from app.rag.answer import answer_from_knowledge
from app.rag.embeddings import embed_query
from app.rag.ingest import ingest_fetched_pages
from app.rag.query import clean_question
from app.rag.retrieval import RetrievedChunk, fetch_active_goals, search_swim_knowledge
from app.rag.sharpen import sharpen_question
from app.rag.sharpen_flag import is_sharpen_enabled
from app.rag.web_fallback import answer_with_web_fallback


@dataclass(frozen=True)
class TrainingAnswer:
    answer: str
    answered_from_knowledge_base: bool
    sources: list[str]


def _is_hit(results: list[RetrievedChunk]) -> bool:
    return bool(results) and results[0].similarity >= settings.similarity_threshold


def ask_training(db: Session, *, user_id: int, raw_question: str) -> TrainingAnswer:
    question = clean_question(raw_question)
    profile = db.query(Profile).filter(Profile.user_id == user_id).first()
    goals = fetch_active_goals(db, user_id)
    query_vector = embed_query(question)
    results = search_swim_knowledge(db, query_vector)

    if not _is_hit(results) and is_sharpen_enabled():
        question = sharpen_question(question, profile=profile, goals=goals)
        query_vector = embed_query(question)
        results = search_swim_knowledge(db, query_vector)

    if _is_hit(results):
        answer = answer_from_knowledge(question, results, profile=profile, goals=goals)
        sources = [result.chunk.source_url for result in results]
        return TrainingAnswer(answer=answer, answered_from_knowledge_base=True, sources=sources)

    fallback = answer_with_web_fallback(question, profile=profile, goals=goals)
    ingest_fetched_pages(db, source_query=question, pages=fallback.fetched_pages)
    # Flattens to plain URLs on purpose - anything else on CitedSource is dropped, not lost (still on fallback.sources).
    sources = [source.url for source in fallback.sources]
    return TrainingAnswer(answer=fallback.answer, answered_from_knowledge_base=False, sources=sources)
