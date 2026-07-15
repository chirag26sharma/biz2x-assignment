"""Rate limit middleware behavior."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def strict_rate_limits(monkeypatch):
    monkeypatch.setattr("app.config.settings.rate_limit_enabled", True)
    monkeypatch.setattr("app.config.settings.app_env", "production")
    monkeypatch.setattr("app.config.settings.rate_limit_llm_requests_per_minute", 2)
    monkeypatch.setattr("app.config.settings.rate_limit_requests_per_minute", 100)


def _client_ip(ip: str) -> dict[str, str]:
    return {"X-Forwarded-For": ip}


def test_llm_rate_limit_returns_429_with_retry_after(
    client: TestClient,
    auth,
    strict_rate_limits,
):
    headers = {**auth("A001"), **_client_ip("198.51.100.10")}

    for _ in range(2):
        res = client.get("/api/borrowers/B101/explanation", headers=headers)
        assert res.status_code == 200, res.text

    res = client.get("/api/borrowers/B101/explanation", headers=headers)
    assert res.status_code == 429
    body = res.json()
    assert body["detail"]
    assert body["retry_after_seconds"] >= 1
    assert res.headers.get("Retry-After")


def test_general_api_not_blocked_when_llm_limit_exhausted(
    client: TestClient,
    auth,
    strict_rate_limits,
):
    headers = {**auth("A001"), **_client_ip("198.51.100.11")}

    for _ in range(2):
        client.get("/api/borrowers/B101/explanation", headers=headers)

    blocked = client.get("/api/borrowers/B101/explanation", headers=headers)
    assert blocked.status_code == 429

    alerts = client.get("/api/alerts", headers=headers)
    assert alerts.status_code == 200

    health = client.get("/health", headers=_client_ip("198.51.100.11"))
    assert health.status_code == 200
