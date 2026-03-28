"""
Global error handling middleware and exception handlers.

Converts all exceptions into the standard API error response format:
{
    "error": {
        "code": "...",
        "message": "...",
        "details": ...,
        "request_id": "...",
        "timestamp": "..."
    }
}
"""

from __future__ import annotations

from datetime import datetime

import structlog
from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.exceptions import AppException
from app.core.logging import get_logger

logger = get_logger(__name__)


def _error_response(
    status_code: int,
    code: str,
    message: str,
    request_id: str | None = None,
    details: object = None,
) -> JSONResponse:
    """Construct a standard JSONResponse for error cases."""
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": code,
                "message": message,
                "details": details,
                "request_id": request_id or structlog.contextvars.get_contextvars().get("request_id"),
                "timestamp": datetime.utcnow().isoformat() + "Z",
            }
        },
    )


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """Handle all custom AppException subclasses."""
    logger.warning(
        "app_exception",
        code=exc.code,
        message=exc.message,
        status_code=exc.status_code,
    )
    return _error_response(exc.status_code, exc.code, exc.message, details=exc.details)


async def http_exception_handler(
    request: Request, exc: StarletteHTTPException
) -> JSONResponse:
    """Handle standard FastAPI/Starlette HTTP exceptions."""
    logger.warning("http_exception", status_code=exc.status_code, detail=exc.detail)
    return _error_response(exc.status_code, "HTTP_ERROR", str(exc.detail))


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Handle Pydantic request validation errors (422)."""
    logger.info("validation_error", error_count=len(exc.errors()))
    return _error_response(
        422,
        "VALIDATION_ERROR",
        "Request validation failed",
        details=exc.errors(),
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all for any unhandled exception — returns 500 without leaking internals."""
    logger.exception("unhandled_exception", exc_type=type(exc).__name__, error=str(exc))
    return _error_response(500, "INTERNAL_ERROR", "An unexpected error occurred")
