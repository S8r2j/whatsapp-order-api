"""
Customer service — business logic for customer management.
"""

from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException
from app.core.logging import get_logger
from app.models.customer import Customer
from app.repositories.customer_repo import customer_repo
from app.repositories.order_repo import order_repo

logger = get_logger(__name__)


class CustomerService:
    """Manages customer lookup and profile updates."""

    async def list_customers(
        self,
        db: AsyncSession,
        shop_id: uuid.UUID,
        *,
        page: int = 1,
        size: int = 50,
    ) -> tuple[list[Customer], int]:
        """List all customers for a shop, paginated.

        Args:
            db: Async session.
            shop_id: Authenticated shop's UUID.
            page: 1-based page number.
            size: Records per page.

        Returns:
            Tuple of (list of customers, total count).
        """
        skip = (page - 1) * size
        return await customer_repo.get_multi_for_shop(db, shop_id, skip=skip, limit=size)

    async def get_customer(
        self, db: AsyncSession, customer_id: uuid.UUID, shop_id: uuid.UUID
    ) -> Customer:
        """Fetch a single customer, ensuring shop isolation.

        Args:
            db: Async session.
            customer_id: Target customer UUID.
            shop_id: Authenticated shop's UUID.

        Returns:
            The Customer instance.

        Raises:
            NotFoundException: If customer not found or belongs to a different shop.
        """
        customer = await customer_repo.get(db, customer_id)
        if not customer or customer.shop_id != shop_id:
            raise NotFoundException(f"Customer {customer_id} not found")
        return customer

    async def update_customer(
        self,
        db: AsyncSession,
        customer_id: uuid.UUID,
        shop_id: uuid.UUID,
        name: Optional[str],
    ) -> Customer:
        """Update a customer's display name.

        Args:
            db: Async session.
            customer_id: Target customer UUID.
            shop_id: Authenticated shop's UUID.
            name: New display name.

        Returns:
            The updated Customer instance.
        """
        customer = await self.get_customer(db, customer_id, shop_id)
        updated = await customer_repo.update(db, db_obj=customer, updates={"name": name})
        logger.info("customer_updated", customer_id=str(customer_id))
        return updated

    async def get_customer_orders(
        self,
        db: AsyncSession,
        customer_id: uuid.UUID,
        shop_id: uuid.UUID,
        *,
        page: int = 1,
        size: int = 20,
    ) -> tuple[list, int]:
        """Fetch recent orders for a specific customer.

        Args:
            db: Async session.
            customer_id: Target customer UUID.
            shop_id: Authenticated shop's UUID.
            page: Page number.
            size: Page size.

        Returns:
            Tuple of (list of orders, total count).
        """
        # Verify customer belongs to this shop first
        await self.get_customer(db, customer_id, shop_id)

        skip = (page - 1) * size
        return await order_repo.get_multi_for_shop(
            db, shop_id, customer_id=customer_id, skip=skip, limit=size
        )


customer_service = CustomerService()
