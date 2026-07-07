def test_create_goal(client, auth_headers):
    response = client.post("/goals", json={"text": "Swim a sub-1:00 100m free"}, headers=auth_headers)
    assert response.status_code == 201
    body = response.json()
    assert body["text"] == "Swim a sub-1:00 100m free"
    assert body["is_active"] is True
    assert body["deactivation_reason"] is None


def test_create_goal_unauthenticated(client):
    response = client.post("/goals", json={"text": "Swim faster"})
    assert response.status_code == 401


def test_create_goal_blank_text_rejected(client, auth_headers):
    response = client.post("/goals", json={"text": ""}, headers=auth_headers)
    assert response.status_code == 422


def test_create_goal_text_too_long_rejected(client, auth_headers):
    response = client.post("/goals", json={"text": "a" * 2001}, headers=auth_headers)
    assert response.status_code == 422


def test_list_goals_returns_only_active(client, auth_headers):
    client.post("/goals", json={"text": "Goal one"}, headers=auth_headers)
    second = client.post("/goals", json={"text": "Goal two"}, headers=auth_headers)

    client.patch(f"/goals/{second.json()['id']}/deactivate", json={"reason": "reached"}, headers=auth_headers)

    response = client.get("/goals", headers=auth_headers)
    assert response.status_code == 200
    texts = [g["text"] for g in response.json()]
    assert texts == ["Goal one"]


def test_list_goals_status_all_returns_everything(client, auth_headers):
    client.post("/goals", json={"text": "Goal one"}, headers=auth_headers)
    second = client.post("/goals", json={"text": "Goal two"}, headers=auth_headers)

    client.patch(f"/goals/{second.json()['id']}/deactivate", json={"reason": "reached"}, headers=auth_headers)

    response = client.get("/goals", params={"status": "all"}, headers=auth_headers)
    assert response.status_code == 200
    texts = [g["text"] for g in response.json()]
    assert texts == ["Goal two", "Goal one"]


def test_list_goals_invalid_status_rejected(client, auth_headers):
    response = client.get("/goals", params={"status": "bogus"}, headers=auth_headers)
    assert response.status_code == 422


def test_list_goals_only_returns_own_goals(client, auth_headers):
    client.post("/goals", json={"text": "My goal"}, headers=auth_headers)

    other = client.post(
        "/auth/register",
        json={"name": "Other User", "email": "other@example.com", "password": "supersecret123"},
    )
    other_headers = {"Authorization": f"Bearer {other.json()['access_token']}"}
    client.post("/goals", json={"text": "Other goal"}, headers=other_headers)

    response = client.get("/goals", headers=auth_headers)
    texts = [g["text"] for g in response.json()]
    assert texts == ["My goal"]


def test_update_goal_text(client, auth_headers):
    created = client.post("/goals", json={"text": "Original"}, headers=auth_headers)
    goal_id = created.json()["id"]

    response = client.patch(f"/goals/{goal_id}", json={"text": "Updated"}, headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["text"] == "Updated"


def test_update_goal_not_found(client, auth_headers):
    response = client.patch("/goals/999", json={"text": "Updated"}, headers=auth_headers)
    assert response.status_code == 404


def test_update_goal_owned_by_another_user_not_found(client, auth_headers):
    other = client.post(
        "/auth/register",
        json={"name": "Other User", "email": "other2@example.com", "password": "supersecret123"},
    )
    other_headers = {"Authorization": f"Bearer {other.json()['access_token']}"}
    created = client.post("/goals", json={"text": "Their goal"}, headers=other_headers)
    goal_id = created.json()["id"]

    response = client.patch(f"/goals/{goal_id}", json={"text": "Hijacked"}, headers=auth_headers)
    assert response.status_code == 404


def test_deactivate_goal_with_reason(client, auth_headers):
    created = client.post("/goals", json={"text": "Goal to retire"}, headers=auth_headers)
    goal_id = created.json()["id"]

    response = client.patch(f"/goals/{goal_id}/deactivate", json={"reason": "abandoned"}, headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["is_active"] is False
    assert body["deactivation_reason"] == "abandoned"


def test_deactivate_goal_invalid_reason_rejected(client, auth_headers):
    created = client.post("/goals", json={"text": "Goal to retire"}, headers=auth_headers)
    goal_id = created.json()["id"]

    response = client.patch(f"/goals/{goal_id}/deactivate", json={"reason": "bored"}, headers=auth_headers)
    assert response.status_code == 422


def test_deactivate_goal_not_found(client, auth_headers):
    response = client.patch("/goals/999/deactivate", json={"reason": "reached"}, headers=auth_headers)
    assert response.status_code == 404


def test_deactivate_goal_owned_by_another_user_not_found(client, auth_headers):
    other = client.post(
        "/auth/register",
        json={"name": "Other User", "email": "other3@example.com", "password": "supersecret123"},
    )
    other_headers = {"Authorization": f"Bearer {other.json()['access_token']}"}
    created = client.post("/goals", json={"text": "Their goal"}, headers=other_headers)
    goal_id = created.json()["id"]

    response = client.patch(f"/goals/{goal_id}/deactivate", json={"reason": "reached"}, headers=auth_headers)
    assert response.status_code == 404
