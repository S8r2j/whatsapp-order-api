"""
Order service — business logic for order lifecycle management.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException, ValidationException
from app.core.logging import get_logger
from app.repositories.customer_repo import customer_repo
from app.repositories.message_repo import message_repo
from app.repositories.order_repo import order_repo
from app.repositories.social_connection_repo import social_connection_repo
from app.models.order import Order
from app.services.whatsapp_service import whatsapp_service
from app.models.social_connection import SocialConnectionPlatform
from app.utils.validators import is_valid_order_status, is_valid_status_transition

logger = get_logger(__name__)


class OrderService:
    """Manages order CRUD, status transitions, and customer notifications."""

    async def list_orders(
        self,
        db: AsyncSession,
        shop_id: uuid.UUID,
        *,
        status: Optional[str] = None,
        customer_id: Optional[uuid.UUID] = None,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        page: int = 1,
        size: int = 20,
    ) -> tuple[list[Order], int]:
        """List orders for a shop with filters and pagination.

        Args:
            db: Async session.
            shop_id: Authenticated shop's UUID (enforces isolation).
            status: Optional status filter.
            customer_id: Optional customer filter.
            from_date: Optional start date filter.
            to_date: Optional end date filter.
            page: 1-based page number.
            size: Records per page (max 100).

        Returns:
            Tuple of (list of orders, total count).
        """
        skip = (page - 1) * size
        return await order_repo.get_multi_for_shop(
            db,
            shop_id,
            status=status,
            customer_id=customer_id,
            from_date=from_date,
            to_date=to_date,
            skip=skip,
            limit=size,
        )

    async def get_order_detail(
        self, db: AsyncSession, order_id: uuid.UUID, shop_id: uuid.UUID
    ) -> Order:
        """Fetch a single order with its customer and message thread.

        Raises:
            NotFoundException: If the order doesn't exist for this shop.
        """
        order = await order_repo.get_with_relations(db, order_id, shop_id)
        if not order:
            raise NotFoundException(f"Order {order_id} not found")
        return order

    async def update_status(
        self,
        db: AsyncSession,
        order_id: uuid.UUID,
        shop_id: uuid.UUID,
        new_status: str,
    ) -> Order:
        """Update an order's status and notify the customer via WhatsApp.

        Validates the status is a legal transition before applying.

        Args:
            db: Async session.
            order_id: Target order UUID.
            shop_id: Authenticated shop's UUID.
            new_status: The requested new status.

        Returns:
            The updated Order instance.

        Raises:
            NotFoundException: Order not found for this shop.
            ValidationException: Invalid status or illegal transition.
        """
        if not is_valid_order_status(new_status):
            raise ValidationException(f"'{new_status}' is not a valid order status")

        order = await self.get_order_detail(db, order_id, shop_id)

        if not is_valid_status_transition(order.status, new_status):
            raise ValidationException(
                f"Cannot transition from '{order.status}' to '{new_status}'"
            )

        old_status = order.status
        updated = await order_repo.update(db, db_obj=order, updates={"status": new_status})

        # Notify customer asynchronously (best-effort — errors are logged, not raised)
        sent = False
        if order.customer and order.customer.phone_number:
            connection = await social_connection_repo.get_by_shop_and_platform(
                db, shop_id, SocialConnectionPlatform.WHATSAPP
            )
            if connection and connection.is_active:
                sent = await whatsapp_service.notify_status_change_for_shop(
                    order.customer.phone_number, new_status, connection
                )
            else:
                logger.warning(
                    "customer_notification_skipped",
                    order_id=str(order_id),
                    shop_id=str(shop_id),
                    reason="no_active_whatsapp_connection",
                )
        else:
            logger.warning(
                "customer_notification_skipped",
                order_id=str(order_id),
                shop_id=str(shop_id),
                reason="missing_customer_phone",
            )

        if not sent:
            logger.warning(
                "customer_notification_failed",
                order_id=str(order_id),
                new_status=new_status,
            )

        logger.info(
            "order_status_updated",
            order_id=str(order_id),
            old_status=old_status,
            new_status=new_status,
        )
        return updated

    async def update_notes(
        self,
        db: AsyncSession,
        order_id: uuid.UUID,
        shop_id: uuid.UUID,
        notes: Optional[str],
        total_amount: Optional[Decimal],
    ) -> Order:
        """Update internal notes and/or total amount for an order.

        Args:
            db: Async session.
            order_id: Target order UUID.
            shop_id: Authenticated shop's UUID.
            notes: New notes text (None to clear).
            total_amount: New total amount (None to leave unchanged).

        Returns:
            The updated Order instance.
        """
        order = await order_repo.get_with_relations(db, order_id, shop_id)
        if not order:
            raise NotFoundException(f"Order {order_id} not found")

        updates: dict = {}
        if notes is not None:
            updates["notes"] = notes
        if total_amount is not None:
            updates["total_amount"] = total_amount

        return await order_repo.update(db, db_obj=order, updates=updates)

    async def reply_to_order(
        self,
        db: AsyncSession,
        order_id: uuid.UUID,
        shop_id: uuid.UUID,
        message_text: str,
    ) -> bool:
        """Send a free-form WhatsApp message to the customer and log it.

        Args:
            db: Async session.
            order_id: The linked order UUID.
            shop_id: Authenticated shop's UUID.
            message_text: The message body to send.

        Returns:
            True if the message was sent successfully.

        Raises:
            NotFoundException: If order not found for this shop.
        """
        order = await order_repo.get_with_relations(db, order_id, shop_id)
        if not order:
            raise NotFoundException(f"Order {order_id} not found")

        if not order.customer or not order.customer.phone_number:
            raise ValidationException("Customer has no phone number to reply to")

        connection = await social_connection_repo.get_by_shop_and_platform(
            db, shop_id, SocialConnectionPlatform.WHATSAPP
        )
        if connection and connection.is_active:
            sent = await whatsapp_service.send_text_message_for_shop(
                order.customer.phone_number, message_text, connection
            )
        else:
            sent = False
            logger.warning(
                "manual_reply_skipped",
                order_id=str(order_id),
                shop_id=str(shop_id),
                reason="no_active_whatsapp_connection",
            )

        # Log the outbound message regardless of send result
        await message_repo.create(
            db,
            obj_in={
                "shop_id": shop_id,
                "customer_id": order.customer_id,
                "order_id": order_id,
                "direction": "outbound",
                "body": message_text,
                "sent_at": datetime.utcnow(),
            },
        )

        logger.info(
            "manual_reply_sent",
            order_id=str(order_id),
            sent=sent,
        )
        return sent


order_service = OrderService()
