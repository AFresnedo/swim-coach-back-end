from datetime import date

import pytest
from pydantic import ValidationError

from app.swim_time.schema import SwimTimeIn


def _valid_payload(**overrides: object) -> dict:
    defaults = {"date": date(2026, 1, 1), "stroke": "freestyle", "course": "scy", "length": 100, "time_seconds": 58.0}
    defaults.update(overrides)
    return defaults


def test_accepts_valid_payload():
    swim_time = SwimTimeIn(**_valid_payload())
    assert swim_time.attempt_number == 1
    assert swim_time.is_official is False


def test_rejects_non_positive_length():
    with pytest.raises(ValidationError):
        SwimTimeIn(**_valid_payload(length=0))


def test_rejects_non_positive_time_seconds():
    with pytest.raises(ValidationError):
        SwimTimeIn(**_valid_payload(time_seconds=0))


def test_rejects_non_positive_attempt_number():
    with pytest.raises(ValidationError):
        SwimTimeIn(**_valid_payload(attempt_number=0))


def test_rejects_stroke_outside_enum():
    with pytest.raises(ValidationError):
        SwimTimeIn(**_valid_payload(stroke="sidestroke"))


def test_rejects_course_outside_enum():
    with pytest.raises(ValidationError):
        SwimTimeIn(**_valid_payload(course="olympic"))


def test_rejects_notes_over_max_length():
    with pytest.raises(ValidationError):
        SwimTimeIn(**_valid_payload(notes="x" * 2_001))
