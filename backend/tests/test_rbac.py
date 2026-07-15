from __future__ import annotations

from fastapi.testclient import TestClient


def test_health_ok(client: TestClient):
    res = client.get("/health")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "ok"


def test_ready_ok(client: TestClient):
    res = client.get("/ready")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "ready"
    assert body["borrowers_loaded"] >= 10


def test_metrics_endpoint(client: TestClient):
    client.get("/health")
    res = client.get("/metrics")
    assert res.status_code == 200
    assert "http_requests_total" in res.text


def test_analyst_a001_sees_assigned_borrower(client: TestClient, auth):
    res = client.get("/api/borrowers/B101/assessment", headers=auth("A001"))
    assert res.status_code == 200
    assert res.json()["borrower_id"] == "B101"


def test_analyst_a001_denied_unassigned_borrower(client: TestClient, auth):
    res = client.get("/api/borrowers/B104/assessment", headers=auth("A001"))
    assert res.status_code == 403


def test_borrower_can_view_own_assessment(client: TestClient, auth):
    res = client.get("/api/borrowers/B101/assessment", headers=auth("U_B101"))
    assert res.status_code == 200


def test_borrower_denied_other_borrower(client: TestClient, auth):
    res = client.get("/api/borrowers/B102/assessment", headers=auth("U_B101"))
    assert res.status_code == 403


def test_borrower_denied_llm_explanation(client: TestClient, auth):
    res = client.get("/api/borrowers/B101/explanation", headers=auth("U_B101"))
    assert res.status_code == 403


def test_borrower_can_get_deterministic_update(client: TestClient, auth):
    res = client.get("/api/borrowers/B101/borrower-update", headers=auth("U_B101"))
    assert res.status_code == 200
    body = res.json()
    assert body["llm_used"] is False
    assert "explanation" in body


def test_analyst_can_access_explanation(client: TestClient, auth):
    res = client.get("/api/borrowers/B101/explanation", headers=auth("A001"))
    assert res.status_code == 200


def test_borrower_profile_redacts_internal_fields(client: TestClient, auth):
    res = client.get("/api/borrowers/B101/profile", headers=auth("U_B101"))
    assert res.status_code == 200
    body = res.json()
    assert "assigned_analyst_id" not in body
    assert "scenario_tag" not in body


def test_qa_rejects_empty_question(client: TestClient, auth):
    res = client.post(
        "/api/borrowers/B101/qa",
        headers=auth("A001"),
        json={"question": ""},
    )
    assert res.status_code == 422


def test_login_returns_jwt(client: TestClient):
    res = client.post("/api/auth/login", json={"user_id": "A001"})
    assert res.status_code == 200
    body = res.json()
    assert body["token"].count(".") == 2
    assert body["expires_in"] > 0
    assert body["user"]["role"] == "analyst"


def test_auth_me(client: TestClient, auth):
    res = client.get("/api/auth/me", headers=auth("A001"))
    assert res.status_code == 200
    assert res.json()["user_id"] == "A001"
