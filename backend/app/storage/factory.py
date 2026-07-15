from __future__ import annotations

from functools import lru_cache

from app.config import settings
from app.storage.base import StorageBackend
from app.storage.db_store import DatabaseStorage
from app.storage.file_store import FileStorage


def clear_storage_cache() -> None:
    """Clear cached storage instance (used in tests and hot-reload)."""
    get_storage.cache_clear()


@lru_cache
def get_storage() -> StorageBackend:
    backend = settings.storage_backend.lower().strip()
    if backend == "file":
        return FileStorage(settings.data_file)
    if backend == "db":
        if not settings.database_url:
            raise RuntimeError("STORAGE_BACKEND=db requires DATABASE_URL")
        return DatabaseStorage(settings.database_url)
    raise ValueError(f"Unknown STORAGE_BACKEND: {backend}")
