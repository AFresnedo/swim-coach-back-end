import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session


def test_get_profile_not_found(client, auth_headers):
    response = client.get("/profile", headers=auth_headers)
    assert response.status_code == 404


def test_get_profile_unauthenticated(client):
    response = client.get("/profile")
    assert response.status_code == 401


def test_get_profile_returns_existing(client, auth_headers):
    client.put(
        "/profile",
        json={"age": 25, "height_cm": 180.0, "weight_kg": 75.0, "sex": "male"},
        headers=auth_headers,
    )

    response = client.get("/profile", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["age"] == 25
    assert body["sex"] == "male"


def test_create_profile(client, auth_headers):
    response = client.put(
        "/profile",
        json={"age": 25, "height_cm": 180.0, "weight_kg": 75.0, "sex": "male"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["age"] == 25
    assert body["sex"] == "male"
    assert body["unit_preference"] == "metric"


def test_create_profile_with_imperial_preference(client, auth_headers):
    response = client.put(
        "/profile",
        json={
            "age": 25,
            "height_cm": 180.0,
            "weight_kg": 75.0,
            "sex": "male",
            "unit_preference": "imperial",
        },
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["unit_preference"] == "imperial"


def test_create_profile_invalid_unit_preference(client, auth_headers):
    response = client.put(
        "/profile",
        json={
            "age": 25,
            "height_cm": 180.0,
            "weight_kg": 75.0,
            "sex": "male",
            "unit_preference": "furlongs",
        },
        headers=auth_headers,
    )
    assert response.status_code == 422


def test_upsert_profile_updates_existing(client, auth_headers):
    first = client.put(
        "/profile",
        json={"age": 25, "height_cm": 180.0, "weight_kg": 75.0, "sex": "male"},
        headers=auth_headers,
    )
    profile_id = first.json()["id"]

    second = client.put(
        "/profile",
        json={"age": 26, "height_cm": 181.0, "weight_kg": 76.0, "sex": "male"},
        headers=auth_headers,
    )
    assert second.status_code == 200
    assert second.json()["id"] == profile_id
    assert second.json()["age"] == 26


def test_create_profile_unauthenticated(client):
    response = client.put(
        "/profile",
        json={"age": 25, "height_cm": 180.0, "weight_kg": 75.0, "sex": "male"},
    )
    assert response.status_code == 401


def test_create_profile_prefer_not_to_say(client, auth_headers):
    response = client.put(
        "/profile",
        json={"age": 25, "height_cm": 180.0, "weight_kg": 75.0, "sex": "prefer_not_to_say"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["sex"] == "prefer_not_to_say"


def test_create_profile_invalid_sex(client, auth_headers):
    response = client.put(
        "/profile",
        json={"age": 25, "height_cm": 180.0, "weight_kg": 75.0, "sex": "alien"},
        headers=auth_headers,
    )
    assert response.status_code == 422


def test_upsert_profile_race_falls_back_to_update(client, auth_headers, monkeypatch):
    from sqlalchemy.orm import Query

    from app.models import Profile

    first = client.put(
        "/profile",
        json={"age": 25, "height_cm": 180.0, "weight_kg": 75.0, "sex": "male"},
        headers=auth_headers,
    )
    assert first.status_code == 200
    profile_id = first.json()["id"]

    # Simulate two concurrent PUT /profile calls for the same brand-new user both
    # seeing "no profile yet" before either commits (TOCTOU race): force the first
    # Profile lookup to report None even though the profile above already exists,
    # so this request proceeds to INSERT and collides with it at commit time. Only
    # the *first* Profile query is faked - the fallback re-query after the race is
    # detected must see the real row, and the auth dependency's own User lookup
    # must be unaffected.
    original_first = Query.first
    profile_query_count = {"n": 0}

    def fake_first(self):
        is_profile_query = any(desc["type"] is Profile for desc in self.column_descriptions)
        if is_profile_query:
            profile_query_count["n"] += 1
            if profile_query_count["n"] == 1:
                return None
        return original_first(self)

    monkeypatch.setattr(Query, "first", fake_first)

    second = client.put(
        "/profile",
        json={"age": 40, "height_cm": 190.0, "weight_kg": 90.0, "sex": "female"},
        headers=auth_headers,
    )
    assert second.status_code == 200
    assert second.json()["id"] == profile_id
    assert second.json()["age"] == 40


def test_upsert_profile_reraises_unrelated_integrity_error(client, auth_headers, monkeypatch):
    # Proves the except block actually discriminates by cause instead of assuming
    # every IntegrityError here means a user_id race: a constraint violation that
    # has nothing to do with "user_id" must propagate as-is, not get silently
    # treated as "someone else already created this profile."
    def fake_commit(self):
        raise IntegrityError("INSERT", {}, Exception("some unrelated constraint violation"))

    monkeypatch.setattr(Session, "commit", fake_commit)

    with pytest.raises(IntegrityError):
        client.put(
            "/profile",
            json={"age": 25, "height_cm": 180.0, "weight_kg": 75.0, "sex": "male"},
            headers=auth_headers,
        )
