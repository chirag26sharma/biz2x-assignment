from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query
from fastapi.responses import StreamingResponse

from app.auth.audit import audit_event
from app.auth.dependencies import (
    assert_can_view_borrower,
    get_current_user,
    require_analyst_or_manager,
)
from app.config import settings
from app.models.schemas import (
    AlertSummary,
    AuthUser,
    BorrowerRecord,
    ExplanationResponse,
    PortfolioSummary,
    QARequest,
    QAResponse,
    RiskAssessment,
    ScenarioRequest,
    UserRole,
)
from app.services.explanation import build_borrower_update_response, generate_explanation
from app.services.llm_stream import stream_explanation_events, stream_qa_events
from app.services.qa import answer_question
from app.services.risk_engine import assess_borrower, simulate_miss_next_emi
from app.storage.factory import get_storage

router = APIRouter(tags=["risk"])

BorrowerId = Annotated[str, Path(pattern=r"^[A-Z][A-Z0-9_]{2,31}$")]


def _visible_borrowers(user: AuthUser) -> list[BorrowerRecord]:
    store = get_storage()
    if user.role == UserRole.MANAGER:
        return store.list_borrowers()
    if user.role == UserRole.ANALYST:
        return store.list_borrowers_for_analyst(user.user_id)
    if user.role == UserRole.BORROWER and user.borrower_id:
        b = store.get_borrower(user.borrower_id)
        return [b] if b else []
    return []


def _to_alert(borrower: BorrowerRecord, assessment: RiskAssessment) -> AlertSummary:
    return AlertSummary(
        borrower_id=borrower.borrower_id,
        borrower_name=borrower.name,
        risk_category=assessment.risk_category,
        severity=assessment.severity,
        recommended_action=assessment.recommended_action,
        risk_score=assessment.risk_score,
        key_reasons=[s.label for s in assessment.signals],
        next_due_date=borrower.loan.next_due_date,
        outstanding_balance=borrower.loan.outstanding_balance,
        insufficient_history=assessment.insufficient_history,
        assigned_analyst_id=borrower.assigned_analyst_id,
    )


@router.get("/alerts", response_model=list[AlertSummary])
def list_alerts(
    user: AuthUser = Depends(get_current_user),
    as_of: date | None = Query(default=None),
) -> list[AlertSummary]:
    as_of = as_of or date.fromisoformat("2026-07-15")
    alerts = [
        _to_alert(b, assess_borrower(b, as_of=as_of))
        for b in _visible_borrowers(user)
    ]
    order = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3, "Info": 4}
    alerts.sort(key=lambda a: (order.get(a.severity.value, 9), -a.risk_score))
    return alerts


@router.get("/borrowers/{borrower_id}/assessment", response_model=RiskAssessment)
def get_assessment(
    borrower_id: BorrowerId,
    user: AuthUser = Depends(get_current_user),
    as_of: date | None = Query(default=None),
) -> RiskAssessment:
    assert_can_view_borrower(user, borrower_id)
    borrower = get_storage().get_borrower(borrower_id)
    assert borrower is not None
    audit_event(action="VIEW_ASSESSMENT", user=user, borrower_id=borrower_id)
    return assess_borrower(borrower, as_of=as_of or date.fromisoformat("2026-07-15"))


@router.get("/borrowers/{borrower_id}/profile")
def get_borrower_profile(
    borrower_id: BorrowerId,
    user: AuthUser = Depends(get_current_user),
) -> dict:
    assert_can_view_borrower(user, borrower_id)
    borrower = get_storage().get_borrower(borrower_id)
    assert borrower is not None
    audit_event(action="VIEW_PROFILE", user=user, borrower_id=borrower_id)
    # Borrowers see a reduced explanation-oriented view (no analyst assignment internals)
    data = borrower.model_dump(mode="json")
    if user.role == UserRole.BORROWER:
        data.pop("assigned_analyst_id", None)
        data.pop("notes", None)
        data.pop("scenario_tag", None)
    return data


@router.get("/borrowers/{borrower_id}/borrower-update", response_model=ExplanationResponse)
def get_borrower_update(
    borrower_id: BorrowerId,
    user: AuthUser = Depends(get_current_user),
    as_of: date | None = Query(default=None),
) -> ExplanationResponse:
    """Deterministic plain-language update for borrowers — no LLM."""
    assert_can_view_borrower(user, borrower_id)
    borrower = get_storage().get_borrower(borrower_id)
    assert borrower is not None
    assessment = assess_borrower(borrower, as_of=as_of or date.fromisoformat("2026-07-15"))
    audit_event(action="BORROWER_UPDATE", user=user, borrower_id=borrower_id)
    return build_borrower_update_response(borrower, assessment)


@router.get("/borrowers/{borrower_id}/explanation", response_model=ExplanationResponse)
async def get_explanation(
    borrower_id: BorrowerId,
    user: AuthUser = Depends(require_analyst_or_manager),
    as_of: date | None = Query(default=None),
) -> ExplanationResponse:
    assert_can_view_borrower(user, borrower_id)
    borrower = get_storage().get_borrower(borrower_id)
    assert borrower is not None
    assessment = assess_borrower(borrower, as_of=as_of or date.fromisoformat("2026-07-15"))
    audit_event(action="LLM_EXPLANATION", user=user, borrower_id=borrower_id)
    return await generate_explanation(borrower, assessment)


@router.get("/borrowers/{borrower_id}/explanation/stream")
async def stream_explanation(
    borrower_id: BorrowerId,
    user: AuthUser = Depends(require_analyst_or_manager),
    as_of: date | None = Query(default=None),
) -> StreamingResponse:
    assert_can_view_borrower(user, borrower_id)
    borrower = get_storage().get_borrower(borrower_id)
    assert borrower is not None
    assessment = assess_borrower(borrower, as_of=as_of or date.fromisoformat("2026-07-15"))
    audit_event(action="LLM_EXPLANATION_STREAM", user=user, borrower_id=borrower_id)

    async def event_generator():
        async for event in stream_explanation_events(borrower, assessment):
            yield event

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/borrowers/{borrower_id}/qa", response_model=QAResponse)
async def ask_question(
    borrower_id: BorrowerId,
    body: QARequest,
    user: AuthUser = Depends(require_analyst_or_manager),
    as_of: date | None = Query(default=None),
) -> QAResponse:
    assert_can_view_borrower(user, borrower_id)
    borrower = get_storage().get_borrower(borrower_id)
    assert borrower is not None
    assessment = assess_borrower(borrower, as_of=as_of or date.fromisoformat("2026-07-15"))
    audit_event(action="ANALYST_QA", user=user, borrower_id=borrower_id)
    return await answer_question(borrower, assessment, body.question)


@router.post("/borrowers/{borrower_id}/qa/stream")
async def stream_question(
    borrower_id: BorrowerId,
    body: QARequest,
    user: AuthUser = Depends(require_analyst_or_manager),
    as_of: date | None = Query(default=None),
) -> StreamingResponse:
    assert_can_view_borrower(user, borrower_id)
    borrower = get_storage().get_borrower(borrower_id)
    assert borrower is not None
    assessment = assess_borrower(borrower, as_of=as_of or date.fromisoformat("2026-07-15"))
    audit_event(action="ANALYST_QA_STREAM", user=user, borrower_id=borrower_id)

    async def event_generator():
        async for event in stream_qa_events(borrower, assessment, body.question):
            yield event

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/borrowers/{borrower_id}/scenario", response_model=RiskAssessment)
def run_scenario(
    borrower_id: BorrowerId,
    body: ScenarioRequest,
    user: AuthUser = Depends(require_analyst_or_manager),
    as_of: date | None = Query(default=None),
) -> RiskAssessment:
    assert_can_view_borrower(user, borrower_id)
    borrower = get_storage().get_borrower(borrower_id)
    assert borrower is not None
    audit_event(action="SCENARIO_SIMULATION", user=user, borrower_id=borrower_id)
    as_of_date = as_of or date.fromisoformat("2026-07-15")
    if body.miss_next_emi:
        return simulate_miss_next_emi(borrower, as_of=as_of_date)
    return assess_borrower(borrower, as_of=as_of_date)


@router.get("/portfolio/summary", response_model=PortfolioSummary)
def portfolio_summary(
    user: AuthUser = Depends(get_current_user),
    as_of: date | None = Query(default=None),
) -> PortfolioSummary:
    as_of = as_of or date.fromisoformat("2026-07-15")
    borrowers = _visible_borrowers(user)
    by_category: dict[str, int] = {}
    by_severity: dict[str, int] = {}
    at_risk = 0.0
    critical = 0
    high = 0
    for b in borrowers:
        a = assess_borrower(b, as_of=as_of)
        by_category[a.risk_category.value] = by_category.get(a.risk_category.value, 0) + 1
        by_severity[a.severity.value] = by_severity.get(a.severity.value, 0) + 1
        if a.risk_category.value in ("High Risk", "Critical", "Watchlist"):
            at_risk += b.loan.outstanding_balance
        if a.risk_category.value == "Critical":
            critical += 1
        if a.risk_category.value == "High Risk":
            high += 1
    return PortfolioSummary(
        total_borrowers=len(borrowers),
        by_category=by_category,
        by_severity=by_severity,
        total_outstanding_at_risk=at_risk,
        critical_count=critical,
        high_risk_count=high,
    )


@router.get("/config/public")
def public_config() -> dict:
    return {
        "delinquency_horizon_days": settings.delinquency_horizon_days,
        "min_payment_history_cycles": settings.min_payment_history_cycles,
        "payment_trend_window": settings.payment_trend_window,
        "score_bands": {
            "watchlist_min": settings.score_watchlist_min,
            "high_min": settings.score_high_min,
            "critical_min": settings.score_critical_min,
        },
        "as_of_default": "2026-07-15",
        "llm_configured": bool(settings.llm_api_token),
        "api_version": "1.3",
    }
