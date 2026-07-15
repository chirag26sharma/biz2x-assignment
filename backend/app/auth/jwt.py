"""Signed JWT access tokens for demo and production deployments."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import jwt
from jwt import InvalidTokenError

from app.config import settings

DEFAULT_DEV_SECRET = "dev-only-change-in-production-use-32b-min"
ALGORITHM = "HS256"
ISSUER = "biz2x-eews"


def _secret() -> str:
    return settings.jwt_secret or DEFAULT_DEV_SECRET


def create_access_token(
    user_id: str,
    role: str,
    borrower_id: str | None,
) -> tuple[str, int]:
    expires_in = settings.jwt_expiry_hours * 3600
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "role": role,
        "borrower_id": borrower_id,
        "iat": now,
        "exp": now + timedelta(seconds=expires_in),
        "iss": ISSUER,
    }
    token = jwt.encode(payload, _secret(), algorithm=ALGORITHM)
    return token, expires_in


def decode_access_token(token: str) -> dict:
    return jwt.decode(
        token,
        _secret(),
        algorithms=[ALGORITHM],
        issuer=ISSUER,
        options={"require": ["exp", "sub", "role", "iss"]},
    )


def is_jwt_token(token: str) -> bool:
    return token.count(".") == 2


class TokenValidationError(Exception):
    pass


def resolve_token_identity(token: str) -> dict:
    """Return JWT claims or raise TokenValidationError."""
    try:
        return decode_access_token(token)
    except InvalidTokenError as exc:
        raise TokenValidationError(str(exc)) from exc
