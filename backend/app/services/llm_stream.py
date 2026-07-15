"""SSE streaming helpers — wrapper API returns full text; we chunk for progressive UX."""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from typing import Any

from app.models.schemas import BorrowerRecord, RiskAssessment
from app.services.explanation import _fallback_explanation, build_explanation_prompt
from app.services.llm_client import llm_client
from app.services.qa import _fallback_answer, build_qa_prompt

CHUNK_DELAY_SECONDS = 0.018
WORDS_PER_CHUNK = 2


def _sse(event: str, payload: dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"


async def _emit_text_chunks(text: str) -> AsyncIterator[str]:
    words = text.split()
    if not words:
        return
    for i in range(0, len(words), WORDS_PER_CHUNK):
        chunk = " ".join(words[i : i + WORDS_PER_CHUNK])
        suffix = "" if i + WORDS_PER_CHUNK >= len(words) else " "
        yield _sse("chunk", {"text": chunk + suffix})
        await asyncio.sleep(CHUNK_DELAY_SECONDS)


async def stream_explanation_events(
    borrower: BorrowerRecord,
    assessment: RiskAssessment,
) -> AsyncIterator[str]:
    key_reasons = [s.label for s in assessment.signals]
    yield _sse(
        "meta",
        {
            "borrower_id": borrower.borrower_id,
            "risk_category": assessment.risk_category.value,
            "severity": assessment.severity.value,
            "recommended_action": assessment.recommended_action.value,
            "key_reasons": key_reasons,
        },
    )
    yield _sse("status", {"phase": "started", "message": "Generating explanation…"})

    prompt = build_explanation_prompt(borrower, assessment)
    llm_used = False
    text = ""

    if not llm_client.configured:
        text = _fallback_explanation(borrower, assessment)
        yield _sse("status", {"phase": "fallback", "message": "Using template fallback"})
    else:
        yield _sse("status", {"phase": "generating", "message": "Answering…"})
        try:
            text = (await llm_client.query(
                prompt,
                metadata={"feature": "risk_explanation_stream", "borrower_id": borrower.borrower_id},
            )).strip()
            llm_used = True
        except Exception as exc:
            text = _fallback_explanation(borrower, assessment)
            yield _sse("status", {"phase": "fallback", "message": f"LLM unavailable: {exc}"})

    yield _sse("status", {"phase": "streaming", "message": "Streaming response…"})
    async for event in _emit_text_chunks(text):
        yield event

    yield _sse("done", {"llm_used": llm_used, "full_text": text, "grounded": True})


async def stream_qa_events(
    borrower: BorrowerRecord,
    assessment: RiskAssessment,
    question: str,
) -> AsyncIterator[str]:
    yield _sse(
        "meta",
        {
            "borrower_id": borrower.borrower_id,
            "question": question,
            "risk_category": assessment.risk_category.value,
            "risk_score": assessment.risk_score,
        },
    )
    yield _sse("status", {"phase": "started", "message": "Processing question…"})

    prompt = build_qa_prompt(borrower, assessment, question)
    llm_used = False
    text = ""

    if not llm_client.configured:
        text = _fallback_answer(borrower, assessment, question)
        yield _sse("status", {"phase": "fallback", "message": "Using template fallback"})
    else:
        yield _sse("status", {"phase": "generating", "message": "Answering…"})
        try:
            text = (await llm_client.query(
                prompt,
                metadata={"feature": "analyst_qa_stream", "borrower_id": borrower.borrower_id},
            )).strip()
            llm_used = True
        except Exception as exc:
            text = _fallback_answer(borrower, assessment, question)
            yield _sse("status", {"phase": "fallback", "message": f"LLM unavailable: {exc}"})

    yield _sse("status", {"phase": "streaming", "message": "Streaming answer…"})
    async for event in _emit_text_chunks(text):
        yield event

    yield _sse("done", {"llm_used": llm_used, "full_text": text, "grounded": True})
