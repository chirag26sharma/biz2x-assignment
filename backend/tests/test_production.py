from __future__ import annotations

import pytest

from app.auth.jwt import DEFAULT_DEV_SECRET
from app.startup import validate_startup


def test_production_startup_rejects_default_jwt(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("JWT_SECRET", DEFAULT_DEV_SECRET)
    monkeypatch.setenv("ALLOW_LEGACY_USER_ID_AUTH", "false")
    monkeypatch.setenv("ALLOW_DEMO_LOGIN", "false")

    from app.config import Settings

    # Rebuild settings with production env
    prod_settings = Settings()
    assert prod_settings.is_production

    with pytest.raises(RuntimeError, match="JWT_SECRET"):
        # validate_startup reads module-level settings; patch it
        import app.startup as startup_mod
        import app.config as config_mod

        monkeypatch.setattr(config_mod, "settings", prod_settings)
        monkeypatch.setattr(startup_mod, "settings", prod_settings)
        validate_startup()
