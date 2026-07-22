from datetime import date

import pytest
from sqlalchemy.exc import IntegrityError

from app.swim_time.model import SwimTime


def _make_swim_time(**overrides: object) -> SwimTime:
    defaults = {
        "user_id": 1,
        "date": date(2026, 1, 1),
        "stroke": "freestyle",
        "course": "scy",
        "length": 100,
        "time_seconds": 58.0,
    }
    defaults.update(overrides)
    return SwimTime(**defaults)


def test_defaults(db_session):
    swim_time = _make_swim_time()
    db_session.add(swim_time)
    db_session.commit()

    assert swim_time.attempt_number == 1
    assert swim_time.is_official is False
    assert swim_time.notes is None
    assert swim_time.created_at is not None


def test_length_must_be_positive(db_session):
    db_session.add(_make_swim_time(length=0))
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_time_seconds_must_be_positive(db_session):
    db_session.add(_make_swim_time(time_seconds=0))
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_attempt_number_must_be_positive(db_session):
    db_session.add(_make_swim_time(attempt_number=0))
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_stroke_rejects_value_outside_enum(db_session):
    db_session.add(_make_swim_time(stroke="sidestroke"))
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_course_rejects_value_outside_enum(db_session):
    db_session.add(_make_swim_time(course="olympic"))
    with pytest.raises(IntegrityError):
        db_session.commit()
