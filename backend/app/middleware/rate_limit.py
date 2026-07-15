"""Simple in-memory rate limiting for prototype deployments."""

from __future__ import annotations

import time
from collections import defaultdict
from threading import Lock

from fastapi import Request, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.config import settings
from app.observability import metrics

_LLM_PATH_SUFFIXES = ("/explanation", "/explanation/stream", "/qa", "/qa/stream")
_LOGIN_PATH = "/api/auth/login"


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app) -> None:
        super().__init__(app)
        self._lock = Lock()
        # Separate buckets per client + tier so dashboard API calls don't consume LLM quota.
        self._hits: dict[str, list[float]] = defaultdict(list)

    def _client_key(self, request: Request) -> str:
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        if request.client:
            return request.client.host
        return "unknown"

    def _is_llm_route(self, path: str) -> bool:
        return any(path.endswith(suffix) for suffix in _LLM_PATH_SUFFIXES)

    def _bucket_name(self, path: str) -> str:
        if path.endswith(_LOGIN_PATH) or path == _LOGIN_PATH:
            return "login"
        if self._is_llm_route(path):
            return "llm"
        return "general"

    def _limit_for(self, bucket: str) -> int:
        if bucket == "login":
            return settings.rate_limit_login_per_minute
        if bucket == "llm":
            return settings.effective_llm_rate_limit
        return settings.rate_limit_requests_per_minute

    def _allow(self, bucket_key: str, limit: int) -> tuple[bool, int]:
        """Return (allowed, retry_after_seconds)."""
        now = time.time()
        window_start = now - 60.0
        with self._lock:
            hits = self._hits[bucket_key]
            hits[:] = [t for t in hits if t >= window_start]
            if len(hits) >= limit:
                retry_after = max(1, int(60 - (now - hits[0])))
                return False, retry_after
            hits.append(now)
            return True, 0

    async def dispatch(self, request: Request, call_next):
        if request.method == "OPTIONS" or not settings.rate_limit_enabled:
            return await call_next(request)

        client = self._client_key(request)
        bucket = self._bucket_name(request.url.path)
        bucket_key = f"{client}:{bucket}"
        limit = self._limit_for(bucket)

        allowed, retry_after = self._allow(bucket_key, limit)
        if not allowed:
            metrics.increment("rate_limit_hits_total")
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "detail": "Rate limit exceeded. Try again shortly.",
                    "retry_after_seconds": retry_after,
                },
                headers={"Retry-After": str(retry_after)},
            )
        return await call_next(request)
