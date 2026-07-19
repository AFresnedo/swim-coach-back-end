"""Steps 1-2 of the hybrid RAG training-coach pipeline: fetch the swimmer's
active goals via plain SQL, and cosine-search SwimKnowledge for the nearest
chunks to an already-embedded question (see the "Hybrid RAG training-coach
endpoint" Trello card).
"""

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models import Goal
from app.rag.models import SwimKnowledge

DEFAULT_TOP_K = 5


@dataclass(frozen=True)
class RetrievedChunk:
    chunk: SwimKnowledge
    similarity: float


def fetch_active_goals(db: Session, user_id: int) -> list[Goal]:
    return (
        db.query(Goal)
        .filter(Goal.user_id == user_id, Goal.is_active.is_(True))
        .order_by(Goal.created_at.desc())
        .all()
    )


def search_swim_knowledge(db: Session, query_vector: list[float], *, top_k: int = DEFAULT_TOP_K) -> list[RetrievedChunk]:
    """Cosine-search SwimKnowledge for the top_k chunks nearest query_vector,
    ordered by similarity (best match first).

    pgvector's cosine_distance() returns 1 - cosine_similarity, not the
    similarity itself - converted here so callers compare directly against
    RagSettings.similarity_threshold, matching the card's "best match >=
    SIMILARITY_THRESHOLD" framing rather than a distance framing.
    """
    distance = SwimKnowledge.embedding.cosine_distance(query_vector)
    rows = db.query(SwimKnowledge, distance.label("distance")).order_by(distance).limit(top_k).all()
    return [RetrievedChunk(chunk=chunk, similarity=1 - dist) for chunk, dist in rows]
