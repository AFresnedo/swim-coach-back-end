import pytest
from pydantic import ValidationError

from app.rag.config import RagSettings


def _valid_kwargs(**overrides: object) -> dict:
    defaults: dict[str, object] = {"anthropic_api_key": "sk-ant-test", "voyage_api_key": "pa-test"}
    defaults.update(overrides)
    return defaults


def test_accepts_a_valid_payload():
    settings = RagSettings(**_valid_kwargs())
    assert settings.coach_model == "claude-sonnet-5"
    assert settings.sharpen_model == "claude-haiku-4-5"
    assert settings.similarity_threshold == 0.75
    assert settings.max_web_ingestions_per_query == 2


def test_rejects_coach_model_outside_the_allowed_literal():
    with pytest.raises(ValidationError):
        RagSettings(**_valid_kwargs(coach_model="gpt-4"))


def test_rejects_similarity_threshold_above_one():
    with pytest.raises(ValidationError):
        RagSettings(**_valid_kwargs(similarity_threshold=1.5))


def test_rejects_similarity_threshold_below_zero():
    with pytest.raises(ValidationError):
        RagSettings(**_valid_kwargs(similarity_threshold=-0.1))


def test_rejects_max_web_ingestions_per_query_below_one():
    with pytest.raises(ValidationError):
        RagSettings(**_valid_kwargs(max_web_ingestions_per_query=0))
