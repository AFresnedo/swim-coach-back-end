VALID_SWIM_TIME = {
    "date": "2026-07-01",
    "stroke": "freestyle",
    "course": "scy",
    "length": 100,
    "attempt_number": 1,
    "time_seconds": 58.32,
    "is_official": False,
    "notes": None,
}


def test_users_count_zero(client):
    response = client.get("/stats/users-count")
    assert response.status_code == 200
    assert response.json() == {"user_count": 0}


def test_users_count_after_registrations(client):
    for i in range(3):
        client.post(
            "/auth/register",
            json={"name": f"User {i}", "email": f"user{i}@example.com", "password": "supersecret123"},
        )
    response = client.get("/stats/users-count")
    assert response.status_code == 200
    assert response.json() == {"user_count": 3}


def test_users_count_does_not_require_auth(client):
    response = client.get("/stats/users-count")
    assert response.status_code == 200
    assert "user_count" in response.json()


def test_swims_count_zero(client):
    response = client.get("/stats/swims-count")
    assert response.status_code == 200
    assert response.json() == {"swim_count": 0}


def test_swims_count_after_creation(client, auth_headers):
    for _ in range(3):
        client.post("/swim-times", json=VALID_SWIM_TIME, headers=auth_headers)
    response = client.get("/stats/swims-count")
    assert response.status_code == 200
    assert response.json() == {"swim_count": 3}


def test_swims_count_does_not_require_auth(client):
    response = client.get("/stats/swims-count")
    assert response.status_code == 200
    assert "swim_count" in response.json()


def test_users_count_rate_limit_exceeded(client):
    for _ in range(30):
        response = client.get("/stats/users-count")
        assert response.status_code == 200

    response = client.get("/stats/users-count")
    assert response.status_code == 429
    assert response.json() == {"detail": "Too many requests. Try again later."}
    assert "Retry-After" in response.headers


def test_swims_count_rate_limit_exceeded(client):
    for _ in range(30):
        response = client.get("/stats/swims-count")
        assert response.status_code == 200

    response = client.get("/stats/swims-count")
    assert response.status_code == 429
    assert response.json() == {"detail": "Too many requests. Try again later."}
    assert "Retry-After" in response.headers
