"""LLM used ONLY to narrate an already-computed risk assessment."""

from __future__ import annotations

import logging

from app.config import settings
from app.models.schemas import BorrowerRecord, ExplanationResponse, RiskAssessment
from app.observability import metrics
from app.security.llm_guard import validate_llm_narration
from app.services.llm_client import llm_client

logger = logging.getLogger(__name__)


def _plain_observations(assessment: RiskAssessment) -> list[str]:
    mapping: dict[str, str] = {
        "CURRENT_DPD_WATCH": "A recent payment was slightly delayed.",
        "CURRENT_DPD_HIGH": "A recent payment was significantly delayed.",
        "CURRENT_DPD_CRITICAL": "A payment is considerably overdue.",
        "DPD_TREND_WORSENING": "Payment delays have been increasing over the last few months.",
        "FAILED_AUTODEBIT_WATCH": "A couple of recent automatic payment attempts did not go through.",
        "FAILED_AUTODEBIT_HIGH": "Several recent automatic payment attempts did not go through.",
        "UTILIZATION_WATCH": "Your loan balance has been climbing relative to your limit.",
        "UTILIZATION_HIGH": "Your loan balance is quite high relative to your available limit.",
        "UTILIZATION_RISING": "Your loan balance has risen noticeably recently.",
        "INCOME_DECLINE": "Money coming into your account has been lower than usual lately.",
        "BALANCE_DECLINE": "Your account balance has been declining.",
        "PARTIAL_OR_SKIPPED": "Some recent payments were partial or missed.",
        "INSUFFICIENT_HISTORY": "We have limited repayment history on your account so far.",
        "MISSING_PAYMENT_DATA": "We are still building a complete picture of your repayment history.",
    }
    seen: set[str] = set()
    lines: list[str] = []
    for signal in assessment.signals:
        if signal.code == "CATEGORY_CAPPED":
            continue
        plain = mapping.get(signal.code)
        if plain and plain not in seen:
            seen.add(plain)
            lines.append(plain)
    return lines


def _borrower_action_hint(action: str) -> str:
    hints = {
        "no action": "Keep paying on time — you're on track.",
        "soft reminder": "Consider setting a payment reminder before your next due date.",
        "payment plan offer": "If cash flow is tight, a flexible payment plan may help.",
        "proactive call": "Our team may reach out to see if you need support.",
        "restructuring review": "We can discuss options to make repayments more manageable.",
        "manual analyst review": "Our team will review your account and may contact you with options.",
    }
    return hints.get(action, "Reach out if you need help with your next payment.")


def borrower_template_explanation(borrower: BorrowerRecord, assessment: RiskAssessment) -> str:
    """Deterministic borrower-facing message — never uses the LLM."""
    observations = _plain_observations(assessment)
    if observations:
        bullets = "\n".join(f"- {line}" for line in observations)
        noticed = f"### What we've noticed\n{bullets}"
    else:
        noticed = "### What we've noticed\n- Your repayments look on track right now."
    hint = _borrower_action_hint(assessment.recommended_action.value)
    return (
        "## A note about your account\n\n"
        "We've been reviewing your recent repayment activity and wanted to share a quick update.\n\n"
        f"{noticed}\n\n"
        "### What you can do\n"
        f"- {hint}\n"
        "- If you're facing any difficulty, please contact us — we're here to help."
    )


def build_borrower_update_response(
    borrower: BorrowerRecord,
    assessment: RiskAssessment,
) -> ExplanationResponse:
    return ExplanationResponse(
        borrower_id=borrower.borrower_id,
        risk_category=assessment.risk_category,
        severity=assessment.severity,
        recommended_action=assessment.recommended_action,
        key_reasons=[],
        explanation=borrower_template_explanation(borrower, assessment),
        grounded=True,
        llm_used=False,
    )


def _fallback_explanation(borrower: BorrowerRecord, assessment: RiskAssessment) -> str:
    if assessment.signals:
        bullets = "\n".join(f"- **{s.label}:** {s.detail}" for s in assessment.signals)
        drivers = f"\n\n### Key drivers\n{bullets}"
    else:
        drivers = "\n\nNo material stress signals detected."
    return (
        f"## Risk explanation\n\n"
        f"**{borrower.name}** (`{borrower.borrower_id}`) is categorized as "
        f"**{assessment.risk_category.value}** with severity **{assessment.severity.value}**.\n\n"
        f"- **Deterministic score:** {assessment.risk_score}"
        f"{drivers}\n\n"
        f"### Recommended action\n"
        f"**{assessment.recommended_action.value}**"
    )


def build_explanation_prompt(borrower: BorrowerRecord, assessment: RiskAssessment) -> str:
    signal_lines = "\n".join(
        f"- [{s.code}] {s.label}: {s.detail} (points={s.points})"
        for s in assessment.signals
    ) or "- None"
    return f"""You are explaining a lending early-warning result to a credit analyst.
Use ONLY the facts below. Do not invent data, scores, or recommendations.
Do not change the risk category, severity, or recommended action — they are final.

Borrower: {borrower.name} ({borrower.borrower_id})
Loan outstanding: {borrower.loan.outstanding_balance}
EMI: {borrower.loan.emi_amount}
Next due date: {borrower.loan.next_due_date}
Risk score (deterministic): {assessment.risk_score}
Risk category (deterministic): {assessment.risk_category.value}
Severity (deterministic): {assessment.severity.value}
Recommended action (deterministic): {assessment.recommended_action.value}
Insufficient history: {assessment.insufficient_history}

Signals:
{signal_lines}

Indicators: {assessment.indicators}

Write 2-4 concise sentences explaining why this borrower was flagged (or not),
grounded strictly in the signals above. End by restating the recommended action.

Format your entire response in Markdown:
- Start with a ## heading
- Use **bold** for category, severity, score, and recommended action
- Use bullet lists for key drivers/signals when present
- Do not wrap the response in code fences
"""


async def generate_explanation(
    borrower: BorrowerRecord,
    assessment: RiskAssessment,
) -> ExplanationResponse:
    key_reasons = [s.label for s in assessment.signals]
    prompt = build_explanation_prompt(borrower, assessment)

    if not llm_client.configured:
        text = _fallback_explanation(borrower, assessment)
        return ExplanationResponse(
            borrower_id=borrower.borrower_id,
            risk_category=assessment.risk_category,
            severity=assessment.severity,
            recommended_action=assessment.recommended_action,
            key_reasons=key_reasons,
            explanation=text,
            grounded=True,
            llm_used=False,
        )

    try:
        text = await llm_client.query(
            prompt,
            metadata={"feature": "risk_explanation", "borrower_id": borrower.borrower_id},
        )
        metrics.increment("llm_calls_total")
        text = validate_llm_narration(text, assessment)
        if len(text) > settings.llm_max_response_chars:
            text = text[: settings.llm_max_response_chars] + "\n\n…"
        llm_used = True
    except Exception as exc:
        logger.warning("LLM explanation failed for %s: %s", borrower.borrower_id, exc)
        text = _fallback_explanation(borrower, assessment)
        llm_used = False

    return ExplanationResponse(
        borrower_id=borrower.borrower_id,
        risk_category=assessment.risk_category,
        severity=assessment.severity,
        recommended_action=assessment.recommended_action,
        key_reasons=key_reasons,
        explanation=text.strip(),
        grounded=True,
        llm_used=llm_used,
    )
