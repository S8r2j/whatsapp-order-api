"""Order repository — data access layer for the orders table."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import List, Optional, Tuple

from sqlalchemy import func, select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.order import Order
from app.repositories.base import BaseRepository


class OrderRepository(BaseRepository[Order]):
    """Data access operations for Order records."""

    def __init__(self) -> None:
        super().__init__(Order)

    async def get_with_relations(
        self, db: AsyncSession, order_id: uuid.UUID, shop_id: uuid.UUID
    ) -> Optional[Order]:
        """Fetch a single order with customer and messages eagerly loaded.

        Args:
            db: Async database session.
            order_id: Target order UUID.
            shop_id: Must match for shop isolation enforcement.

        Returns:
            The Order with .customer and .messages populated, or None.
        """
        result = await db.execute(
            select(Order)
            .options(
                selectinload(Order.customer),
                selectinload(Order.messages),
            )
            .where(Order.id == order_id, Order.shop_id == shop_id)
        )
        return result.scalar_one_or_none()

    async def get_multi_for_shop(
        self,
        db: AsyncSession,
        shop_id: uuid.UUID,
        *,
        status: Optional[str] = None,
        customer_id: Optional[uuid.UUID] = None,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        skip: int = 0,
        limit: int = 20,
    ) -> Tuple[List[Order], int]:
        """List orders for a shop with optional filters and pagination.

        All filtering is done at the DB level — no client-side filtering.
        shop_id is always enforced to prevent cross-shop data leakage.

        Returns:
            Tuple of (list of orders with customer loaded, total count).
        """
        conditions = [Order.shop_id == shop_id]

        if status:
            conditions.append(Order.status == status)
        if customer_id:
            conditions.append(Order.customer_id == customer_id)
        if from_date:
            conditions.append(Order.created_at >= from_date)
        if to_date:
            conditions.append(Order.created_at <= to_date)

        base_q = (
            select(Order)
            .options(selectinload(Order.customer))
            .where(*conditions)
            .order_by(Order.created_at.desc())
        )
        count_q = (
            select(func.count()).select_from(Order).where(*conditions)
        )

        total = (await db.execute(count_q)).scalar_one()
        rows = (await db.execute(base_q.offset(skip).limit(limit))).scalars().all()
        return list(rows), total

    async def count_by_status_today(
        self, db: AsyncSession, shop_id: uuid.UUID
    ) -> dict:
        """Count today's orders grouped by status for the daily summary task.

        Returns:
            Dict mapping status -> count, e.g. {"new": 3, "delivered": 8, ...}
        """
        today = datetime.utcnow().date()
        result = await db.execute(
            select(Order.status, func.count(Order.id))
            .where(
                Order.shop_id == shop_id,
                func.date(Order.created_at) == today,
            )
            .group_by(Order.status)
        )
        return {row[0]: row[1] for row in result.all()}


order_repo = OrderRepository()
