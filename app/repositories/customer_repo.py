"""Customer repository — data access layer for the customers table."""

from __future__ import annotations

import uuid
from typing import List, Optional, Tuple

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.encryption import hash_for_lookup
from app.models.customer import Customer
from app.repositories.base import BaseRepository


class CustomerRepository(BaseRepository[Customer]):
    """Data access operations for Customer records."""

    def __init__(self) -> None:
        super().__init__(Customer)

    async def get_by_phone_for_shop(
        self, db: AsyncSession, shop_id: uuid.UUID, phone: str
    ) -> Optional[Customer]:
        """Find a customer within a shop by phone using the hash index.

        Args:
            db: Async database session.
            shop_id: The owning shop's UUID (enforces shop isolation).
            phone: Plaintext phone number.

        Returns:
            The matching Customer, or None.
        """
        phone_hash = hash_for_lookup(phone)
        result = await db.execute(
            select(Customer).where(
                Customer.shop_id == shop_id,
                Customer.phone_hash == phone_hash,
            )
        )
        return result.scalar_one_or_none()

    async def get_multi_for_shop(
        self,
        db: AsyncSession,
        shop_id: uuid.UUID,
        *,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[List[Customer], int]:
        """List all customers for a shop with pagination.

        Args:
            db: Async database session.
            shop_id: The owning shop's UUID.
            skip: Records to skip.
            limit: Max records to return.

        Returns:
            Tuple of (list of customers, total count).
        """
        base_q = (
            select(Customer)
            .where(Customer.shop_id == shop_id)
            .order_by(Customer.created_at.desc())
        )
        count_q = (
            select(func.count())
            .select_from(Customer)
            .where(Customer.shop_id == shop_id)
        )

        total = (await db.execute(count_q)).scalar_one()
        rows = (await db.execute(base_q.offset(skip).limit(limit))).scalars().all()
        return list(rows), total

    async def increment_order_count(self, db: AsyncSession, customer_id: uuid.UUID) -> None:
        """Atomically increment the total_orders counter for a customer."""
        customer = await self.get(db, customer_id)
        if customer:
            customer.total_orders = customer.total_orders + 1
            db.add(customer)
            await db.flush()


customer_repo = CustomerRepository()
