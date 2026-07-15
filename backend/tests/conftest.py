from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.storage.factory import clear_storage_cache, get_storage


@pytest.fixture(autouse=True)
def _test_runtime(monkeypatch):
    clear_storage_cache()
    monkeypatch.setattr("app.config.settings.rate_limit_enabled", False)
    yield
    clear_storage_cache()


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def storage():
    return get_storage()


@pytest.fixture
def token_for(client: TestClient):
    def _issue(user_id: str) -> str:
        res = client.post("/api/auth/login", json={"user_id": user_id})
        assert res.status_code == 200, res.text
        return res.json()["token"]

    return _issue


@pytest.fixture
def auth(token_for):
    def _headers(user_id: str) -> dict[str, str]:
        return {"Authorization": f"Bearer {token_for(user_id)}"}

    return _headers
