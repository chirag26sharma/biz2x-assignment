from __future__ import annotations

from datetime import date

from app.services.explanation import build_borrower_update_response, borrower_template_explanation
from app.services.risk_engine import assess_borrower
from app.storage.factory import get_storage

AS_OF = date(2026, 7, 15)

INTERNAL_TERMS = (
    "Critical",
    "High Risk",
    "Watchlist",
    "restructuring review",
    "manual analyst review",
    "DPD",
    "utilization",
)


def test_borrower_template_avoids_internal_taxonomy():
    borrower = get_storage().get_borrower("B110")
    assert borrower is not None
    assessment = assess_borrower(borrower, as_of=AS_OF)
    text = borrower_template_explanation(borrower, assessment)
    for term in INTERNAL_TERMS:
        assert term not in text


def test_borrower_update_response_flags_no_llm():
    borrower = get_storage().get_borrower("B101")
    assert borrower is not None
    assessment = assess_borrower(borrower, as_of=AS_OF)
    response = build_borrower_update_response(borrower, assessment)
    assert response.llm_used is False
    assert response.grounded is True
    assert "A note about your account" in response.explanation
