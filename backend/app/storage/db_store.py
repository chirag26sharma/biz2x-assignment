"""DB storage stub — activate when DATABASE_URL is configured."""

from __future__ import annotations

from app.models.schemas import BorrowerRecord, UserRecord
from app.storage.base import StorageBackend


class DatabaseStorage(StorageBackend):
    def __init__(self, database_url: str) -> None:
        self.database_url = database_url
        raise NotImplementedError(
            "DatabaseStorage is reserved for production. "
            "Set STORAGE_BACKEND=file until DB credentials are provided."
        )

    def list_borrowers(self) -> list[BorrowerRecord]:
        raise NotImplementedError

    def get_borrower(self, borrower_id: str) -> BorrowerRecord | None:
        raise NotImplementedError

    def list_users(self) -> list[UserRecord]:
        raise NotImplementedError

    def get_user(self, user_id: str) -> UserRecord | None:
        raise NotImplementedError

    def list_borrowers_for_analyst(self, analyst_id: str) -> list[BorrowerRecord]:
        raise NotImplementedError
