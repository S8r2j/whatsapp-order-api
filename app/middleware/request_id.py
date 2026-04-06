"""
X-Request-ID middleware.

Generates a unique UUID for every request and:
- Attaches it to the structlog context (appears in every log record).
- Returns it in the X-Request-ID response header for client-side tracing.

If the client already sends an X-Request-ID header, that value is reused.
"""

from __future__ import annotations

import uuid

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Injects a per-request trace ID into structlog context and response headers."""

    async def dispatch(self, request: Request, call_next) -> Response:  # type: ignore[override]
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())

        # Bind to structlog context for this request's lifetime
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)

        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response
