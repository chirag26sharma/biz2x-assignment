from __future__ import annotations

import json
from pathlib import Path
from threading import Lock

from app.models.schemas import BorrowerRecord, UserRecord
from app.storage.base import StorageBackend


class FileStorage(StorageBackend):
    """JSON file-backed storage for the assignment prototype."""

    def __init__(self, file_path: str) -> None:
        self._path = Path(file_path)
        self._lock = Lock()
        self._borrowers: dict[str, BorrowerRecord] = {}
        self._users: dict[str, UserRecord] = {}
        self._load()

    def _load(self) -> None:
        if not self._path.exists():
            raise FileNotFoundError(f"Mock dataset not found: {self._path}")
        raw = json.loads(self._path.read_text(encoding="utf-8"))
        self._borrowers = {
            item["borrower_id"]: BorrowerRecord.model_validate(item)
            for item in raw.get("borrowers", [])
        }
        self._users = {
            item["user_id"]: UserRecord.model_validate(item)
            for item in raw.get("users", [])
        }

    def list_borrowers(self) -> list[BorrowerRecord]:
        with self._lock:
            return list(self._borrowers.values())

    def get_borrower(self, borrower_id: str) -> BorrowerRecord | None:
        with self._lock:
            return self._borrowers.get(borrower_id)

    def list_users(self) -> list[UserRecord]:
        with self._lock:
            return list(self._users.values())

    def get_user(self, user_id: str) -> UserRecord | None:
        with self._lock:
            return self._users.get(user_id)

    def list_borrowers_for_analyst(self, analyst_id: str) -> list[BorrowerRecord]:
        with self._lock:
            return [b for b in self._borrowers.values() if b.assigned_analyst_id == analyst_id]
