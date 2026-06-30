from datetime import UTC, datetime, timedelta

import jwt

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


def test_me_expired_token(client, registered_user_token):
    expired_payload = {
        "sub": registered_user_token["email"],
        "exp": datetime.now(UTC) - timedelta(minutes=1),
    }
    expired_token = jwt.encode(expired_payload, settings.secret_key, algorithm=ALGORITHM)
    response = client.get("/auth/me", headers={"Authorization": f"Bearer {expired_token}"})
    assert response.status_code == 401
