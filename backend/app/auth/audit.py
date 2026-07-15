"""Structured audit trail for sensitive data and LLM access."""

from __future__ import annotations

import json
import logging
from contextvars import ContextVar
from datetime import datetime, timezone

from app.models.schemas import AuthUser

request_id_var: ContextVar[str] = ContextVar("request_id", default="-")
client_ip_var: ContextVar[str] = ContextVar("client_ip", default="-")

audit_logger = logging.getLogger("audit")


def audit_event(
    *,
    action: str,
    user: AuthUser | None,
    borrower_id: str | None = None,
    outcome: str = "success",
    detail: str = "",
) -> None:
    """Append-only style audit record (stdout / log aggregator in production)."""
    record = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "request_id": request_id_var.get(),
        "client_ip": client_ip_var.get(),
        "action": action,
        "user_id": user.user_id if user else None,
        "role": user.role.value if user else None,
        "borrower_id": borrower_id,
        "outcome": outcome,
        "detail": detail,
    }
    audit_logger.info(json.dumps(record, separators=(",", ":")))
