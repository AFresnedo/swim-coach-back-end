import pytest
from pydantic import ValidationError

from app.rate_limit_config import RateLimitSettings


def test_accepts_a_well_formed_rate_limit_string():
    settings = RateLimitSettings(login_rate_limit_per_email="10/day")
    assert settings.login_rate_limit_per_email == "10/day"


def test_rejects_a_malformed_rate_limit_string():
    with pytest.raises(ValidationError):
        RateLimitSettings(login_rate_limit_per_email="5/nonsense-unit")
