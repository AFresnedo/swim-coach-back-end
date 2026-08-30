from app.goal.model import Goal
from app.profile.model import Profile
from app.rag.swimmer_context import build_swimmer_context


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


def test_build_swimmer_context_includes_demographics_and_goals():
    context = build_swimmer_context(_profile(), [_goal()])

    assert "15yo female" in context
    assert "sub-60 100 free" in context


def test_build_swimmer_context_falls_back_when_no_profile_or_goals():
    assert build_swimmer_context(None, []) == "no profile or goals on file"


def test_build_swimmer_context_omits_sex_when_prefer_not_to_say():
    context = build_swimmer_context(_profile(sex="prefer_not_to_say"), [])

    assert "15yo" in context
    assert "prefer_not_to_say" not in context


def test_build_swimmer_context_summarizes_all_given_goals():
    first = _goal(text="sub-60 100 free")
    second = _goal(text="qualify for states")

    context = build_swimmer_context(None, [first, second])

    assert "sub-60 100 free" in context
    assert "qualify for states" in context
