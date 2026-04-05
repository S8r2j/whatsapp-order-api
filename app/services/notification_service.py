"""
Notification service — formats and dispatches scheduled notifications.

Used by Celery tasks to send daily summaries to shop owners.
"""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.repositories.order_repo import order_repo
from app.repositories.social_connection_repo import social_connection_repo
from app.models.social_connection import SocialConnectionPlatform
from app.services.whatsapp_service import whatsapp_service

logger = get_logger(__name__)


class NotificationService:
    """Formats and sends scheduled notification messages."""

    def _format_daily_summary(self, counts: dict[str, int]) -> str:
        """Build the daily summary WhatsApp message text.

        Args:
            counts: Dict mapping status -> order count for today.

        Returns:
            A formatted multi-line summary string.
        """
        total = sum(counts.values())
        delivered = counts.get("delivered", 0)
        cancelled = counts.get("cancelled", 0)
        pending = counts.get("new", 0) + counts.get("confirmed", 0) + counts.get("ready", 0)

        lines = [
            "📊 *Daily Order Summary*",
            "",
            f"Total orders today: *{total}*",
            f"✅ Delivered: {delivered}",
            f"⏳ Pending: {pending}",
            f"❌ Cancelled: {cancelled}",
        ]

        if counts.get("new", 0) > 0:
            lines.append(f"\n⚠️  {counts['new']} new order(s) still unconfirmed!")

        return "\n".join(lines)

    async def send_daily_summary(
        self, db: AsyncSession, shop_id: uuid.UUID, shop_phone: str
    ) -> None:
        """Count today's orders for a shop and send a WhatsApp summary."""
        connection = await social_connection_repo.get_by_shop_and_platform(
            db, shop_id, SocialConnectionPlatform.WHATSAPP
        )
        if not connection or not connection.is_active:
            logger.info("no_active_whatsapp_connection_skip_summary", shop_id=str(shop_id))
            return

        counts = await order_repo.count_by_status_today(db, shop_id)
        if not counts:
            logger.info("no_orders_today_skip_summary", shop_id=str(shop_id))
            return

        message = self._format_daily_summary(counts)
        sent = await whatsapp_service.send_text_message_for_shop(shop_phone, message, connection)

        if sent:
            logger.info("daily_summary_sent", shop_id=str(shop_id))
        else:
            logger.error("daily_summary_send_failed", shop_id=str(shop_id))


notification_service = NotificationService()
