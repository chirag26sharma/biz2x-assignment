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

    def _allow(self, key: str, limit: int) -> bool:
        now = time.time()
        window_start = now - 60.0
        with self._lock:
            bucket = self._hits[key]
            self._hits[key] = [t for t in bucket if t >= window_start]
            if len(self._hits[key]) >= limit:
                return False
            self._hits[key].append(now)
            return True

    def _limit_for(self, path: str) -> int:
        if path.endswith(_LOGIN_PATH) or path == _LOGIN_PATH:
            return settings.rate_limit_login_per_minute
        if self._is_llm_route(path):
            return settings.rate_limit_llm_requests_per_minute
        return settings.rate_limit_requests_per_minute

    async def dispatch(self, request: Request, call_next):
        if request.method == "OPTIONS" or not settings.rate_limit_enabled:
            return await call_next(request)

        key = self._client_key(request)
        limit = self._limit_for(request.url.path)
        if not self._allow(key, limit):
            metrics.increment("rate_limit_hits_total")
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={"detail": "Rate limit exceeded. Try again shortly."},
            )
        return await call_next(request)
