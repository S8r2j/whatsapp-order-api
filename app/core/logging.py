"""
Structured logging configuration using structlog.

In development: coloured, human-readable console output.
In production:  JSON lines for log aggregation (Datadog, CloudWatch, etc.).

Every log record automatically includes:
- timestamp
- log level
- logger name
- request_id  (bound per-request by RequestIDMiddleware)
- shop_id     (bound after authentication)

Usage::

    from app.core.logging import get_logger
    logger = get_logger(__name__)
    logger.info("order_created", order_id=str(order.id), status="new")
"""

from __future__ import annotations

import logging
import sys
from typing import Any

import structlog

from app.core.config import settings


def configure_logging() -> None:
    """Configure structlog and the stdlib logging backend.

    Call once at application startup (inside ``lifespan`` or ``main.py``).
    """
    log_level = logging.DEBUG if not settings.is_production else logging.INFO

    # Configure standard library logging so third-party libraries
    # (SQLAlchemy, httpx, etc.) also flow through structlog.
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=log_level,
    )

    shared_processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
    ]

    if settings.is_production:
        # JSON output for log aggregation
        renderer = structlog.processors.JSONRenderer()
    else:
        # Pretty coloured output for local development
        renderer = structlog.dev.ConsoleRenderer(colors=True)

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared_processors,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers = [handler]
    root_logger.setLevel(log_level)

    # Silence noisy third-party loggers in production
    if settings.is_production:
        logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
        logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Return a bound structlog logger for the given module name.

    Args:
        name: Typically ``__name__`` of the calling module.

    Returns:
        A structlog BoundLogger that includes the module name in every record.
    """
    return structlog.get_logger(name)
