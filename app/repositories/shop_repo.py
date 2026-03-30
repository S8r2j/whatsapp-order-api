"""Shop repository — data access layer for the shops table."""

from __future__ import annotations

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.encryption import hash_for_lookup
from app.models.shop import Shop
from app.repositories.base import BaseRepository


class ShopRepository(BaseRepository[Shop]):
    """Data access operations for Shop records."""

    def __init__(self) -> None:
        super().__init__(Shop)

    async def get_by_email(self, db: AsyncSession, email: str) -> Optional[Shop]:
        """Find a shop by email using the hash index (O(1) lookup).

        Args:
            db: Async database session.
            email: Plaintext email address.

        Returns:
            The matching Shop, or None.
        """
        email_hash = hash_for_lookup(email)
        result = await db.execute(
            select(Shop).where(Shop.email_hash == email_hash)
        )
        return result.scalar_one_or_none()

    async def get_by_phone(self, db: AsyncSession, phone: str) -> Optional[Shop]:
        """Find a shop by phone number using the hash index.

        Args:
            db: Async database session.
            phone: Plaintext phone number.

        Returns:
            The matching Shop, or None.
        """
        phone_hash = hash_for_lookup(phone)
        result = await db.execute(
            select(Shop).where(Shop.phone_hash == phone_hash)
        )
        return result.scalar_one_or_none()

    async def email_exists(self, db: AsyncSession, email: str) -> bool:
        """Return True if a shop with this email already exists."""
        return (await self.get_by_email(db, email)) is not None

    async def phone_exists(self, db: AsyncSession, phone: str) -> bool:
        """Return True if a shop with this phone number already exists."""
        return (await self.get_by_phone(db, phone)) is not None


shop_repo = ShopRepository()
