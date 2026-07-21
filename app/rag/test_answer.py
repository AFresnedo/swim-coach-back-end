from unittest.mock import MagicMock, patch

from app.rag.answer import answer_from_knowledge
from app.rag.models import EMBEDDING_DIMENSION, SwimKnowledge
from app.rag.retrieval import RetrievedChunk


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


def test_answer_from_knowledge_returns_text_block_and_includes_context():
    fake_text_block = MagicMock(type="text", text="Try bilateral breathing every 3 strokes.")
    fake_response = MagicMock(content=[fake_text_block])
    chunks = [RetrievedChunk(chunk=_make_chunk(), similarity=0.9)]

    with patch("app.rag.answer.anthropic_client.messages.create", return_value=fake_response) as mock_create:
        answer = answer_from_knowledge("how do I breathe better?", chunks)

    assert answer == "Try bilateral breathing every 3 strokes."
    call_kwargs = mock_create.call_args.kwargs
    assert call_kwargs["messages"] == [{"role": "user", "content": "how do I breathe better?"}]
    assert "Bilateral breathing improves stroke symmetry." in call_kwargs["system"]
    assert "https://example.com/breathing" in call_kwargs["system"]


def test_answer_from_knowledge_skips_leading_thinking_blocks():
    fake_thinking_block = MagicMock(type="thinking", thinking="")
    fake_text_block = MagicMock(type="text", text="Final answer.")
    fake_response = MagicMock(content=[fake_thinking_block, fake_text_block])
    chunks = [RetrievedChunk(chunk=_make_chunk(), similarity=0.9)]

    with patch("app.rag.answer.anthropic_client.messages.create", return_value=fake_response):
        answer = answer_from_knowledge("question", chunks)

    assert answer == "Final answer."
