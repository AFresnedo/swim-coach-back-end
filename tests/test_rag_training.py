from unittest.mock import MagicMock, patch

from app.rag.retrieval import RetrievedChunk
from app.rag.training import ask_training


def _chunk(similarity: float):
    return RetrievedChunk(chunk=object(), similarity=similarity)


def test_ask_training_answers_from_knowledge_base_on_hit():
    db = MagicMock()
    with (
        patch("app.rag.training.clean_question", return_value="cleaned question") as mock_clean,
        patch("app.rag.training.embed_query", return_value=[0.1]) as mock_embed,
        patch("app.rag.training.search_swim_knowledge", return_value=[_chunk(0.9)]) as mock_search,
        patch("app.rag.training.answer_from_knowledge", return_value="Do more bilateral breathing.") as mock_answer,
        patch("app.rag.training.settings") as mock_settings,
    ):
        mock_settings.similarity_threshold = 0.75
        result = ask_training(db, raw_question="  how do i breathe better?  ")

    mock_clean.assert_called_once_with("  how do i breathe better?  ")
    mock_embed.assert_called_once_with("cleaned question")
    mock_search.assert_called_once_with(db, [0.1])
    mock_answer.assert_called_once()
    assert result.answer == "Do more bilateral breathing."
    assert result.answered_from_knowledge_base is True


def test_ask_training_returns_no_match_answer_when_similarity_below_threshold():
    db = MagicMock()
    with (
        patch("app.rag.training.clean_question", return_value="cleaned question"),
        patch("app.rag.training.embed_query", return_value=[0.1]),
        patch("app.rag.training.search_swim_knowledge", return_value=[_chunk(0.5)]),
        patch("app.rag.training.answer_from_knowledge") as mock_answer,
        patch("app.rag.training.settings") as mock_settings,
    ):
        mock_settings.similarity_threshold = 0.75
        result = ask_training(db, raw_question="vague question")

    mock_answer.assert_not_called()
    assert result.answered_from_knowledge_base is False
    assert result.sources == []


def test_ask_training_returns_no_match_answer_when_kb_empty():
    db = MagicMock()
    with (
        patch("app.rag.training.clean_question", return_value="cleaned question"),
        patch("app.rag.training.embed_query", return_value=[0.1]),
        patch("app.rag.training.search_swim_knowledge", return_value=[]),
        patch("app.rag.training.answer_from_knowledge") as mock_answer,
    ):
        result = ask_training(db, raw_question="anything")

    mock_answer.assert_not_called()
    assert result.answered_from_knowledge_base is False
