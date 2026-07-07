import pytest
from pydantic import ValidationError

from app.config import Settings


def test_settings_rejects_invalid_rate_limit_string(monkeypatch):
    monkeypatch.setenv("LOGIN_RATE_LIMIT_PER_EMAIL", "5/nonsense-unit")
    with pytest.raises(ValidationError):
        Settings()


def test_settings_accepts_valid_rate_limit_strings(monkeypatch):
    monkeypatch.setenv("LOGIN_RATE_LIMIT_PER_EMAIL", "10/day")
    settings = Settings()
    assert settings.login_rate_limit_per_email == "10/day"
