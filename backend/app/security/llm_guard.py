"""Post-LLM checks to ensure narration does not override deterministic risk outputs."""

from __future__ import annotations

import re

from app.models.schemas import RiskAssessment

_CATEGORY_OVERRIDE = re.compile(
    r"(risk\s+)?category\s+.*\b(low|watchlist|high\s*risk|critical)\b",
    re.I,
)
_SCORE_OVERRIDE = re.compile(
    r"(risk\s+)?score\s+(is|should\s+be|changed\s+to)\s+\d{1,3}",
    re.I,
)
_ACTION_OVERRIDE = re.compile(
    r"recommended\s+action\s+(is|should\s+be|changed\s+to)",
    re.I,
)


def validate_llm_narration(text: str, assessment: RiskAssessment) -> str:
    """Return safe narration; append guardrail notice if model tried to override scoring."""
    stripped = text.strip()
    if not stripped:
        return stripped

    violations: list[str] = []
    if _CATEGORY_OVERRIDE.search(stripped):
        violations.append("category")
    if _SCORE_OVERRIDE.search(stripped):
        violations.append("score")
    if _ACTION_OVERRIDE.search(stripped):
        violations.append("action")

    if not violations:
        return stripped

    guard = (
        "\n\n---\n"
        f"*System note: Risk category ({assessment.risk_category.value}), "
        f"score ({assessment.risk_score}), and recommended action "
        f"({assessment.recommended_action.value}) are fixed by the rule engine "
        f"and were not altered by this narration.*"
    )
    return stripped + guard
