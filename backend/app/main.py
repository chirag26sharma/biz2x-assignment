from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse

from app.config import settings
from app.logging_config import configure_logging
from app.middleware.rate_limit import RateLimitMiddleware
from app.middleware.request_context import RequestContextMiddleware
from app.middleware.security_headers import SecurityHeadersMiddleware
from app.observability import metrics
from app.routers import auth, risk
from app.startup import validate_startup
from app.storage.factory import get_storage

import logging

configure_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    validate_startup()
    borrower_count = len(get_storage().list_borrowers())
    logger.info(
        "Started %s env=%s borrowers=%s llm=%s",
        settings.app_name,
        settings.app_env,
        borrower_count,
        "configured" if settings.llm_api_token else "fallback",
    )
    yield
    logger.info("Shutting down %s", settings.app_name)


app = FastAPI(title=settings.app_name, lifespan=lifespan)

origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins if origins else ["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-Id"],
)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(RequestContextMiddleware)

app.include_router(auth.router, prefix="/api")
app.include_router(risk.router, prefix="/api")


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    request_id = getattr(request.state, "request_id", "-")
    logger.exception("Unhandled error request_id=%s", request_id)
    metrics.increment("http_errors_total")
    detail = "Internal server error" if settings.is_production else str(exc)
    return JSONResponse(
        status_code=500,
        content={"detail": detail, "request_id": request_id},
    )


@app.get("/health")
def health():
    return {
        "status": "ok",
        "build": "1.3",
        "env": settings.app_env,
    }


@app.get("/ready")
def ready():
    try:
        count = len(get_storage().list_borrowers())
        storage_ok = count > 0
    except Exception as exc:
        logger.warning("Readiness check failed: %s", exc)
        storage_ok = False
    if not storage_ok:
        raise HTTPException(status_code=503, detail="Storage not ready")
    return {
        "status": "ready",
        "borrowers_loaded": count,
        "llm_configured": bool(settings.llm_api_token),
        "jwt_configured": bool(settings.jwt_secret) or not settings.is_production,
    }


@app.get("/metrics")
def prometheus_metrics():
    return PlainTextResponse(metrics.render_prometheus(), media_type="text/plain; version=0.0.4")
