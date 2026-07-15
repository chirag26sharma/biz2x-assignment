"""Request correlation ID and client IP for logs and audit."""

from __future__ import annotations

import logging
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.auth.audit import client_ip_var, request_id_var
from app.observability import metrics

logger = logging.getLogger("access")


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = request.headers.get("X-Request-Id") or str(uuid.uuid4())
        client_ip = request.client.host if request.client else "unknown"
        token_rid = request_id_var.set(request_id)
        token_ip = client_ip_var.set(client_ip)
        request.state.request_id = request_id

        started = time.perf_counter()
        metrics.increment("http_requests_total")
        try:
            response = await call_next(request)
        except Exception:
            metrics.increment("http_errors_total")
            raise
        finally:
            request_id_var.reset(token_rid)
            client_ip_var.reset(token_ip)

        elapsed_ms = (time.perf_counter() - started) * 1000
        if request.url.path not in ("/health", "/ready", "/metrics"):
            logger.info(
                "%s %s %s %.1fms",
                request.method,
                request.url.path,
                response.status_code,
                elapsed_ms,
                extra={"request_id": request_id},
            )

        response.headers["X-Request-Id"] = request_id
        if response.status_code >= 500:
            metrics.increment("http_errors_total")
        return response
