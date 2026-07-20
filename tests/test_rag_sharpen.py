from unittest.mock import MagicMock, patch

from app.models import Goal, Profile
from app.rag.sharpen import sharpen_question


def _profile(**overrides: object) -> Profile:
    defaults = {
        "user_id": 1,
        "age": 15,
        "height_cm": 170.0,
        "weight_kg": 60.0,
        "sex": "female",
        "unit_preference": "metric",
    }
    defaults.update(overrides)
    return Profile(**defaults)


def _goal(**overrides: object) -> Goal:
    defaults = {"user_id": 1, "text": "sub-60 100 free", "is_active": True}
    defaults.update(overrides)
    return Goal(**defaults)


def test_sharpen_question_returns_rewritten_text_and_includes_swimmer_context():
    fake_text_block = MagicMock(type="text", text="  How can I improve my 100m freestyle sprint speed?  ")
    fake_response = MagicMock(content=[fake_text_block])

    with patch("app.rag.sharpen.anthropic_client.messages.create", return_value=fake_response) as mock_create:
        result = sharpen_question("help me get faster", profile=_profile(), goals=[_goal()])

    assert result == "How can I improve my 100m freestyle sprint speed?"
    call_kwargs = mock_create.call_args.kwargs
    assert call_kwargs["messages"] == [{"role": "user", "content": "help me get faster"}]
    assert "15yo female" in call_kwargs["system"]
    assert "sub-60 100 free" in call_kwargs["system"]


def test_sharpen_question_handles_no_profile_or_goals():
    fake_text_block = MagicMock(type="text", text="rewritten")
    fake_response = MagicMock(content=[fake_text_block])

    with patch("app.rag.sharpen.anthropic_client.messages.create", return_value=fake_response) as mock_create:
        sharpen_question("vague question", profile=None, goals=[])

    call_kwargs = mock_create.call_args.kwargs
    assert "no profile or goals on file" in call_kwargs["system"]


def test_sharpen_question_omits_sex_when_prefer_not_to_say():
    fake_text_block = MagicMock(type="text", text="rewritten")
    fake_response = MagicMock(content=[fake_text_block])
    profile = _profile(sex="prefer_not_to_say")

    with patch("app.rag.sharpen.anthropic_client.messages.create", return_value=fake_response) as mock_create:
        sharpen_question("question", profile=profile, goals=[])

    call_kwargs = mock_create.call_args.kwargs
    assert "15yo" in call_kwargs["system"]
    assert "prefer_not_to_say" not in call_kwargs["system"]


def test_sharpen_question_summarizes_all_given_goals():
    fake_text_block = MagicMock(type="text", text="rewritten")
    fake_response = MagicMock(content=[fake_text_block])
    first = _goal(text="sub-60 100 free")
    second = _goal(text="qualify for states")

    with patch("app.rag.sharpen.anthropic_client.messages.create", return_value=fake_response) as mock_create:
        sharpen_question("question", profile=None, goals=[first, second])

    call_kwargs = mock_create.call_args.kwargs
    assert "sub-60 100 free" in call_kwargs["system"]
    assert "qualify for states" in call_kwargs["system"]
