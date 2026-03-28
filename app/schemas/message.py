"""Message Pydantic schemas."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict


class MessageResponse(BaseModel):
    """A single message in a conversation."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    shop_id: uuid.UUID
    customer_id: uuid.UUID
    order_id: Optional[uuid.UUID] = None
    direction: str  # inbound | outbound
    body: str
    wa_message_id: Optional[str] = None
    sent_at: Optional[datetime] = None
    created_at: datetime


class ConversationSummary(BaseModel):
    """One row in the conversation list — represents a thread with a customer."""

    customer_id: uuid.UUID
    customer_name: Optional[str] = None
    customer_phone: str
    last_message: str
    last_message_at: Optional[datetime] = None
    last_direction: str
    unread_count: int = 0


class ConversationDetail(BaseModel):
    """Full conversation thread with a customer."""

    customer_id: uuid.UUID
    customer_name: Optional[str] = None
    customer_phone: str
    messages: List[MessageResponse]


class SendReplyRequest(BaseModel):
    """Body for the shop/AI sending an outbound message."""

    message: str

