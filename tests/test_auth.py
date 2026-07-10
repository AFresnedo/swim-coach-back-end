from datetime import UTC, datetime, timedelta

import jwt
import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import settings
from app.security import ALGORITHM


def test_register_success(client):
    response = client.post(
        "/auth/register",
        json={"name": "Alice", "email": "alice@example.com", "password": "longenoughpw"},
    )
    assert response.status_code == 201
    body = response.json()
    assert "access_token" in body
    assert body["token_type"] == "bearer"


def test_register_duplicate_email(client, registered_user_token):
    response = client.post(
        "/auth/register",
        json={"name": "Dup", "email": registered_user_token["email"], "password": "anotherpassword"},
    )
    assert response.status_code == 400


def test_register_weak_password(client):
    response = client.post(
        "/auth/register",
        json={"name": "Bob", "email": "bob@example.com", "password": "short"},
    )
    assert response.status_code == 422


def test_login_success(client, registered_user_token):
    response = client.post(
        "/auth/login",
        json={"email": registered_user_token["email"], "password": registered_user_token["password"]},
    )
    assert response.status_code == 200
    assert "access_token" in response.json()


def test_login_wrong_password(client, registered_user_token):
    response = client.post(
        "/auth/login",
        json={"email": registered_user_token["email"], "password": "wrongpassword"},
    )
    assert response.status_code == 401


def test_login_nonexistent_email(client):
    response = client.post(
        "/auth/login",
        json={"email": "nobody-here@example.com", "password": "whatever123"},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect email or password"


def test_register_race_returns_400_not_500(client, monkeypatch):
    from sqlalchemy.orm import Query

    payload = {"name": "Racer", "email": "racer@example.com", "password": "supersecret123"}

    first = client.post("/auth/register", json=payload)
    assert first.status_code == 201

    # Simulate two concurrent registrations for the same email both passing the
    # SELECT check before either commits (TOCTOU race): force the pre-check to
    # report "no existing user" even though the row above already exists, so this
    # request proceeds straight to INSERT and collides with it at commit time.
    monkeypatch.setattr(Query, "first", lambda self: None)

    second = client.post("/auth/register", json={**payload, "name": "Racer Two"})
    assert second.status_code == 400
    assert second.json()["detail"] == "Email already registered"


def test_register_reraises_unrelated_integrity_error(client, monkeypatch):
    # Proves the except block actually discriminates by cause instead of assuming
    # every IntegrityError here means a duplicate email: a constraint violation
    # that has nothing to do with "email" must propagate as-is, not get mislabeled.
    def fake_commit(self):
        raise IntegrityError("INSERT", {}, Exception("some unrelated constraint violation"))

    monkeypatch.setattr(Session, "commit", fake_commit)

    with pytest.raises(IntegrityError):
        client.post(
            "/auth/register",
            json={"name": "X", "email": "unrelated@example.com", "password": "supersecret123"},
        )


def test_register_rate_limit_exceeded(client):
    for i in range(5):
        response = client.post(
            "/auth/register",
            json={"name": f"User{i}", "email": f"rl-register-{i}@example.com", "password": "supersecret123"},
        )
        assert response.status_code == 201

    response = client.post(
        "/auth/register",
        json={"name": "Overflow", "email": "rl-register-overflow@example.com", "password": "supersecret123"},
    )
    assert response.status_code == 429
    assert response.json() == {"detail": "Too many requests. Try again later."}
    assert "Retry-After" in response.headers


def test_login_rate_limit_per_email_exceeded(client, registered_user_token):
    email = registered_user_token["email"]
    for _ in range(5):
        response = client.post("/auth/login", json={"email": email, "password": "wrongpassword"})
        assert response.status_code == 401

    response = client.post("/auth/login", json={"email": email, "password": "wrongpassword"})
    assert response.status_code == 429
    assert response.json() == {"detail": "Too many requests. Try again later."}
    assert "Retry-After" in response.headers


def test_login_rate_limit_per_email_is_independent_per_email(client, registered_user_token):
    email = registered_user_token["email"]
    for _ in range(5):
        client.post("/auth/login", json={"email": email, "password": "wrongpassword"})
    blocked = client.post("/auth/login", json={"email": email, "password": "wrongpassword"})
    assert blocked.status_code == 429

    # A different email must be unaffected - proves the limit is keyed per email,
    # not shared globally across every login attempt.
    other = client.post("/auth/login", json={"email": "someone-else@example.com", "password": "whatever123"})
    assert other.status_code == 401


def test_login_rate_limit_per_ip_exceeded(client):
    # Use a distinct email per call so the per-email limit (5/5minutes) never
    # trips first - this isolates testing the broader per-IP limit (20/5minutes).
    for i in range(20):
        response = client.post("/auth/login", json={"email": f"rl-ip-{i}@example.com", "password": "whatever123"})
        assert response.status_code == 401

    response = client.post("/auth/login", json={"email": "rl-ip-overflow@example.com", "password": "whatever123"})
    assert response.status_code == 429
    assert response.json() == {"detail": "Too many requests. Try again later."}


def test_me_valid_token(client, auth_headers):
    response = client.get("/auth/me", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["email"] == "test@example.com"


def test_me_missing_token(client):
    response = client.get("/auth/me")
    assert response.status_code == 401


def test_me_invalid_token(client):
    response = client.get("/auth/me", headers={"Authorization": "Bearer not-a-real-token"})
    assert response.status_code == 401


def test_me_expired_token(client):
    expired_payload = {
        # Value is irrelevant here: jwt.decode raises on the expired exp claim
        # before decode_access_token ever inspects sub.
        "sub": "1",
        "exp": datetime.now(UTC) - timedelta(minutes=1),
    }
    expired_token = jwt.encode(expired_payload, settings.secret_key, algorithm=ALGORITHM)
    response = client.get("/auth/me", headers={"Authorization": f"Bearer {expired_token}"})
    assert response.status_code == 401


def test_access_token_subject_is_user_id_not_email(registered_user_token):
    # Locks in the fix: sub must be the immutable user id, not the mutable email,
    # so a token can't resolve to a different account if email reuse is ever
    # possible (e.g. a future email-change feature).
    payload = jwt.decode(registered_user_token["token"], settings.secret_key, algorithms=[ALGORITHM])
    assert payload["sub"] != registered_user_token["email"]
    assert payload["sub"].isdigit()


def test_logout_invalidates_the_token_used_to_log_out(client, auth_headers):
    logout_response = client.post("/auth/logout", headers=auth_headers)
    assert logout_response.status_code == 204

    response = client.get("/auth/me", headers=auth_headers)
    assert response.status_code == 401


def test_logout_invalidates_other_outstanding_tokens_too(client, registered_user_token):
    # A user can hold more than one valid token at once (e.g. two devices), since
    # nothing here tracks individual sessions. Logout must kill all of them, not
    # just the one presented to the endpoint itself.
    email, password = registered_user_token["email"], registered_user_token["password"]
    older_token = registered_user_token["token"]

    login_response = client.post("/auth/login", json={"email": email, "password": password})
    newer_headers = {"Authorization": f"Bearer {login_response.json()['access_token']}"}

    client.post("/auth/logout", headers=newer_headers)

    assert client.get("/auth/me", headers={"Authorization": f"Bearer {older_token}"}).status_code == 401
    assert client.get("/auth/me", headers=newer_headers).status_code == 401


def test_logout_requires_auth(client):
    response = client.post("/auth/logout")
    assert response.status_code == 401


def test_login_after_logout_issues_a_working_token(client, registered_user_token):
    email, password = registered_user_token["email"], registered_user_token["password"]
    old_headers = {"Authorization": f"Bearer {registered_user_token['token']}"}
    client.post("/auth/logout", headers=old_headers)

    login_response = client.post("/auth/login", json={"email": email, "password": password})
    new_headers = {"Authorization": f"Bearer {login_response.json()['access_token']}"}

    assert client.get("/auth/me", headers=new_headers).status_code == 200


def test_me_rejects_unexpired_token_missing_iat_claim(client, registered_user_token):
    # Simulates a token minted before this feature shipped: has a still-valid exp
    # but no iat at all (the pre-jwt-revoke token shape). Must be rejected purely
    # because decode_access_token requires iat - there's no token_valid_after
    # comparison to fall back on, since decoding fails before that check runs.
    existing_payload = jwt.decode(registered_user_token["token"], settings.secret_key, algorithms=[ALGORITHM])
    payload_without_iat = {"sub": existing_payload["sub"], "exp": datetime.now(UTC) + timedelta(minutes=5)}
    token_without_iat = jwt.encode(payload_without_iat, settings.secret_key, algorithm=ALGORITHM)

    response = client.get("/auth/me", headers={"Authorization": f"Bearer {token_without_iat}"})
    assert response.status_code == 401
