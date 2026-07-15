from __future__ import annotations

from fastapi import Depends, Header, HTTPException, status

from app.auth.audit import audit_event
from app.auth.jwt import TokenValidationError, is_jwt_token, resolve_token_identity
from app.config import settings
from app.models.schemas import AuthUser, UserRole
from app.observability import metrics
from app.storage.factory import get_storage


def _parse_bearer(authorization: str | None) -> str | None:
    if not authorization:
        return None
    parts = authorization.split(" ", 1)
    if len(parts) == 2 and parts[0].lower() == "bearer":
        return parts[1].strip()
    return authorization.strip()


def _user_from_id(user_id: str) -> AuthUser:
    user = get_storage().get_user(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unknown user")
    return AuthUser(
        user_id=user.user_id,
        name=user.name,
        role=user.role,
        borrower_id=user.borrower_id,
    )


def _resolve_user_from_token(token: str) -> AuthUser:
    if is_jwt_token(token):
        try:
            claims = resolve_token_identity(token)
        except TokenValidationError:
            metrics.increment("auth_failures_total")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired access token",
            ) from None
        return _user_from_id(claims["sub"])

    if settings.allow_legacy_user_id_auth and not settings.is_production:
        return _user_from_id(token)

    metrics.increment("auth_failures_total")
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid access token. Obtain a token via POST /api/auth/login.",
    )


async def get_current_user(
    authorization: str | None = Header(default=None),
) -> AuthUser:
    token = _parse_bearer(authorization)
    if not token:
        metrics.increment("auth_failures_total")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing credentials. Provide Authorization: Bearer <token>.",
        )
    return _resolve_user_from_token(token)


def require_roles(*roles: UserRole):
    async def _checker(user: AuthUser = Depends(get_current_user)) -> AuthUser:
        if user.role not in roles:
            audit_event(
                action="ACCESS_DENIED",
                user=user,
                outcome="denied",
                detail=f"required roles: {[r.value for r in roles]}",
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{user.role.value}' is not permitted for this action",
            )
        return user

    return _checker


require_analyst_or_manager = require_roles(UserRole.ANALYST, UserRole.MANAGER)


def assert_can_view_borrower(user: AuthUser, borrower_id: str) -> None:
    store = get_storage()
    borrower = store.get_borrower(borrower_id)
    if not borrower:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Borrower not found")

    if user.role == UserRole.MANAGER:
        return

    if user.role == UserRole.BORROWER:
        if user.borrower_id != borrower_id:
            audit_event(
                action="BORROWER_ACCESS_DENIED",
                user=user,
                borrower_id=borrower_id,
                outcome="denied",
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Borrowers may only view their own account",
            )
        return

    if user.role == UserRole.ANALYST:
        if borrower.assigned_analyst_id != user.user_id:
            audit_event(
                action="ANALYST_ACCESS_DENIED",
                user=user,
                borrower_id=borrower_id,
                outcome="denied",
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Analysts may only view borrowers assigned to them",
            )
        return

    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
