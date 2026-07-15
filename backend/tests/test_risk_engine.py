from __future__ import annotations

from datetime import date

from app.models.schemas import RiskCategory
from app.services.risk_engine import assess_borrower, simulate_miss_next_emi
from app.storage.factory import get_storage

AS_OF = date(2026, 7, 15)


def _assess(borrower_id: str):
    borrower = get_storage().get_borrower(borrower_id)
    assert borrower is not None
    return assess_borrower(borrower, as_of=AS_OF)


def test_b101_healthy_low_risk():
    result = _assess("B101")
    assert result.risk_category == RiskCategory.LOW
    assert result.insufficient_history is False


def test_b102_rising_dpd_high_risk():
    result = _assess("B102")
    assert result.risk_category == RiskCategory.HIGH_RISK
    codes = {s.code for s in result.signals}
    assert "DPD_TREND_WORSENING" in codes or "CURRENT_DPD_HIGH" in codes


def test_b110_critical_multi_signal():
    result = _assess("B110")
    assert result.risk_category == RiskCategory.CRITICAL
    assert result.risk_score >= 70


def test_b108_missing_payments_capped_watchlist():
    result = _assess("B108")
    assert result.risk_category == RiskCategory.WATCHLIST
    assert result.insufficient_history is True


def test_b109_insufficient_history_capped():
    result = _assess("B109")
    assert result.risk_category == RiskCategory.WATCHLIST
    assert result.insufficient_history is True


def test_scenario_miss_next_emi_increases_score():
    borrower = get_storage().get_borrower("B102")
    assert borrower is not None
    baseline = assess_borrower(borrower, as_of=AS_OF)
    simulated = simulate_miss_next_emi(borrower, as_of=AS_OF)
    assert simulated.risk_score >= baseline.risk_score


def test_b103_failed_autodebit_high_risk():
    result = _assess("B103")
    assert result.risk_category == RiskCategory.HIGH_RISK
    codes = {s.code for s in result.signals}
    assert "FAILED_AUTODEBIT_HIGH" in codes


def test_b104_utilization_high_risk():
    result = _assess("B104")
    assert result.risk_category == RiskCategory.HIGH_RISK
    codes = {s.code for s in result.signals}
    assert "UTILIZATION_HIGH" in codes or "UTILIZATION_RISING" in codes


def test_b105_balance_decline_high_risk():
    result = _assess("B105")
    assert result.risk_category == RiskCategory.HIGH_RISK
    codes = {s.code for s in result.signals}
    assert "BALANCE_DECLINE" in codes


def test_b106_partial_or_skipped_high_risk():
    result = _assess("B106")
    assert result.risk_category == RiskCategory.HIGH_RISK
    codes = {s.code for s in result.signals}
    assert "PARTIAL_OR_SKIPPED" in codes


def test_b107_balance_decline_high_risk():
    result = _assess("B107")
    assert result.risk_category == RiskCategory.HIGH_RISK
    codes = {s.code for s in result.signals}
    assert "BALANCE_DECLINE" in codes
