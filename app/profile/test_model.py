import pytest
from sqlalchemy.exc import IntegrityError

from app.profile.model import Profile


def _make_profile(**overrides: object) -> Profile:
    defaults = {"user_id": 1, "age": 25, "height_cm": 175.0, "weight_kg": 70.0, "sex": "male"}
    defaults.update(overrides)
    return Profile(**defaults)


def test_unit_preference_defaults_to_metric(db_session):
    profile = _make_profile()
    db_session.add(profile)
    db_session.commit()

    assert profile.unit_preference == "metric"


def test_sex_rejects_value_outside_enum(db_session):
    profile = _make_profile(sex="alien")
    db_session.add(profile)

    with pytest.raises(IntegrityError):
        db_session.commit()


def test_unit_preference_rejects_value_outside_enum(db_session):
    profile = _make_profile(unit_preference="furlongs")
    db_session.add(profile)

    with pytest.raises(IntegrityError):
        db_session.commit()


def test_user_id_unique_constraint(db_session):
    db_session.add(_make_profile(user_id=42))
    db_session.commit()

    db_session.add(_make_profile(user_id=42))
    with pytest.raises(IntegrityError):
        db_session.commit()
