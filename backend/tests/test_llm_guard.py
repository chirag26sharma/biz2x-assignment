import pytest

from app.security.llm_guard import validate_llm_narration
from app.models.schemas import (
    RiskAssessment,
    RiskCategory,
    Severity,
    RecommendedAction,
)
from datetime import datetime, timezone


def _assessment() -> RiskAssessment:
    return RiskAssessment(
        borrower_id="B101",
        assessed_at=datetime.now(timezone.utc),
        risk_score=10,
        risk_category=RiskCategory.LOW,
        severity=Severity.LOW,
        recommended_action=RecommendedAction.NO_ACTION,
        signals=[],
    )


def test_llm_guard_appends_notice_on_category_override():
    text = "The risk category should be changed to Critical immediately."
    result = validate_llm_narration(text, _assessment())
    assert "System note" in result
    assert "fixed by the rule engine" in result
