from __future__ import annotations

from abc import ABC, abstractmethod

from app.models.schemas import BorrowerRecord, UserRecord


class StorageBackend(ABC):
    """Abstract data access layer. Swap FileStore for a DB implementation later."""

    @abstractmethod
    def list_borrowers(self) -> list[BorrowerRecord]:
        raise NotImplementedError

    @abstractmethod
    def get_borrower(self, borrower_id: str) -> BorrowerRecord | None:
        raise NotImplementedError

    @abstractmethod
    def list_users(self) -> list[UserRecord]:
        raise NotImplementedError

    @abstractmethod
    def get_user(self, user_id: str) -> UserRecord | None:
        raise NotImplementedError

    @abstractmethod
    def list_borrowers_for_analyst(self, analyst_id: str) -> list[BorrowerRecord]:
        raise NotImplementedError
