import pytest
from pydantic import ValidationError

from app.profile.schema import ProfileIn


def _valid_payload(**overrides: object) -> dict:
    defaults = {"age": 25, "height_cm": 175.0, "weight_kg": 70.0, "sex": "male"}
    defaults.update(overrides)
    return defaults


def test_accepts_valid_payload():
    profile = ProfileIn(**_valid_payload())
    assert profile.unit_preference == "metric"


def test_rejects_age_below_minimum():
    with pytest.raises(ValidationError):
        ProfileIn(**_valid_payload(age=4))


def test_rejects_age_above_maximum():
    with pytest.raises(ValidationError):
        ProfileIn(**_valid_payload(age=121))


def test_rejects_height_below_minimum():
    with pytest.raises(ValidationError):
        ProfileIn(**_valid_payload(height_cm=49))


def test_rejects_weight_above_maximum():
    with pytest.raises(ValidationError):
        ProfileIn(**_valid_payload(weight_kg=401))


def test_rejects_sex_outside_enum():
    with pytest.raises(ValidationError):
        ProfileIn(**_valid_payload(sex="alien"))


def test_rejects_unit_preference_outside_enum():
    with pytest.raises(ValidationError):
        ProfileIn(**_valid_payload(unit_preference="furlongs"))
