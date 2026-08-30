from unittest.mock import patch

from app.rag.ingest import ingest_fetched_pages
from app.rag.models import EMBEDDING_DIMENSION, SwimKnowledge
from app.rag.web_fallback import FetchedPage


def _page(**overrides: object) -> FetchedPage:
    defaults = {
        "source_url": "https://swimswam.com/catch",
        "raw_text": "A high-elbow catch generates more propulsive power.",
        "quality_score": 0.8,
        "quality_flag": "pass",
        "quality_reason": "Clear coaching advice.",
        "stroke_type": "freestyle",
        "topic_category": "technique",
        "skill_level": "intermediate",
    }
    defaults.update(overrides)
    return FetchedPage(**defaults)


def _fake_embed(texts: list[str]) -> list[list[float]]:
    return [[0.0] * EMBEDDING_DIMENSION for _ in texts]


def test_ingest_fetched_pages_writes_chunk_with_full_provenance(pg_session):
    with (
        patch("app.rag.ingest.clean_fetched_text", side_effect=lambda text: text),
        patch("app.rag.ingest.embed_documents", side_effect=_fake_embed),
    ):
        rows = ingest_fetched_pages(pg_session, source_query="how do I improve my catch?", pages=[_page()])

    assert len(rows) == 1
    stored = pg_session.query(SwimKnowledge).one()
    assert stored.source_url == "https://swimswam.com/catch"
    assert stored.source_query == "how do I improve my catch?"
    assert stored.ingestion_reason == "fallback_web_search"
    assert stored.quality_flag == "pass"
    assert stored.quality_score == 0.8
    assert stored.stroke_type == "freestyle"
    assert stored.topic_category == "technique"
    assert stored.skill_level == "intermediate"
    assert stored.ingested_at is not None


def test_ingest_fetched_pages_rejects_quality_flag_reject(pg_session):
    rows = ingest_fetched_pages(pg_session, source_query="q", pages=[_page(quality_flag="reject")])

    assert rows == []
    assert pg_session.query(SwimKnowledge).count() == 0


def test_ingest_fetched_pages_skips_source_url_already_in_knowledge_base(pg_session):
    existing = SwimKnowledge(
        chunk_text="existing chunk",
        embedding=[0.0] * EMBEDDING_DIMENSION,
        source_url="https://swimswam.com/catch",
        source_query="prior question",
        ingestion_reason="fallback_web_search",
        quality_flag="pass",
    )
    pg_session.add(existing)
    pg_session.commit()

    rows = ingest_fetched_pages(pg_session, source_query="q", pages=[_page()])

    assert rows == []
    assert pg_session.query(SwimKnowledge).count() == 1


def test_ingest_fetched_pages_dedups_duplicate_source_url_within_one_call(pg_session):
    with (
        patch("app.rag.ingest.clean_fetched_text", side_effect=lambda text: text),
        patch("app.rag.ingest.embed_documents", side_effect=_fake_embed),
    ):
        rows = ingest_fetched_pages(pg_session, source_query="q", pages=[_page(), _page()])

    assert len(rows) == 1
    assert pg_session.query(SwimKnowledge).count() == 1


def test_ingest_fetched_pages_splits_long_text_into_multiple_chunks(pg_session):
    long_text = "A high-elbow catch generates more propulsive power. " * 100
    with (
        patch("app.rag.ingest.clean_fetched_text", side_effect=lambda text: text),
        patch("app.rag.ingest.embed_documents", side_effect=_fake_embed),
    ):
        rows = ingest_fetched_pages(pg_session, source_query="q", pages=[_page(raw_text=long_text)])

    assert len(rows) > 1
    assert all(row.source_url == "https://swimswam.com/catch" for row in rows)


def test_ingest_fetched_pages_chunks_cleaned_text_not_raw_text(pg_session):
    with (
        patch("app.rag.ingest.clean_fetched_text", return_value="Cleaned article body.") as mock_clean,
        patch("app.rag.ingest.embed_documents", side_effect=_fake_embed),
    ):
        rows = ingest_fetched_pages(
            pg_session, source_query="q", pages=[_page(raw_text="nav links\n\nreal content\n\nfooter links")]
        )

    mock_clean.assert_called_once_with("nav links\n\nreal content\n\nfooter links")
    assert len(rows) == 1
    assert rows[0].chunk_text == "Cleaned article body."
