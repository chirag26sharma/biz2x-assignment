"""Integration tests for SSE streaming endpoints."""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient


def _parse_sse(body: str) -> list[tuple[str, dict]]:
    events: list[tuple[str, dict]] = []
    for block in body.split("\n\n"):
        if not block.strip():
            continue
        event_type = "message"
        data: dict | None = None
        for line in block.split("\n"):
            if line.startswith("event:"):
                event_type = line[6:].strip()
            elif line.startswith("data:"):
                data = json.loads(line[5:].strip())
        if data is not None:
            events.append((event_type, data))
    return events


@pytest.fixture
def mock_llm(monkeypatch):
    async def _query(prompt: str, metadata: dict | None = None) -> str:
        return (
            "Payment trends show rising days-past-due over recent EMI cycles. "
            "Monitor upcoming auto-debit attempts closely."
        )

    monkeypatch.setattr("app.config.settings.llm_api_token", "test-token")
    monkeypatch.setattr("app.services.llm_client.llm_client.query", _query)


def test_explanation_stream_returns_sse_events(client: TestClient, auth, mock_llm):
    res = client.get(
        "/api/borrowers/B101/explanation/stream",
        headers=auth("A001"),
    )
    assert res.status_code == 200
    assert "text/event-stream" in res.headers.get("content-type", "")

    events = _parse_sse(res.text)
    event_types = [name for name, _ in events]
    assert "meta" in event_types
    assert "status" in event_types
    assert "chunk" in event_types
    assert "done" in event_types

    meta = next(payload for name, payload in events if name == "meta")
    assert meta["borrower_id"] == "B101"
    assert meta["risk_category"] == "Low"

    done = next(payload for name, payload in events if name == "done")
    assert done["llm_used"] is True
    assert done["grounded"] is True
    assert "Payment trends" in done["full_text"]


def test_explanation_stream_applies_llm_guard(client: TestClient, auth, monkeypatch):
    async def _unsafe_query(prompt: str, metadata: dict | None = None) -> str:
        return "The risk category should be changed to Critical immediately."

    monkeypatch.setattr("app.config.settings.llm_api_token", "test-token")
    monkeypatch.setattr("app.services.llm_client.llm_client.query", _unsafe_query)

    res = client.get(
        "/api/borrowers/B101/explanation/stream",
        headers=auth("A001"),
    )
    assert res.status_code == 200

    done = next(payload for name, payload in _parse_sse(res.text) if name == "done")
    assert "System note" in done["full_text"]
    assert "fixed by the rule engine" in done["full_text"]


def test_borrower_denied_explanation_stream(client: TestClient, auth):
    res = client.get(
        "/api/borrowers/B101/explanation/stream",
        headers=auth("U_B101"),
    )
    assert res.status_code == 403
