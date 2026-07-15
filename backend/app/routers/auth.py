from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse

from app.auth.audit import audit_event
from app.auth.dependencies import get_current_user
from app.auth.jwt import create_access_token
from app.config import settings
from app.models.schemas import AuthUser, LoginRequest, LoginResponse
from app.observability import metrics
from app.storage.factory import get_storage

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/users")
def list_demo_users() -> list[AuthUser]:
    """Demo helper: list simulated users for the login picker."""
    if not settings.allow_demo_login:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Demo user listing is disabled",
        )
    return [
        AuthUser(
            user_id=u.user_id,
            name=u.name,
            role=u.role,
            borrower_id=u.borrower_id,
        )
        for u in get_storage().list_users()
    ]


@router.post("/login", response_model=LoginResponse)
def login(body: LoginRequest) -> JSONResponse:
    user = get_storage().get_user(body.user_id)
    if not user:
        metrics.increment("auth_failures_total")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unknown user")

    auth_user = AuthUser(
        user_id=user.user_id,
        name=user.name,
        role=user.role,
        borrower_id=user.borrower_id,
    )
    token, expires_in = create_access_token(
        user.user_id,
        user.role.value,
        user.borrower_id,
    )
    payload = LoginResponse(
        user=auth_user,
        token=token,
        expires_in=expires_in,
    )
    audit_event(action="LOGIN", user=auth_user, outcome="success")
    response = JSONResponse(content=payload.model_dump())
    response.set_cookie(
        key="eews_token",
        value=token,
        httponly=True,
        samesite="lax",
        secure=settings.is_production,
        max_age=expires_in,
        path="/",
    )
    return response


@router.get("/me", response_model=AuthUser)
def me(user: AuthUser = Depends(get_current_user)) -> AuthUser:
    return user
