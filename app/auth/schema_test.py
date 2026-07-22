import pytest
from pydantic import ValidationError

from app.auth.schema import Token, UserCreate, UserLogin


def test_user_create_accepts_valid_payload():
    user = UserCreate(name="Alice", email="alice@example.com", password="supersecret123")
    assert user.email == "alice@example.com"


def test_user_create_rejects_malformed_email():
    with pytest.raises(ValidationError):
        UserCreate(name="Alice", email="not-an-email", password="supersecret123")


def test_user_create_rejects_short_password():
    with pytest.raises(ValidationError):
        UserCreate(name="Alice", email="alice@example.com", password="short")


def test_user_create_rejects_empty_name():
    with pytest.raises(ValidationError):
        UserCreate(name="", email="alice@example.com", password="supersecret123")


def test_user_login_rejects_malformed_email():
    with pytest.raises(ValidationError):
        UserLogin(email="not-an-email", password="whatever")


def test_token_defaults_token_type_to_bearer():
    token = Token(access_token="abc123")
    assert token.token_type == "bearer"
