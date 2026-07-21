import pytest
from pydantic import ValidationError

from app.rag.schema import TrainingAskIn


def test_accepts_valid_question():
    ask = TrainingAskIn(question="How do I improve my flip turn?")
    assert ask.question == "How do I improve my flip turn?"


def test_rejects_empty_question():
    with pytest.raises(ValidationError):
        TrainingAskIn(question="")


def test_rejects_question_over_max_length():
    with pytest.raises(ValidationError):
        TrainingAskIn(question="x" * 2_001)
