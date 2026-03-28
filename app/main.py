"""
FastAPI application entry point.

Application lifecycle:
    1. Configure structlog on startup.
    2. Mount all middleware (CORS, RequestID, rate limiter).
    3. Register all exception handlers.
    4. Include API v1 router.
    5. Optionally initialise Sentry if SENTRY_DSN is set.

Run in development:
    uvicorn app.main:app --reload --port 8000

Run in production (via Docker):
    uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator

import sentry_sdk
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.v1.api import api_router
from app.api.pages.privacy_policy import router as pages_router
from app.core.config import settings
from app.core.exceptions import AppException
from app.core.logging import configure_logging, get_logger
from app.middleware.error_handler import (
    app_exception_handler,
    http_exception_handler,
    unhandled_exception_handler,
    validation_exception_handler,
)
from app.middleware.request_id import RequestIDMiddleware

logger = get_logger(__name__)


# ── Sentry (optional) ─────────────────────────────────────────────────────────

_sentry_dsn = settings.SENTRY_DSN.strip().strip('"\'')
if _sentry_dsn:
    sentry_sdk.init(
        dsn=_sentry_dsn,
        environment=settings.ENVIRONMENT,
        traces_sample_rate=0.2,
    )


# ── Rate limiter ──────────────────────────────────────────────────────────────

limiter = Limiter(key_func=get_remote_address, default_limits=["200/minute"])


# ── Application lifespan ──────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Run startup and shutdown tasks."""
    configure_logging()
    logger.info(
        "application_starting",
        environment=settings.ENVIRONMENT,
        app_name=settings.APP_NAME,
    )
    yield
    logger.info("application_shutting_down")


# ── FastAPI app ───────────────────────────────────────────────────────────────

app = FastAPI(
    title=settings.APP_NAME,
    description=(
        "REST API for WhatsApp Order Management. "
        "Receives orders via WhatsApp webhook, surfaces them in a dashboard, "
        "and sends status updates back to customers."
    ),
    version="0.1.0",
    docs_url="/docs" if not settings.is_production else None,
    redoc_url="/redoc" if not settings.is_production else None,
    lifespan=lifespan,
)

# ── Middleware (order matters — outermost registered first) ───────────────────

# 1. Request ID — must be first so every downstream middleware has a request_id
app.add_middleware(RequestIDMiddleware)

# 2. CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Rate limiter ──────────────────────────────────────────────────────────────

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]

# ── Exception handlers ────────────────────────────────────────────────────────

app.add_exception_handler(AppException, app_exception_handler)  # type: ignore[arg-type]
app.add_exception_handler(StarletteHTTPException, http_exception_handler)  # type: ignore[arg-type]
app.add_exception_handler(RequestValidationError, validation_exception_handler)  # type: ignore[arg-type]
app.add_exception_handler(Exception, unhandled_exception_handler)

# ── Routes ────────────────────────────────────────────────────────────────────

app.include_router(api_router)
app.include_router(pages_router)


@app.get("/", tags=["Health"], summary="Root")
async def root() -> dict:
    return {"status": "ok", "app": settings.APP_NAME}


@app.get("/health", tags=["Health"], summary="Liveness check")
async def health_check() -> dict:
    """Simple liveness endpoint for load balancer health checks."""
    return {"status": "ok", "environment": settings.ENVIRONMENT, "version": "0.1.0"}
