"""Application startup validation for production deployments."""

from __future__ import annotations

import logging

from app.auth.jwt import DEFAULT_DEV_SECRET
from app.config import settings

logger = logging.getLogger(__name__)


def validate_startup() -> None:
    """Fail fast when production configuration is unsafe."""
    if not settings.is_production:
        logger.info("APP_ENV=development — demo login and legacy auth allowed")
        return

    errors: list[str] = []
    if not settings.jwt_secret or settings.jwt_secret == DEFAULT_DEV_SECRET:
        errors.append("JWT_SECRET must be set to a strong random value in production")
    if settings.allow_legacy_user_id_auth:
        errors.append("ALLOW_LEGACY_USER_ID_AUTH must be false in production")
    if settings.allow_demo_login:
        errors.append("ALLOW_DEMO_LOGIN should be false in production")
    if not settings.cors_origins or settings.cors_origins.strip() == "*":
        errors.append("CORS_ORIGINS must list explicit frontend origins in production")

    if errors:
        raise RuntimeError("Unsafe production configuration: " + "; ".join(errors))

    logger.info("Production configuration validated")
