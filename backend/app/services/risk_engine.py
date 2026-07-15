"""Deterministic rule-based risk scoring.

Risk category, severity, and recommended action are NEVER produced by the LLM.
"""

from __future__ import annotations

from datetime import date, datetime, timezone

from app.config import Settings, settings
from app.models.schemas import (
    BorrowerRecord,
    RecommendedAction,
    RiskAssessment,
    RiskCategory,
    RiskSignal,
    Severity,
)


def _utilization_pct(outstanding: float, credit_limit: float) -> float | None:
    if credit_limit <= 0:
        return None
    return round((outstanding / credit_limit) * 100.0, 2)


def _sum_income(
    borrower: BorrowerRecord,
    start: date,
    end: date,
    as_of: date,
    cfg: Settings,
) -> float:
    """Sum income credits within [start, end], capped by transaction_lookback_days."""
    earliest = as_of.fromordinal(as_of.toordinal() - cfg.transaction_lookback_days)
    effective_start = max(start, earliest)
    total = 0.0
    for tx in borrower.transactions:
        if (
            tx.category == "income"
            and tx.type == "credit"
            and effective_start <= tx.date <= end
        ):
            total += tx.amount
    return total


def assess_borrower(
    borrower: BorrowerRecord,
    as_of: date | None = None,
    cfg: Settings | None = None,
) -> RiskAssessment:
    cfg = cfg or settings
    as_of = as_of or date.today()
    signals: list[RiskSignal] = []
    score = 0
    indicators: dict[str, float | int | bool | str | None] = {}

    payments = sorted(borrower.payments, key=lambda p: p.due_date)
    payment_count = len(payments)
    insufficient_history = payment_count < cfg.min_payment_history_cycles
    indicators["payment_cycles"] = payment_count
    indicators["insufficient_history"] = insufficient_history
    indicators["as_of"] = as_of.isoformat()

    if insufficient_history:
        signals.append(
            RiskSignal(
                code="INSUFFICIENT_HISTORY",
                label="Insufficient payment history",
                detail=(
                    f"Only {payment_count} payment cycle(s); "
                    f"minimum for full scoring is {cfg.min_payment_history_cycles}."
                ),
                points=cfg.weight_insufficient_history,
            )
        )
        score += cfg.weight_insufficient_history

    # --- Current / recent DPD ---
    recent = payments[-cfg.payment_trend_window :] if payments else []
    current_dpd = recent[-1].days_past_due if recent else 0
    indicators["current_dpd"] = current_dpd

    if current_dpd >= cfg.current_dpd_critical:
        signals.append(
            RiskSignal(
                code="CURRENT_DPD_CRITICAL",
                label="Current days-past-due critical",
                detail=f"Latest DPD is {current_dpd} days (>= {cfg.current_dpd_critical}).",
                points=cfg.weight_current_dpd_critical,
            )
        )
        score += cfg.weight_current_dpd_critical
    elif current_dpd >= cfg.current_dpd_high:
        signals.append(
            RiskSignal(
                code="CURRENT_DPD_HIGH",
                label="Current days-past-due elevated",
                detail=f"Latest DPD is {current_dpd} days (>= {cfg.current_dpd_high}).",
                points=cfg.weight_current_dpd_high,
            )
        )
        score += cfg.weight_current_dpd_high
    elif current_dpd >= cfg.current_dpd_watch:
        signals.append(
            RiskSignal(
                code="CURRENT_DPD_WATCH",
                label="Current days-past-due watch",
                detail=f"Latest DPD is {current_dpd} day(s).",
                points=cfg.weight_current_dpd_watch,
            )
        )
        score += cfg.weight_current_dpd_watch

    # --- DPD trend (worsening across window) ---
    if len(recent) >= 2:
        dpd_values = [p.days_past_due for p in recent]
        dpd_delta = dpd_values[-1] - dpd_values[0]
        indicators["dpd_trend_delta"] = dpd_delta
        strictly_non_decreasing = all(
            dpd_values[i] <= dpd_values[i + 1] for i in range(len(dpd_values) - 1)
        )
        if dpd_delta >= cfg.dpd_increasing_min_delta and strictly_non_decreasing:
            signals.append(
                RiskSignal(
                    code="DPD_TREND_WORSENING",
                    label="Days-past-due trend worsening",
                    detail=(
                        f"DPD rose by {dpd_delta} across last {len(recent)} cycles "
                        f"({dpd_values})."
                    ),
                    points=cfg.weight_dpd_trend,
                )
            )
            score += cfg.weight_dpd_trend
    else:
        indicators["dpd_trend_delta"] = None

    # --- Failed auto-debits ---
    lookback_start = as_of.fromordinal(as_of.toordinal() - cfg.failed_autodebit_lookback_days)
    failed_count = sum(
        1
        for p in payments
        if p.auto_debit_failed and p.due_date >= lookback_start and p.due_date <= as_of
    )
    indicators["failed_autodebit_count"] = failed_count
    if failed_count >= cfg.failed_autodebit_count_high:
        signals.append(
            RiskSignal(
                code="FAILED_AUTODEBIT_HIGH",
                label="Frequent failed auto-debits",
                detail=(
                    f"{failed_count} failed auto-debit(s) in last "
                    f"{cfg.failed_autodebit_lookback_days} days."
                ),
                points=cfg.weight_failed_autodebit_high,
            )
        )
        score += cfg.weight_failed_autodebit_high
    elif failed_count >= cfg.failed_autodebit_count_watch:
        signals.append(
            RiskSignal(
                code="FAILED_AUTODEBIT_WATCH",
                label="Repeated failed auto-debits",
                detail=(
                    f"{failed_count} failed auto-debit(s) in last "
                    f"{cfg.failed_autodebit_lookback_days} days."
                ),
                points=cfg.weight_failed_autodebit_watch,
            )
        )
        score += cfg.weight_failed_autodebit_watch

    # --- Utilization (outstanding / credit_limit) ---
    util_now = _utilization_pct(borrower.loan.outstanding_balance, borrower.loan.credit_limit)
    indicators["utilization_pct"] = util_now
    if util_now is not None:
        if util_now >= cfg.utilization_high_pct:
            signals.append(
                RiskSignal(
                    code="UTILIZATION_HIGH",
                    label="High credit utilization",
                    detail=f"Utilization is {util_now}% (>= {cfg.utilization_high_pct}%).",
                    points=cfg.weight_utilization_high,
                )
            )
            score += cfg.weight_utilization_high
        elif util_now >= cfg.utilization_watch_pct:
            signals.append(
                RiskSignal(
                    code="UTILIZATION_WATCH",
                    label="Elevated credit utilization",
                    detail=f"Utilization is {util_now}% (>= {cfg.utilization_watch_pct}%).",
                    points=cfg.weight_utilization_watch,
                )
            )
            score += cfg.weight_utilization_watch

        history = sorted(borrower.balance_history, key=lambda b: b.date)
        if len(history) >= 2:
            prior_util = _utilization_pct(history[0].outstanding_balance, history[0].credit_limit)
            if prior_util is not None:
                rise = util_now - prior_util
                indicators["utilization_rise_pct_points"] = round(rise, 2)
                if rise >= cfg.utilization_rise_pct_points:
                    signals.append(
                        RiskSignal(
                            code="UTILIZATION_RISING",
                            label="Rising credit utilization",
                            detail=(
                                f"Utilization rose {rise:.1f} pts "
                                f"({prior_util}% → {util_now}%)."
                            ),
                            points=cfg.weight_utilization_rising,
                        )
                    )
                    score += cfg.weight_utilization_rising

    # --- Reduced income inflows ---
    recent_start = as_of.fromordinal(as_of.toordinal() - cfg.income_recent_days)
    baseline_end = recent_start
    baseline_start = baseline_end.fromordinal(
        baseline_end.toordinal() - cfg.income_baseline_days
    )
    recent_income = _sum_income(borrower, recent_start, as_of, as_of, cfg)
    baseline_income = _sum_income(borrower, baseline_start, baseline_end, as_of, cfg)
    # Normalize baseline to comparable monthly-ish period
    baseline_period_days = max((baseline_end - baseline_start).days, 1)
    comparable_baseline = baseline_income * (cfg.income_recent_days / baseline_period_days)
    indicators["recent_income"] = recent_income
    indicators["baseline_income_comparable"] = round(comparable_baseline, 2)
    if comparable_baseline > 0:
        decline_pct = ((comparable_baseline - recent_income) / comparable_baseline) * 100.0
        indicators["income_decline_pct"] = round(decline_pct, 2)
        if decline_pct >= cfg.income_decline_pct:
            signals.append(
                RiskSignal(
                    code="INCOME_DECLINE",
                    label="Reduced income inflows",
                    detail=(
                        f"Recent {cfg.income_recent_days}-day income is {decline_pct:.1f}% "
                        f"below comparable baseline."
                    ),
                    points=cfg.weight_income_decline,
                )
            )
            score += cfg.weight_income_decline

    # --- Declining account balance ---
    balances = sorted(borrower.balance_history, key=lambda b: b.date)[-cfg.balance_trend_window :]
    if len(balances) >= 2 and balances[0].account_balance > 0:
        bal_decline = (
            (balances[0].account_balance - balances[-1].account_balance)
            / balances[0].account_balance
        ) * 100.0
        indicators["balance_decline_pct"] = round(bal_decline, 2)
        if bal_decline >= cfg.balance_decline_pct:
            signals.append(
                RiskSignal(
                    code="BALANCE_DECLINE",
                    label="Declining account balance",
                    detail=(
                        f"Account balance fell {bal_decline:.1f}% across last "
                        f"{len(balances)} snapshots."
                    ),
                    points=cfg.weight_balance_decline,
                )
            )
            score += cfg.weight_balance_decline

    # --- Skipped / partial / missed payments ---
    status_window = recent if recent else []
    bad_statuses = {"partial", "skipped", "missed"}
    bad_count = sum(1 for p in status_window if p.status in bad_statuses)
    indicators["partial_or_skipped_count"] = bad_count
    if bad_count >= cfg.partial_payment_count_watch:
        signals.append(
            RiskSignal(
                code="PARTIAL_OR_SKIPPED",
                label="Skipped or partial payments",
                detail=(
                    f"{bad_count} skipped/partial/missed payment(s) in last "
                    f"{len(status_window)} cycle(s)."
                ),
                points=cfg.weight_partial_or_skipped,
            )
        )
        score += cfg.weight_partial_or_skipped

    # Missing payments entirely (beyond insufficient history soft flag)
    if payment_count == 0:
        signals.append(
            RiskSignal(
                code="MISSING_PAYMENT_DATA",
                label="Missing payment data",
                detail="No repayment records available for this borrower.",
                points=cfg.weight_insufficient_history,
            )
        )
        # avoid double-counting if already flagged insufficient
        if not any(s.code == "INSUFFICIENT_HISTORY" for s in signals):
            score += cfg.weight_insufficient_history
        insufficient_history = True

    category = _score_to_category(score, cfg)
    # Cap incomplete histories — avoid Critical from sparse data alone
    if insufficient_history and category in (RiskCategory.HIGH_RISK, RiskCategory.CRITICAL):
        category = RiskCategory.WATCHLIST
        signals.append(
            RiskSignal(
                code="CATEGORY_CAPPED",
                label="Category capped due to insufficient history",
                detail="High/Critical capped to Watchlist until enough payment cycles exist.",
                points=0,
            )
        )

    severity = _category_to_severity(category)
    action = _category_to_action(category, signals)

    return RiskAssessment(
        borrower_id=borrower.borrower_id,
        assessed_at=datetime.now(timezone.utc),
        risk_score=score,
        risk_category=category,
        severity=severity,
        recommended_action=action,
        signals=signals,
        insufficient_history=insufficient_history,
        indicators=indicators,
    )


def _score_to_category(score: int, cfg: Settings) -> RiskCategory:
    if score >= cfg.score_critical_min:
        return RiskCategory.CRITICAL
    if score >= cfg.score_high_min:
        return RiskCategory.HIGH_RISK
    if score >= cfg.score_watchlist_min:
        return RiskCategory.WATCHLIST
    return RiskCategory.LOW


def _category_to_severity(category: RiskCategory) -> Severity:
    return {
        RiskCategory.LOW: Severity.INFO,
        RiskCategory.WATCHLIST: Severity.MEDIUM,
        RiskCategory.HIGH_RISK: Severity.HIGH,
        RiskCategory.CRITICAL: Severity.CRITICAL,
    }[category]


def _category_to_action(
    category: RiskCategory,
    signals: list[RiskSignal],
) -> RecommendedAction:
    codes = {s.code for s in signals}
    if category == RiskCategory.LOW:
        return RecommendedAction.NO_ACTION
    if category == RiskCategory.CRITICAL:
        if "PARTIAL_OR_SKIPPED" in codes or "CURRENT_DPD_CRITICAL" in codes:
            return RecommendedAction.RESTRUCTURING_REVIEW
        return RecommendedAction.MANUAL_ANALYST_REVIEW
    if category == RiskCategory.HIGH_RISK:
        if "INCOME_DECLINE" in codes or "PARTIAL_OR_SKIPPED" in codes:
            return RecommendedAction.PAYMENT_PLAN_OFFER
        return RecommendedAction.PROACTIVE_CALL
    # Watchlist
    if "FAILED_AUTODEBIT_WATCH" in codes or "FAILED_AUTODEBIT_HIGH" in codes:
        return RecommendedAction.SOFT_REMINDER
    if "INSUFFICIENT_HISTORY" in codes or "MISSING_PAYMENT_DATA" in codes:
        return RecommendedAction.MANUAL_ANALYST_REVIEW
    return RecommendedAction.SOFT_REMINDER


def simulate_miss_next_emi(borrower: BorrowerRecord, as_of: date | None = None) -> RiskAssessment:
    """Scenario: assume next EMI is missed (adds a synthetic missed payment)."""
    from copy import deepcopy

    from app.models.schemas import PaymentRecord

    as_of = as_of or date.today()
    clone = deepcopy(borrower)
    clone.payments.append(
        PaymentRecord(
            due_date=clone.loan.next_due_date,
            due_amount=clone.loan.emi_amount,
            paid_amount=0,
            paid_date=None,
            days_past_due=max((as_of - clone.loan.next_due_date).days, 1)
            if as_of >= clone.loan.next_due_date
            else cfg_dpd_if_future_missed(),
            status="missed",
            channel="unknown",
            auto_debit_failed=True,
        )
    )
    return assess_borrower(clone, as_of=as_of)


def cfg_dpd_if_future_missed() -> int:
    # Treating a committed miss of the next EMI as at least watch-level DPD stress.
    return settings.current_dpd_high
