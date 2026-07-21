from datetime import UTC, datetime, timedelta

import pytest
from fastapi import HTTPException

from app.deps import get_current_user
from app.security import create_access_token
from app.user.model import User


def _make_user(db_session, **overrides: object) -> User:
    defaults: dict[str, object] = {"name": "Alice", "email": "alice@example.com", "hashed_password": "not-a-real-hash"}
    defaults.update(overrides)
    user = User(**defaults)
    db_session.add(user)
    db_session.commit()
    return user


def test_returns_the_user_for_a_valid_token(db_session):
    user = _make_user(db_session)
    token = create_access_token(subject=user.id)

    result = get_current_user(token=token, db=db_session)

    assert result.id == user.id


def test_rejects_an_undecodable_token(db_session):
    with pytest.raises(HTTPException) as exc_info:
        get_current_user(token="not-a-real-token", db=db_session)

    assert exc_info.value.status_code == 401


def test_rejects_a_valid_token_for_a_user_that_no_longer_exists(db_session):
    # A syntactically and cryptographically valid token can still reference a
    # user_id with no matching row - nothing today deletes users, but a token
    # surviving a dev-database reset hits the exact same path, so this must be
    # rejected rather than crash on a None lookup.
    token = create_access_token(subject=999_999)

    with pytest.raises(HTTPException) as exc_info:
        get_current_user(token=token, db=db_session)

    assert exc_info.value.status_code == 401


def test_rejects_a_token_issued_before_the_revocation_cutoff(db_session):
    user = _make_user(db_session)
    token = create_access_token(subject=user.id)

    user.token_valid_after = datetime.now(UTC) + timedelta(minutes=1)
    db_session.commit()

    with pytest.raises(HTTPException) as exc_info:
        get_current_user(token=token, db=db_session)

    assert exc_info.value.status_code == 401
