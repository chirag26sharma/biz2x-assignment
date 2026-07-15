"""Analyst Q&A grounded strictly in one borrower's available data."""

from __future__ import annotations

import logging

from app.config import settings
from app.models.schemas import BorrowerRecord, QAResponse, RiskAssessment
from app.observability import metrics
from app.security.llm_guard import validate_llm_narration
from app.services.llm_client import llm_client

logger = logging.getLogger(__name__)


def _compact_borrower_context(borrower: BorrowerRecord, assessment: RiskAssessment) -> str:
    payments = [
        {
            "due_date": str(p.due_date),
            "due_amount": p.due_amount,
            "paid_amount": p.paid_amount,
            "dpd": p.days_past_due,
            "status": p.status,
            "auto_debit_failed": p.auto_debit_failed,
        }
        for p in sorted(borrower.payments, key=lambda x: x.due_date)[-6:]
    ]
    signals = [{"code": s.code, "label": s.label, "detail": s.detail} for s in assessment.signals]
    return (
        f"Borrower ID: {borrower.borrower_id}\n"
        f"Name: {borrower.name}\n"
        f"Loan: amount={borrower.loan.loan_amount}, emi={borrower.loan.emi_amount}, "
        f"outstanding={borrower.loan.outstanding_balance}, "
        f"credit_limit={borrower.loan.credit_limit}, next_due={borrower.loan.next_due_date}\n"
        f"Risk: score={assessment.risk_score}, category={assessment.risk_category.value}, "
        f"severity={assessment.severity.value}, action={assessment.recommended_action.value}\n"
        f"Signals: {signals}\n"
        f"Indicators: {assessment.indicators}\n"
        f"Recent payments: {payments}\n"
        f"Recent transactions: "
        f"{[{'date': str(t.date), 'amount': t.amount, 'type': t.type, 'category': t.category} for t in sorted(borrower.transactions, key=lambda x: x.date)[-8:]]}\n"
        f"Balance history: "
        f"{[{'date': str(b.date), 'account_balance': b.account_balance, 'outstanding': b.outstanding_balance} for b in sorted(borrower.balance_history, key=lambda x: x.date)]}\n"
    )


def build_qa_prompt(borrower: BorrowerRecord, assessment: RiskAssessment, question: str) -> str:
    context = _compact_borrower_context(borrower, assessment)
    return f"""You answer credit-analyst questions about ONE borrower.
Rules:
1. Use ONLY the borrower data and assessment below.
2. If the answer is not in the data, say you do not have that information.
3. Do not invent payments, balances, scores, or other borrowers.
4. Do not change risk category, severity, or recommended action.
5. Keep the answer concise and operational.
6. Format the entire answer in Markdown:
   - Use a ## heading
   - Use **bold** for key facts (category, score, DPD, amounts)
   - Use bullet lists for multiple reasons or data points
   - Do not wrap the response in code fences

BORROWER DATA:
{context}

QUESTION: {question}

ANSWER:
"""


def _fallback_answer(borrower: BorrowerRecord, assessment: RiskAssessment, question: str) -> str:
    if assessment.signals:
        bullets = "\n".join(f"- **{s.label}**" for s in assessment.signals)
        reasons = f"\n\n### Key reasons\n{bullets}"
    else:
        reasons = "\n\nNo material signals in the available data."
    return (
        f"## Analyst answer\n\n"
        f"Based only on data for **{borrower.borrower_id}**:\n\n"
        f"- **Category:** {assessment.risk_category.value}\n"
        f"- **Score:** {assessment.risk_score}\n"
        f"- **Recommended action:** {assessment.recommended_action.value}"
        f"{reasons}\n\n"
        f"> *Template fallback — LLM unavailable. Question: {question[:120]}*"
    )


async def answer_question(
    borrower: BorrowerRecord,
    assessment: RiskAssessment,
    question: str,
) -> QAResponse:
    prompt = build_qa_prompt(borrower, assessment, question)

    if not llm_client.configured:
        return QAResponse(
            borrower_id=borrower.borrower_id,
            question=question,
            answer=_fallback_answer(borrower, assessment, question),
            grounded=True,
            llm_used=False,
        )

    try:
        answer = await llm_client.query(
            prompt,
            metadata={"feature": "analyst_qa", "borrower_id": borrower.borrower_id},
        )
        metrics.increment("llm_calls_total")
        answer = validate_llm_narration(answer, assessment)
        if len(answer) > settings.llm_max_response_chars:
            answer = answer[: settings.llm_max_response_chars] + "\n\n…"
        llm_used = True
    except Exception as exc:
        logger.warning("LLM Q&A failed for %s: %s", borrower.borrower_id, exc)
        answer = _fallback_answer(borrower, assessment, question)
        llm_used = False

    return QAResponse(
        borrower_id=borrower.borrower_id,
        question=question,
        answer=answer.strip(),
        grounded=True,
        llm_used=llm_used,
    )
