"""Conversation endpoints — list threads and send replies."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_shop
from app.core.database import get_async_db
from app.models.shop import Shop
from app.repositories.customer_repo import customer_repo
from app.repositories.message_repo import message_repo
from app.repositories.social_connection_repo import social_connection_repo
from app.models.social_connection import SocialConnectionPlatform
from app.schemas.message import ConversationDetail, ConversationSummary, MessageResponse, SendReplyRequest
from app.services.whatsapp_service import whatsapp_service

router = APIRouter(tags=["Conversations"])


@router.get(
    "/conversations",
    response_model=List[ConversationSummary],
    summary="List all conversations",
)
async def list_conversations(
    current_shop: Shop = Depends(get_current_shop),
    db: AsyncSession = Depends(get_async_db),
) -> List[ConversationSummary]:
    """Return one summary row per customer, ordered by most recent message."""
    latest_messages = await message_repo.get_latest_per_customer(db, current_shop.id)

    result: List[ConversationSummary] = []
    for msg in latest_messages:
        customer = await customer_repo.get(db, msg.customer_id)
        if not customer:
            continue
        unread = await message_repo.count_unread(db, current_shop.id, customer.id)
        result.append(
            ConversationSummary(
                customer_id=customer.id,
                customer_name=customer.name,
                customer_phone=customer.phone_number,
                last_message=msg.body,
                last_message_at=msg.sent_at or msg.created_at,
                last_direction=msg.direction,
                unread_count=unread,
            )
        )
    return result


@router.get(
    "/conversations/{customer_id}/messages",
    response_model=ConversationDetail,
    summary="Get full conversation with a customer",
)
async def get_conversation(
    customer_id: uuid.UUID,
    current_shop: Shop = Depends(get_current_shop),
    db: AsyncSession = Depends(get_async_db),
) -> ConversationDetail:
    customer = await customer_repo.get(db, customer_id)
    if not customer or customer.shop_id != current_shop.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")

    messages = await message_repo.get_for_conversation(db, current_shop.id, customer_id)
    return ConversationDetail(
        customer_id=customer.id,
        customer_name=customer.name,
        customer_phone=customer.phone_number,
        messages=[MessageResponse.model_validate(m) for m in messages],
    )


@router.post(
    "/conversations/{customer_id}/reply",
    response_model=MessageResponse,
    summary="Send a message to a customer",
)
async def send_reply(
    customer_id: uuid.UUID,
    body: SendReplyRequest,
    current_shop: Shop = Depends(get_current_shop),
    db: AsyncSession = Depends(get_async_db),
) -> MessageResponse:
    customer = await customer_repo.get(db, customer_id)
    if not customer or customer.shop_id != current_shop.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")

    connection = await social_connection_repo.get_by_shop_and_platform(
        db, current_shop.id, SocialConnectionPlatform.WHATSAPP
    )
    if not connection or not connection.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active WhatsApp connection for this shop",
        )

    sent = await whatsapp_service.send_text_message_for_shop(
        customer.phone_number, body.message, connection
    )
    if not sent:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to send WhatsApp message",
        )

    msg = await message_repo.create(
        db,
        obj_in={
            "shop_id": current_shop.id,
            "customer_id": customer.id,
            "direction": "outbound",
            "body": body.message,
            "sent_at": datetime.utcnow(),
        },
    )
    return MessageResponse.model_validate(msg)
