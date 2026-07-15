"""Lightweight request counters for ops dashboards (Prometheus-compatible text)."""

from __future__ import annotations

from threading import Lock

_lock = Lock()
_counters: dict[str, int] = {
    "http_requests_total": 0,
    "http_errors_total": 0,
    "auth_failures_total": 0,
    "llm_calls_total": 0,
    "rate_limit_hits_total": 0,
}


def increment(name: str, amount: int = 1) -> None:
    with _lock:
        _counters[name] = _counters.get(name, 0) + amount


def snapshot() -> dict[str, int]:
    with _lock:
        return dict(_counters)


def render_prometheus() -> str:
    lines: list[str] = []
    for key, value in snapshot().items():
        lines.append(f"# TYPE {key} counter")
        lines.append(f"{key} {value}")
    return "\n".join(lines) + "\n"
