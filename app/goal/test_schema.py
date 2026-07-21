import pytest
from pydantic import ValidationError

from app.goal.schema import GoalDeactivateReason, GoalIn


def test_goal_in_accepts_valid_text():
    goal = GoalIn(text="Swim a 50 free under 25 seconds")
    assert goal.text == "Swim a 50 free under 25 seconds"


def test_goal_in_rejects_empty_text():
    with pytest.raises(ValidationError):
        GoalIn(text="")


def test_goal_in_rejects_text_over_max_length():
    with pytest.raises(ValidationError):
        GoalIn(text="x" * 2_001)


def test_goal_deactivate_reason_rejects_value_outside_enum():
    with pytest.raises(ValidationError):
        GoalDeactivateReason(reason="changed-my-mind")  # pyright: ignore[reportArgumentType]


def test_goal_deactivate_reason_accepts_enum_value():
    reason = GoalDeactivateReason(reason="reached")
    assert reason.reason == "reached"
