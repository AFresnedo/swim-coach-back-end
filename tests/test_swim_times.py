VALID_SWIM_TIME = {
    "date": "2026-07-01",
    "stroke": "freestyle",
    "course": "scy",
    "length": 100,
    "attempt_number": 1,
    "time_seconds": 58.32,
    "is_official": False,
    "notes": "felt strong on the back half",
}


def test_create_swim_time(client, auth_headers):
    response = client.post("/swim-times", json=VALID_SWIM_TIME, headers=auth_headers)
    assert response.status_code == 201
    body = response.json()
    assert body["stroke"] == "freestyle"
    assert body["course"] == "scy"
    assert body["length"] == 100
    assert body["time_seconds"] == 58.32
    assert body["is_official"] is False


def test_create_swim_time_unauthenticated(client):
    response = client.post("/swim-times", json=VALID_SWIM_TIME)
    assert response.status_code == 401


def test_create_swim_time_invalid_stroke_rejected(client, auth_headers):
    payload = {**VALID_SWIM_TIME, "stroke": "sidestroke"}
    response = client.post("/swim-times", json=payload, headers=auth_headers)
    assert response.status_code == 422


def test_create_swim_time_invalid_course_rejected(client, auth_headers):
    payload = {**VALID_SWIM_TIME, "course": "olympic"}
    response = client.post("/swim-times", json=payload, headers=auth_headers)
    assert response.status_code == 422


def test_create_swim_time_non_positive_time_rejected(client, auth_headers):
    payload = {**VALID_SWIM_TIME, "time_seconds": 0}
    response = client.post("/swim-times", json=payload, headers=auth_headers)
    assert response.status_code == 422


def test_list_swim_times_orders_most_recent_first(client, auth_headers):
    older = {**VALID_SWIM_TIME, "date": "2026-06-01"}
    newer = {**VALID_SWIM_TIME, "date": "2026-07-01"}
    client.post("/swim-times", json=older, headers=auth_headers)
    client.post("/swim-times", json=newer, headers=auth_headers)

    response = client.get("/swim-times", headers=auth_headers)
    assert response.status_code == 200
    dates = [t["date"] for t in response.json()]
    assert dates == ["2026-07-01", "2026-06-01"]


def test_list_swim_times_respects_limit(client, auth_headers):
    for i in range(3):
        client.post("/swim-times", json={**VALID_SWIM_TIME, "attempt_number": i + 1}, headers=auth_headers)

    response = client.get("/swim-times", params={"limit": 2}, headers=auth_headers)
    assert response.status_code == 200
    assert len(response.json()) == 2


def test_list_swim_times_only_returns_own_times(client, auth_headers):
    client.post("/swim-times", json=VALID_SWIM_TIME, headers=auth_headers)

    other = client.post(
        "/auth/register",
        json={"name": "Other User", "email": "other-swim@example.com", "password": "supersecret123"},
    )
    other_headers = {"Authorization": f"Bearer {other.json()['access_token']}"}
    client.post("/swim-times", json=VALID_SWIM_TIME, headers=other_headers)

    response = client.get("/swim-times", headers=auth_headers)
    assert response.status_code == 200
    assert len(response.json()) == 1
