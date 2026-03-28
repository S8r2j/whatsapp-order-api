"""
Async SQLAlchemy database engine and session management.

Provides:
- ``async_engine``: The application-wide async engine.
- ``AsyncSessionLocal``: Async session factory bound to the engine.
- ``get_async_db()``: FastAPI dependency that yields an ``AsyncSession`` and
  automatically commits on success or rolls back on error.

Slow query logging:
  Any query exceeding SLOW_QUERY_THRESHOLD_MS is logged at WARNING level with
  its execution time so performance regressions are caught early.
"""

from __future__ import annotations

import time
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import (
    AsyncConnection,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

SLOW_QUERY_THRESHOLD_MS = 200  # Log queries slower than this

# ── Engine ────────────────────────────────────────────────────────────────────

async_engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,          # Set True only for deep SQL debugging
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,  # Validates connections before use
    pool_recycle=3600,   # Recycle connections every hour
)


# ── Slow query instrumentation ────────────────────────────────────────────────

@event.listens_for(async_engine.sync_engine, "before_cursor_execute")
def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):  # type: ignore[no-untyped-def]
    """Attach a start timestamp to the connection for slow-query detection."""
    conn.info.setdefault("query_start_time", []).append(time.monotonic())


@event.listens_for(async_engine.sync_engine, "after_cursor_execute")
def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):  # type: ignore[no-untyped-def]
    """Log a warning if the query exceeded the slow-query threshold."""
    elapsed_ms = (time.monotonic() - conn.info["query_start_time"].pop()) * 1000
    if elapsed_ms > SLOW_QUERY_THRESHOLD_MS:
        logger.warning(
            "slow_query_detected",
            elapsed_ms=round(elapsed_ms, 2),
            statement=statement[:200],  # Truncate for log safety
        )


# ── Session factory ───────────────────────────────────────────────────────────

AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


# ── Declarative base ──────────────────────────────────────────────────────────

class Base(DeclarativeBase):
    """Shared declarative base for all SQLAlchemy models."""
    pass


# ── Dependency ────────────────────────────────────────────────────────────────

async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that provides an ``AsyncSession``.

    Commits the transaction on success; rolls back on any exception.
    Always closes the session when the request is done.

    Usage::

        @router.get("/orders")
        async def list_orders(db: AsyncSession = Depends(get_async_db)):
            ...
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# ── Context manager variant (for use outside FastAPI, e.g. Celery tasks) ──────

@asynccontextmanager
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Async context manager providing a database session for non-FastAPI contexts.

    Usage::

        async with get_db_session() as db:
            result = await db.execute(...)
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
