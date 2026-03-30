"""Message repository — data access layer for the messages table."""

from __future__ import annotations

import uuid
from typing import List, Optional

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.message import Message
from app.repositories.base import BaseRepository


class MessageRepository(BaseRepository[Message]):
    """Data access operations for Message records."""

    def __init__(self) -> None:
        super().__init__(Message)

    async def get_by_wa_message_id(
        self, db: AsyncSession, wa_message_id: str
    ) -> Optional[Message]:
        result = await db.execute(
            select(Message).where(Message.wa_message_id == wa_message_id)
        )
        return result.scalar_one_or_none()

    async def wa_message_exists(self, db: AsyncSession, wa_message_id: str) -> bool:
        """Return True if a message with this WhatsApp ID has already been stored."""
        return (await self.get_by_wa_message_id(db, wa_message_id)) is not None

    async def get_for_conversation(
        self,
        db: AsyncSession,
        shop_id: uuid.UUID,
        customer_id: uuid.UUID,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Message]:
        """Return all messages in a conversation ordered oldest → newest."""
        result = await db.execute(
            select(Message)
            .where(
                Message.shop_id == shop_id,
                Message.customer_id == customer_id,
            )
            .order_by(Message.sent_at.asc(), Message.created_at.asc())
            .offset(offset)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_latest_per_customer(
        self,
        db: AsyncSession,
        shop_id: uuid.UUID,
    ) -> List[Message]:
        """Return the most recent message per customer — used for the conversation list."""
        subq = (
            select(
                Message.customer_id,
                func.max(Message.created_at).label("max_ts"),
            )
            .where(Message.shop_id == shop_id)
            .group_by(Message.customer_id)
            .subquery()
        )
        result = await db.execute(
            select(Message)
            .join(
                subq,
                (Message.customer_id == subq.c.customer_id)
                & (Message.created_at == subq.c.max_ts),
            )
            .where(Message.shop_id == shop_id)
            .order_by(desc(subq.c.max_ts))
        )
        return list(result.scalars().all())

    async def count_unread(
        self,
        db: AsyncSession,
        shop_id: uuid.UUID,
        customer_id: uuid.UUID,
    ) -> int:
        """Count inbound messages that arrived after the last outbound message."""
        # Find the timestamp of the last outbound message
        last_outbound_result = await db.execute(
            select(func.max(Message.created_at))
            .where(
                Message.shop_id == shop_id,
                Message.customer_id == customer_id,
                Message.direction == "outbound",
            )
        )
        last_outbound_ts = last_outbound_result.scalar_one_or_none()

        query = select(func.count()).where(
            Message.shop_id == shop_id,
            Message.customer_id == customer_id,
            Message.direction == "inbound",
        )
        if last_outbound_ts:
            query = query.where(Message.created_at > last_outbound_ts)

        result = await db.execute(query)
        return result.scalar_one() or 0


message_repo = MessageRepository()

