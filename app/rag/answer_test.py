from unittest.mock import MagicMock, patch

from app.goal.model import Goal
from app.profile.model import Profile
from app.rag.answer import answer_from_knowledge
from app.rag.models import EMBEDDING_DIMENSION, SwimKnowledge
from app.rag.retrieval import RetrievedChunk
from app.rag.swimmer_context import SwimmerContext

_NO_SWIMMER = SwimmerContext(profile=None, goals=[])


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
        answer = answer_from_knowledge("how do I breathe better?", chunks, swimmer=_NO_SWIMMER)

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
        answer = answer_from_knowledge("question", chunks, swimmer=_NO_SWIMMER)

    assert answer == "Final answer."


def test_answer_from_knowledge_includes_swimmer_context():
    fake_text_block = MagicMock(type="text", text="Answer.")
    fake_response = MagicMock(content=[fake_text_block])
    chunks = [RetrievedChunk(chunk=_make_chunk(), similarity=0.9)]
    profile = Profile(user_id=1, age=15, height_cm=170.0, weight_kg=60.0, sex="female", unit_preference="metric")
    goals = [Goal(user_id=1, text="sub-60 100 free", is_active=True)]
    swimmer = SwimmerContext(profile=profile, goals=goals)

    with patch("app.rag.answer.anthropic_client.messages.create", return_value=fake_response) as mock_create:
        answer_from_knowledge("question", chunks, swimmer=swimmer)

    call_kwargs = mock_create.call_args.kwargs
    assert "15yo female" in call_kwargs["system"]
    assert "sub-60 100 free" in call_kwargs["system"]
