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


def test_upsert_profile_creates_then_updates_on_postgres(pg_client, pg_auth_headers):
    # The default `client` fixture is SQLite, which only exercises the sqlite branch
    # of the ON CONFLICT upsert. This runs the same create-then-update against real
    # Postgres, covering upsert_returning's postgresql dialect path end to end.
    first = pg_client.put(
        "/profile",
        json={"age": 25, "height_cm": 180.0, "weight_kg": 75.0, "sex": "male"},
        headers=pg_auth_headers,
    )
    assert first.status_code == 200
    profile_id = first.json()["id"]

    second = pg_client.put(
        "/profile",
        json={"age": 26, "height_cm": 181.0, "weight_kg": 76.0, "sex": "male"},
        headers=pg_auth_headers,
    )
    assert second.status_code == 200
    assert second.json()["id"] == profile_id
    assert second.json()["age"] == 26
