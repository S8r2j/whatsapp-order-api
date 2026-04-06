"""Periodic tasks for Meta token lifecycle management."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta

from app.core.database import get_db_session
from app.core.exceptions import ExternalServiceException
from app.core.logging import get_logger
from app.models.social_connection import SocialConnectionStatus
from app.repositories.social_connection_repo import social_connection_repo
from app.services.meta_oauth_service import meta_oauth_service
from app.tasks.celery_app import celery_app

logger = get_logger(__name__)


@celery_app.task(
    name="app.tasks.token_tasks.refresh_expiring_tokens",
    bind=True,
    max_retries=3,
    default_retry_delay=600,
)
def refresh_expiring_tokens(self) -> dict:
    """Refresh long-lived tokens that will expire within the next 7 days."""
    logger.info("refresh_tokens_task_started")

    async def _run() -> dict:
        refreshed = 0
        failed = 0

        async with get_db_session() as db:
            connections = await social_connection_repo.get_expiring_soon(db)

            for connection in connections:
                try:
                    token_data = await meta_oauth_service.refresh_token(connection.access_token)
                    expires_in = token_data.get("expires_in")
                    expires_at = (
                        datetime.utcnow() + timedelta(seconds=expires_in)
                        if expires_in
                        else None
                    )
                    await social_connection_repo.update_token(
                        db,
                        connection_id=connection.id,
                        access_token=token_data["access_token"],
                        expires_at=expires_at,
                        refresh_token=token_data.get("refresh_token"),
                    )
                    refreshed += 1
                except ExternalServiceException as exc:
                    await social_connection_repo.set_status(
                        db,
                        connection_id=connection.id,
                        status=SocialConnectionStatus.ERROR,
                        error_message=str(exc),
                    )
                    failed += 1
                    logger.error(
                        "token_refresh_failed",
                        connection_id=str(connection.id),
                        shop_id=str(connection.shop_id),
                        error=str(exc),
                    )
                except Exception as exc:
                    await social_connection_repo.set_status(
                        db,
                        connection_id=connection.id,
                        status=SocialConnectionStatus.ERROR,
                        error_message=str(exc),
                    )
                    failed += 1
                    logger.error(
                        "token_refresh_unexpected_error",
                        connection_id=str(connection.id),
                        shop_id=str(connection.shop_id),
                        error=str(exc),
                    )

        return {"refreshed": refreshed, "failed": failed}

    try:
        result = asyncio.run(_run())
        logger.info("refresh_tokens_task_completed", **result)
        return result
    except Exception as exc:
        logger.error("refresh_tokens_task_failed", error=str(exc))
        raise self.retry(exc=exc)
