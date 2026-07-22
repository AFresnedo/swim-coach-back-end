from datetime import UTC, date, datetime

from app.swim_time.model import SwimTime
from app.user.model import User

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
    body = response.json()
    dates = [t["date"] for t in body["items"]]
    assert dates == ["2026-07-01", "2026-06-01"]
    assert body["next_cursor"] is None


def test_list_swim_times_respects_limit(client, auth_headers):
    for i in range(3):
        client.post("/swim-times", json={**VALID_SWIM_TIME, "attempt_number": i + 1}, headers=auth_headers)

    response = client.get("/swim-times", params={"limit": 2}, headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert len(body["items"]) == 2
    assert body["next_cursor"] is not None


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
    assert len(response.json()["items"]) == 1


def test_list_swim_times_cursor_walks_full_set_without_overlap(client, auth_headers):
    for i in range(5):
        client.post(
            "/swim-times",
            json={**VALID_SWIM_TIME, "date": f"2026-07-{i + 1:02d}", "attempt_number": i + 1},
            headers=auth_headers,
        )

    seen_dates = []
    cursor = None
    for _ in range(10):
        params = {"limit": 2}
        if cursor is not None:
            params["cursor"] = cursor
        response = client.get("/swim-times", params=params, headers=auth_headers)
        assert response.status_code == 200
        body = response.json()
        seen_dates.extend(t["date"] for t in body["items"])
        cursor = body["next_cursor"]
        if cursor is None:
            break

    assert seen_dates == ["2026-07-05", "2026-07-04", "2026-07-03", "2026-07-02", "2026-07-01"]
    assert cursor is None


def test_list_swim_times_cursor_handles_same_date_tiebreak(client, auth_headers):
    created_ids = []
    for i in range(4):
        response = client.post(
            "/swim-times",
            json={**VALID_SWIM_TIME, "date": "2026-07-01", "attempt_number": i + 1},
            headers=auth_headers,
        )
        created_ids.append(response.json()["id"])

    seen_ids = []
    cursor = None
    for _ in range(10):
        params = {"limit": 1}
        if cursor is not None:
            params["cursor"] = cursor
        response = client.get("/swim-times", params=params, headers=auth_headers)
        assert response.status_code == 200
        body = response.json()
        seen_ids.extend(t["id"] for t in body["items"])
        cursor = body["next_cursor"]
        if cursor is None:
            break

    assert sorted(seen_ids) == sorted(created_ids)
    assert len(seen_ids) == len(set(seen_ids))


def test_list_swim_times_cursor_survives_exact_created_at_collision(client, auth_headers, db_session):
    user = db_session.query(User).filter(User.email == "test@example.com").first()
    tied_at = datetime(2026, 7, 1, 12, 0, 0, tzinfo=UTC)

    row_a = SwimTime(
        user_id=user.id,
        date=date(2026, 7, 1),
        stroke="freestyle",
        course="scy",
        length=100,
        attempt_number=1,
        time_seconds=58.0,
        is_official=False,
        created_at=tied_at,
    )
    row_b = SwimTime(
        user_id=user.id,
        date=date(2026, 7, 1),
        stroke="freestyle",
        course="scy",
        length=100,
        attempt_number=2,
        time_seconds=59.0,
        is_official=False,
        created_at=tied_at,
    )
    db_session.add_all([row_a, row_b])
    db_session.commit()

    seen_ids = []
    cursor = None
    for _ in range(5):
        params = {"limit": 1}
        if cursor is not None:
            params["cursor"] = cursor
        response = client.get("/swim-times", params=params, headers=auth_headers)
        assert response.status_code == 200
        body = response.json()
        seen_ids.extend(t["id"] for t in body["items"])
        cursor = body["next_cursor"]
        if cursor is None:
            break

    assert sorted(seen_ids) == sorted([row_a.id, row_b.id])


def test_list_swim_times_invalid_cursor_rejected(client, auth_headers):
    response = client.get("/swim-times", params={"cursor": "not-valid-base64!!"}, headers=auth_headers)
    assert response.status_code == 422


def test_list_swim_times_filters_by_stroke(client, auth_headers):
    client.post("/swim-times", json={**VALID_SWIM_TIME, "stroke": "freestyle"}, headers=auth_headers)
    client.post("/swim-times", json={**VALID_SWIM_TIME, "stroke": "butterfly"}, headers=auth_headers)

    response = client.get("/swim-times", params={"stroke": "butterfly"}, headers=auth_headers)
    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) == 1
    assert items[0]["stroke"] == "butterfly"


def test_list_swim_times_filters_by_course(client, auth_headers):
    client.post("/swim-times", json={**VALID_SWIM_TIME, "course": "scy"}, headers=auth_headers)
    client.post("/swim-times", json={**VALID_SWIM_TIME, "course": "lcm"}, headers=auth_headers)

    response = client.get("/swim-times", params={"course": "lcm"}, headers=auth_headers)
    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) == 1
    assert items[0]["course"] == "lcm"


def test_list_swim_times_filters_by_length(client, auth_headers):
    client.post("/swim-times", json={**VALID_SWIM_TIME, "length": 100}, headers=auth_headers)
    client.post("/swim-times", json={**VALID_SWIM_TIME, "length": 200}, headers=auth_headers)

    response = client.get("/swim-times", params={"length": 200}, headers=auth_headers)
    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) == 1
    assert items[0]["length"] == 200


def test_list_swim_times_filters_by_is_official(client, auth_headers):
    client.post("/swim-times", json={**VALID_SWIM_TIME, "is_official": True}, headers=auth_headers)
    client.post("/swim-times", json={**VALID_SWIM_TIME, "is_official": False}, headers=auth_headers)

    response = client.get("/swim-times", params={"is_official": True}, headers=auth_headers)
    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) == 1
    assert items[0]["is_official"] is True


def test_list_swim_times_filters_by_date_range(client, auth_headers):
    client.post("/swim-times", json={**VALID_SWIM_TIME, "date": "2026-06-01"}, headers=auth_headers)
    client.post("/swim-times", json={**VALID_SWIM_TIME, "date": "2026-07-01"}, headers=auth_headers)
    client.post("/swim-times", json={**VALID_SWIM_TIME, "date": "2026-08-01"}, headers=auth_headers)

    response = client.get(
        "/swim-times", params={"date_from": "2026-06-15", "date_to": "2026-07-15"}, headers=auth_headers
    )
    assert response.status_code == 200
    items = response.json()["items"]
    assert [t["date"] for t in items] == ["2026-07-01"]


def test_list_swim_times_combined_filters(client, auth_headers):
    client.post(
        "/swim-times",
        json={**VALID_SWIM_TIME, "stroke": "freestyle", "date": "2026-07-01"},
        headers=auth_headers,
    )
    client.post(
        "/swim-times",
        json={**VALID_SWIM_TIME, "stroke": "butterfly", "date": "2026-07-01"},
        headers=auth_headers,
    )
    client.post(
        "/swim-times",
        json={**VALID_SWIM_TIME, "stroke": "freestyle", "date": "2026-05-01"},
        headers=auth_headers,
    )

    response = client.get(
        "/swim-times",
        params={"stroke": "freestyle", "date_from": "2026-06-01", "date_to": "2026-08-01"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) == 1
    assert items[0]["stroke"] == "freestyle"
    assert items[0]["date"] == "2026-07-01"
