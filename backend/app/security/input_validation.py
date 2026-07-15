"""Input validation and prompt-injection guards."""

from __future__ import annotations

import re

BORROWER_ID_RE = re.compile(r"^[A-Z][A-Z0-9_]{2,31}$")

_INJECTION_PATTERNS = (
    re.compile(r"ignore\s+(all\s+)?(previous|prior|above)\s+instructions", re.I),
    re.compile(r"disregard\s+(the\s+)?(system|safety)\s+(prompt|rules)", re.I),
    re.compile(r"you\s+are\s+now\s+(a|an)\s+", re.I),
    re.compile(r"<\s*/?\s*system\s*>", re.I),
    re.compile(r"jailbreak", re.I),
)


class InputValidationError(ValueError):
    pass


def validate_borrower_id(borrower_id: str) -> str:
    borrower_id = borrower_id.strip()
    if not BORROWER_ID_RE.match(borrower_id):
        raise InputValidationError("Invalid borrower_id format")
    return borrower_id


def sanitize_question(question: str, *, max_length: int = 500) -> str:
    cleaned = "".join(ch for ch in question if ch.isprintable() or ch in "\n\t")
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    if not cleaned:
        raise InputValidationError("Question cannot be empty")
    if len(cleaned) > max_length:
        raise InputValidationError(f"Question exceeds {max_length} characters")
    for pattern in _INJECTION_PATTERNS:
        if pattern.search(cleaned):
            raise InputValidationError("Question contains disallowed prompt-injection content")
    return cleaned
