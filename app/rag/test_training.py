from unittest.mock import MagicMock, patch

from app.rag.retrieval import RetrievedChunk
from app.rag.training import ask_training


def _chunk(similarity: float):
    return RetrievedChunk(chunk=MagicMock(source_url="https://example.com"), similarity=similarity)


def _mock_profile_lookup(db: MagicMock, profile: MagicMock | None) -> None:
    """Makes db.query(Profile).filter(...).first() - the exact chain
    ask_training uses to fetch the swimmer's Profile - return `profile`."""
    db.query.return_value.filter.return_value.first.return_value = profile


def test_ask_training_answers_from_knowledge_base_on_hit():
    db = MagicMock()
    first_pass_chunk = _chunk(0.9)

    with (
        patch("app.rag.training.clean_question", return_value="cleaned question") as mock_clean,
        patch("app.rag.training.embed_query", return_value=[0.1]) as mock_embed,
        patch("app.rag.training.search_swim_knowledge", return_value=[first_pass_chunk]) as mock_search,
        patch("app.rag.training.answer_from_knowledge", return_value="Do more bilateral breathing.") as mock_answer,
        patch("app.rag.training.is_sharpen_enabled") as mock_sharpen_enabled,
        patch("app.rag.training.settings") as mock_settings,
    ):
        mock_settings.similarity_threshold = 0.75
        result = ask_training(db, user_id=1, raw_question="  how do i breathe better?  ")

    mock_clean.assert_called_once_with("  how do i breathe better?  ")
    mock_embed.assert_called_once_with("cleaned question")
    mock_search.assert_called_once_with(db, [0.1])
    mock_answer.assert_called_once()
    mock_sharpen_enabled.assert_not_called()
    assert result.answer == "Do more bilateral breathing."
    assert result.answered_from_knowledge_base is True


def test_ask_training_skips_sharpen_and_returns_no_match_when_fallback_disabled():
    db = MagicMock()
    first_pass_chunk = _chunk(0.5)

    with (
        patch("app.rag.training.clean_question", return_value="cleaned question"),
        patch("app.rag.training.embed_query", return_value=[0.1]) as mock_embed,
        patch("app.rag.training.search_swim_knowledge", return_value=[first_pass_chunk]) as mock_search,
        patch("app.rag.training.answer_from_knowledge") as mock_answer,
        patch("app.rag.training.sharpen_question") as mock_sharpen,
        patch("app.rag.training.is_sharpen_enabled", return_value=False),
        patch("app.rag.training.settings") as mock_settings,
    ):
        mock_settings.similarity_threshold = 0.75
        result = ask_training(db, user_id=1, raw_question="vague question")

    mock_sharpen.assert_not_called()
    mock_answer.assert_not_called()
    mock_embed.assert_called_once()
    mock_search.assert_called_once()
    assert result.answered_from_knowledge_base is False
    assert result.sources == []


def test_ask_training_returns_no_match_answer_when_kb_empty():
    db = MagicMock()
    with (
        patch("app.rag.training.clean_question", return_value="cleaned question"),
        patch("app.rag.training.embed_query", return_value=[0.1]),
        patch("app.rag.training.search_swim_knowledge", return_value=[]),
        patch("app.rag.training.answer_from_knowledge") as mock_answer,
        patch("app.rag.training.is_sharpen_enabled", return_value=False),
    ):
        result = ask_training(db, user_id=1, raw_question="anything")

    mock_answer.assert_not_called()
    assert result.answered_from_knowledge_base is False


def test_ask_training_sharpen_rescue_flips_miss_to_hit_when_enabled():
    db = MagicMock()
    fake_profile = MagicMock()
    _mock_profile_lookup(db, fake_profile)
    first_pass_chunk = _chunk(0.5)
    rescued_chunk = _chunk(0.95)

    with (
        patch("app.rag.training.clean_question", return_value="cleaned question"),
        patch("app.rag.training.embed_query", side_effect=[[0.1], [0.2]]) as mock_embed,
        patch(
            "app.rag.training.search_swim_knowledge", side_effect=[[first_pass_chunk], [rescued_chunk]]
        ) as mock_search,
        patch("app.rag.training.fetch_active_goals", return_value=["goal"]) as mock_goals,
        patch("app.rag.training.sharpen_question", return_value="sharpened question") as mock_sharpen,
        patch("app.rag.training.answer_from_knowledge", return_value="Sharpened answer.") as mock_answer,
        patch("app.rag.training.is_sharpen_enabled", return_value=True),
        patch("app.rag.training.settings") as mock_settings,
    ):
        mock_settings.similarity_threshold = 0.75
        result = ask_training(db, user_id=1, raw_question="help me get faster")

    mock_goals.assert_called_once_with(db, 1)
    mock_sharpen.assert_called_once_with("cleaned question", profile=fake_profile, goals=["goal"])
    assert mock_embed.call_args_list[1].args == ("sharpened question",)
    assert mock_search.call_count == 2
    mock_answer.assert_called_once_with("sharpened question", [rescued_chunk])
    assert result.answer == "Sharpened answer."
    assert result.answered_from_knowledge_base is True
    assert result.sources == ["https://example.com"]


def test_ask_training_sharpen_rescue_still_misses_returns_no_match():
    db = MagicMock()
    _mock_profile_lookup(db, None)
    first_pass_chunk = _chunk(0.5)
    rescued_chunk = _chunk(0.6)

    with (
        patch("app.rag.training.clean_question", return_value="cleaned question"),
        patch("app.rag.training.embed_query", side_effect=[[0.1], [0.2]]),
        patch("app.rag.training.search_swim_knowledge", side_effect=[[first_pass_chunk], [rescued_chunk]]),
        patch("app.rag.training.fetch_active_goals", return_value=[]),
        patch("app.rag.training.sharpen_question", return_value="sharpened question"),
        patch("app.rag.training.answer_from_knowledge") as mock_answer,
        patch("app.rag.training.is_sharpen_enabled", return_value=True),
        patch("app.rag.training.settings") as mock_settings,
    ):
        mock_settings.similarity_threshold = 0.75
        result = ask_training(db, user_id=1, raw_question="still vague")

    mock_answer.assert_not_called()
    assert result.answered_from_knowledge_base is False
    assert result.sources == []
