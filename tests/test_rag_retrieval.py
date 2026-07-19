from app.models import Goal
from app.rag.models import EMBEDDING_DIMENSION, SwimKnowledge
from app.rag.retrieval import fetch_active_goals, search_swim_knowledge


def _embedding(*, seed: float) -> list[float]:
    vector = [0.0] * EMBEDDING_DIMENSION
    vector[0] = seed
    return vector


def _make_chunk(**overrides: object) -> SwimKnowledge:
    defaults = {
        "chunk_text": "Bilateral breathing improves stroke symmetry.",
        "embedding": _embedding(seed=1.0),
        "source_url": "https://example.com/breathing",
        "source_query": "how to improve freestyle breathing",
        "ingestion_reason": "fallback_web_search",
        "quality_flag": "pass",
    }
    defaults.update(overrides)
    return SwimKnowledge(**defaults)


def test_search_swim_knowledge_orders_by_similarity_best_first(pg_session):
    query_vector = _embedding(seed=1.0)
    close_chunk = _make_chunk(chunk_text="close match", embedding=_embedding(seed=0.9))
    far_chunk = _make_chunk(chunk_text="far match", embedding=_embedding(seed=-1.0))
    pg_session.add_all([far_chunk, close_chunk])
    pg_session.commit()

    results = search_swim_knowledge(pg_session, query_vector)

    assert [r.chunk.chunk_text for r in results] == ["close match", "far match"]
    assert results[0].similarity > results[1].similarity


def test_search_swim_knowledge_respects_top_k(pg_session):
    for i in range(5):
        pg_session.add(_make_chunk(chunk_text=f"chunk {i}", embedding=_embedding(seed=float(i))))
    pg_session.commit()

    results = search_swim_knowledge(pg_session, _embedding(seed=1.0), top_k=2)

    assert len(results) == 2


def test_search_swim_knowledge_empty_kb_returns_empty_list(pg_session):
    assert search_swim_knowledge(pg_session, _embedding(seed=1.0)) == []


def test_fetch_active_goals_filters_by_user_and_active_status(db_session):
    other_user_goal = Goal(user_id=2, text="not mine", is_active=True)
    inactive_goal = Goal(user_id=1, text="abandoned goal", is_active=False, deactivation_reason="abandoned")
    active_goal = Goal(user_id=1, text="sub-60 100 free", is_active=True)
    db_session.add_all([other_user_goal, inactive_goal, active_goal])
    db_session.commit()

    goals = fetch_active_goals(db_session, user_id=1)

    assert [g.text for g in goals] == ["sub-60 100 free"]
