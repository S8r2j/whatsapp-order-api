"""
Celery tasks for scheduled order operations.

Tasks:
- send_daily_summaries: Sends an order summary to every active shop at 8PM.
- cleanup_old_messages: Deletes message records older than 90 days.

All tasks use asyncio.run() to run async service code inside the synchronous
Celery worker process.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta

from sqlalchemy import delete, select

from app.core.logging import get_logger
from app.core.database import get_db_session
from app.models.message import Message
from app.models.shop import Shop
from app.services.notification_service import notification_service
from app.tasks.celery_app import celery_app

logger = get_logger(__name__)


@celery_app.task(
    name="app.tasks.order_tasks.send_daily_summaries",
    bind=True,
    max_retries=3,
    default_retry_delay=300,  # Retry after 5 minutes on failure
)
def send_daily_summaries(self) -> dict:  # type: ignore[override]
    """Send the daily order summary WhatsApp message to all active shop owners.

    Fetches every active shop with a phone number, counts today's orders
    by status, formats a summary, and sends it via WhatsApp.

    Returns:
        Dict with ``shops_processed`` and ``shops_notified`` counts.
    """
    logger.info("daily_summary_task_started")

    async def _run() -> dict:
        processed = 0
        notified = 0

        async with get_db_session() as db:
            # Fetch all active shops that have a WhatsApp number
            result = await db.execute(
                select(Shop).where(
                    Shop.is_active.is_(True),
                    Shop.phone_number.isnot(None),
                )
            )
            shops = result.scalars().all()

            for shop in shops:
                processed += 1
                try:
                    await notification_service.send_daily_summary(
                        db, shop.id, shop.phone_number  # type: ignore[arg-type]
                    )
                    notified += 1
                except Exception as exc:
                    logger.error(
                        "daily_summary_shop_failed",
                        shop_id=str(shop.id),
                        error=str(exc),
                    )

        return {"shops_processed": processed, "shops_notified": notified}

    try:
        result = asyncio.run(_run())
        logger.info("daily_summary_task_completed", **result)
        return result
    except Exception as exc:
        logger.error("daily_summary_task_failed", error=str(exc))
        raise self.retry(exc=exc)


@celery_app.task(
    name="app.tasks.order_tasks.cleanup_old_messages",
    bind=True,
    max_retries=2,
)
def cleanup_old_messages(self) -> dict:  # type: ignore[override]
    """Delete message records older than 90 days to control database growth.

    Returns:
        Dict with ``deleted_count``.
    """
    logger.info("message_cleanup_task_started")

    async def _run() -> int:
        cutoff = datetime.utcnow() - timedelta(days=90)
        async with get_db_session() as db:
            result = await db.execute(
                delete(Message).where(Message.created_at < cutoff)
            )
            return result.rowcount  # type: ignore[return-value]

    try:
        deleted = asyncio.run(_run())
        logger.info("message_cleanup_task_completed", deleted_count=deleted)
        return {"deleted_count": deleted}
    except Exception as exc:
        logger.error("message_cleanup_task_failed", error=str(exc))
        raise self.retry(exc=exc)
