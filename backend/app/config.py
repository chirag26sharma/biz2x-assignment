"""Centralized configuration for risk thresholds and system assumptions.

All undocumented assignment parameters live here (and are mirrored in README).
Do not hardcode these values inline in scoring logic.
"""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_BASE_DIR = Path(__file__).resolve().parent.parent
_ENV_FILE = _BASE_DIR / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Loan Default Risk Early Warning System"
    app_env: str = "development"  # development | production
    storage_backend: str = "file"  # "file" | "db" (db reserved for future)
    data_file: str = str(Path(__file__).resolve().parent.parent / "data" / "mock_dataset.json")
    database_url: str | None = None

    # Auth / security
    jwt_secret: str = ""
    jwt_expiry_hours: int = 8
    allow_demo_login: bool = True
    allow_legacy_user_id_auth: bool = True  # dev only: Bearer <user_id> without JWT

    llm_base_url: str = "https://llm-wrapper-741152993481.asia-south1.run.app"
    llm_api_token: str = ""
    llm_timeout_seconds: float = 60.0
    llm_max_response_chars: int = 8000

    cors_origins: str = "http://localhost:3000"

    # Security / abuse controls
    qa_max_question_length: int = 500
    rate_limit_requests_per_minute: int = 120
    rate_limit_llm_requests_per_minute: int = 15
    rate_limit_login_per_minute: int = 20
    rate_limit_enabled: bool = True

    @property
    def is_production(self) -> bool:
        return self.app_env.strip().lower() == "production"

    # --- Risk engine assumptions (documented in README) ---
    # Minimum completed payment cycles required before full scoring.
    min_payment_history_cycles: int = 3

    # Lookback windows
    payment_trend_window: int = 3  # last N EMIs for DPD / partial-payment trends
    transaction_lookback_days: int = 90
    income_baseline_days: int = 90  # prior window vs recent window for income comparison
    income_recent_days: int = 30
    failed_autodebit_lookback_days: int = 60
    balance_trend_window: int = 3  # last N balance snapshots

    # Signal thresholds
    dpd_increasing_min_delta: int = 1  # avg DPD rise considered a worsening trend
    failed_autodebit_count_watch: int = 2
    failed_autodebit_count_high: int = 3
    utilization_watch_pct: float = 70.0
    utilization_high_pct: float = 85.0
    utilization_rise_pct_points: float = 15.0  # rise vs prior snapshot
    income_decline_pct: float = 30.0  # recent vs baseline inflow drop
    balance_decline_pct: float = 25.0  # decline across balance snapshots
    partial_payment_count_watch: int = 1
    current_dpd_critical: int = 30
    current_dpd_high: int = 15
    current_dpd_watch: int = 1

    # Signal weights (points added when signal fires)
    weight_dpd_trend: int = 20
    weight_current_dpd_watch: int = 10
    weight_current_dpd_high: int = 25
    weight_current_dpd_critical: int = 40
    weight_failed_autodebit_watch: int = 15
    weight_failed_autodebit_high: int = 25
    weight_utilization_watch: int = 10
    weight_utilization_high: int = 20
    weight_utilization_rising: int = 15
    weight_income_decline: int = 20
    weight_balance_decline: int = 15
    weight_partial_or_skipped: int = 20
    weight_insufficient_history: int = 5  # soft flag only; caps category at Watchlist

    # Category score bands (inclusive lower bounds for next band start)
    score_watchlist_min: int = 20
    score_high_min: int = 45
    score_critical_min: int = 70

    # Horizon the early-warning system targets (informational)
    delinquency_horizon_days: int = 30


settings = Settings()
