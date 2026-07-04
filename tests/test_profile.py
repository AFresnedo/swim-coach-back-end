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
