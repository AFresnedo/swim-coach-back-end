import pytest
from sqlalchemy.exc import IntegrityError

from app.rag.models import EMBEDDING_DIMENSION, SwimKnowledge


def _embedding(*, seed: float) -> list[float]:
    # Deterministic, cheap stand-in for a real Voyage embedding - real values
    # don't matter here, only that they're valid 512-dim floats with a
    # controllable relative distance for the ordering test below.
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
        "stroke_type": "freestyle",
        "topic_category": "technique",
        "skill_level": "intermediate",
    }
    defaults.update(overrides)
    return SwimKnowledge(**defaults)


def test_insert_and_read_back_round_trips_all_fields(pg_session):
    chunk = _make_chunk()
    pg_session.add(chunk)
    pg_session.commit()

    fetched = pg_session.get(SwimKnowledge, chunk.id)
    assert fetched is not None
    assert fetched.chunk_text == chunk.chunk_text
    assert fetched.embedding == pytest.approx(chunk.embedding)
    assert fetched.source_url == chunk.source_url
    assert fetched.ingestion_reason == "fallback_web_search"
    assert fetched.quality_flag == "pass"
    assert fetched.stroke_type == "freestyle"
    assert fetched.topic_category == "technique"
    assert fetched.skill_level == "intermediate"
    assert fetched.ingested_at is not None


def test_cosine_distance_orders_by_similarity(pg_session):
    query_vector = _embedding(seed=1.0)
    matching_chunk = _make_chunk(chunk_text="matching", embedding=query_vector)
    opposite_chunk = _make_chunk(chunk_text="opposite", embedding=[-value for value in query_vector])
    pg_session.add_all([opposite_chunk, matching_chunk])
    pg_session.commit()

    results = pg_session.query(SwimKnowledge).order_by(SwimKnowledge.embedding.cosine_distance(query_vector)).all()

    assert [row.chunk_text for row in results] == ["matching", "opposite"]


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("ingestion_reason", "manual_seed"),
        ("quality_flag", "maybe"),
        ("stroke_type", "sidestroke"),
        ("topic_category", "motivation"),
        ("skill_level", "novice"),
    ],
)
def test_check_constraints_reject_out_of_set_values(pg_session, field, value):
    chunk = _make_chunk(**{field: value})
    pg_session.add(chunk)
    with pytest.raises(IntegrityError):
        pg_session.commit()
