from unittest.mock import MagicMock, patch

from app.rag.models import EMBEDDING_DIMENSION, SwimKnowledge


def _make_chunk(**overrides: object) -> SwimKnowledge:
    defaults = {
        "chunk_text": "Bilateral breathing improves stroke symmetry.",
        "embedding": [0.0] * EMBEDDING_DIMENSION,
        "source_url": "https://example.com/breathing",
        "source_query": "how to improve freestyle breathing",
        "ingestion_reason": "fallback_web_search",
        "quality_flag": "pass",
    }
    defaults.update(overrides)
    return SwimKnowledge(**defaults)


def test_ask_endpoint_requires_auth(pg_client):
    response = pg_client.post("/training/ask", json={"question": "how do i breathe better?"})
    assert response.status_code == 401


def test_ask_endpoint_answers_from_knowledge_base_on_hit(pg_client, pg_session, pg_auth_headers):
    matching_vector = [0.0] * EMBEDDING_DIMENSION
    matching_vector[0] = 1.0
    pg_session.add(_make_chunk(embedding=matching_vector))
    pg_session.commit()

    fake_text_block = MagicMock(type="text", text="Try bilateral breathing every 3 strokes.")
    fake_response = MagicMock(content=[fake_text_block])

    with (
        patch("app.rag.training.embed_query", return_value=matching_vector),
        patch("app.rag.answer.anthropic_client.messages.create", return_value=fake_response),
    ):
        response = pg_client.post(
            "/training/ask",
            json={"question": "how do i breathe better?"},
            headers=pg_auth_headers,
        )

    assert response.status_code == 200
    body = response.json()
    assert body["answer"] == "Try bilateral breathing every 3 strokes."
    assert body["answered_from_knowledge_base"] is True
    assert body["sources"] == ["https://example.com/breathing"]


def test_ask_endpoint_returns_no_match_answer_on_empty_kb(pg_client, pg_auth_headers):
    query_vector = [0.0] * EMBEDDING_DIMENSION

    with patch("app.rag.training.embed_query", return_value=query_vector):
        response = pg_client.post(
            "/training/ask",
            json={"question": "how do i breathe better?"},
            headers=pg_auth_headers,
        )

    assert response.status_code == 200
    body = response.json()
    assert body["answered_from_knowledge_base"] is False
    assert body["sources"] == []


def test_ask_endpoint_rejects_empty_question(pg_client, pg_auth_headers):
    response = pg_client.post("/training/ask", json={"question": ""}, headers=pg_auth_headers)
    assert response.status_code == 422
