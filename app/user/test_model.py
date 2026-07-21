import pytest
from sqlalchemy.exc import IntegrityError

from app.user.model import User


def _make_user(**overrides: object) -> User:
    defaults: dict[str, object] = {"name": "Alice", "email": "alice@example.com", "hashed_password": "not-a-real-hash"}
    defaults.update(overrides)
    return User(**defaults)


def test_defaults(db_session):
    user = _make_user()
    db_session.add(user)
    db_session.commit()

    assert user.created_at is not None
    assert user.token_valid_after is not None


def test_email_unique_constraint(db_session):
    db_session.add(_make_user(email="dup@example.com"))
    db_session.commit()

    db_session.add(_make_user(name="Bob", email="dup@example.com"))
    with pytest.raises(IntegrityError):
        db_session.commit()
