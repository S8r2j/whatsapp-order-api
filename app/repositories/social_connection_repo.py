"""Data access layer for social connections."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.social_connection import (
    SocialConnection,
    SocialConnectionPlatform,
    SocialConnectionStatus,
)
from app.repositories.base import BaseRepository


class SocialConnectionRepository(BaseRepository[SocialConnection]):
    """Repository for social connection records."""

    def __init__(self) -> None:
        super().__init__(SocialConnection)

    async def get_by_shop_and_platform(
        self, db: AsyncSession, shop_id: uuid.UUID, platform: SocialConnectionPlatform
    ) -> Optional[SocialConnection]:
        result = await db.execute(
            select(self.model).where(
                self.model.shop_id == shop_id,
                self.model.platform == platform,
            )
        )
        return result.scalar_one_or_none()

    async def get_by_phone_number_id(
        self, db: AsyncSession, phone_number_id: str
    ) -> Optional[SocialConnection]:
        result = await db.execute(
            select(self.model).where(self.model.phone_number_id == phone_number_id)
        )
        return result.scalar_one_or_none()

    async def get_active_for_shop(
        self, db: AsyncSession, shop_id: uuid.UUID
    ) -> List[SocialConnection]:
        result = await db.execute(
            select(self.model).where(
                self.model.shop_id == shop_id,
                self.model.is_active.is_(True),
            )
        )
        return result.scalars().all()

    async def get_expiring_soon(
        self, db: AsyncSession, within_days: int = 7
    ) -> List[SocialConnection]:
        threshold = datetime.utcnow() + timedelta(days=within_days)
        result = await db.execute(
            select(self.model).where(
                self.model.token_expires_at.isnot(None),
                self.model.token_expires_at <= threshold,
                self.model.is_active.is_(True),
            )
        )
        return result.scalars().all()

    async def update_token(
        self,
        db: AsyncSession,
        connection_id: uuid.UUID,
        access_token: str,
        expires_at: datetime | None,
        *,
        refresh_token: str | None = None,
    ) -> SocialConnection:
        connection = await self.get(db, connection_id)
        if connection is None:
            raise ValueError(f"Connection {connection_id} not found")
        updates = {
            "access_token": access_token,
            "token_expires_at": expires_at,
            "status": SocialConnectionStatus.CONNECTED,
            "error_message": None,
            "last_sync_at": datetime.utcnow(),
        }
        if refresh_token is not None:
            updates["refresh_token"] = refresh_token
        return await self.update(db, db_obj=connection, updates=updates)

    async def set_status(
        self,
        db: AsyncSession,
        connection_id: uuid.UUID,
        status: SocialConnectionStatus,
        error_message: str | None = None,
    ) -> SocialConnection:
        connection = await self.get(db, connection_id)
        if connection is None:
            raise ValueError(f"Connection {connection_id} not found")
        return await self.update(
            db,
            db_obj=connection,
            updates={
                "status": status,
                "error_message": error_message,
                "last_sync_at": datetime.utcnow(),
            },
        )


social_connection_repo = SocialConnectionRepository()
