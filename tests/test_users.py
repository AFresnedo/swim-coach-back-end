def test_user_count_zero(client):
    response = client.get("/users/count")
    assert response.status_code == 200
    assert response.json() == {"user_count": 0}


def test_user_count_after_registrations(client):
    for i in range(3):
        client.post(
            "/auth/register",
            json={"name": f"User {i}", "email": f"user{i}@example.com", "password": "supersecret123"},
        )
    response = client.get("/users/count")
    assert response.status_code == 200
    assert response.json() == {"user_count": 3}


def test_user_count_does_not_require_auth(client):
    response = client.get("/users/count")
    assert response.status_code == 200
    assert "user_count" in response.json()
