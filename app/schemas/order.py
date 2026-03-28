"""Order Pydantic schemas."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.customer import CustomerResponse
from app.schemas.message import MessageResponse


class OrderItemSchema(BaseModel):
    """A single parsed item within an order."""

    name: str
    qty: int = Field(..., ge=1)
    notes: Optional[str] = None


class OrderResponse(BaseModel):
    """Order data returned in list responses."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    shop_id: uuid.UUID
    customer_id: uuid.UUID
    customer_name: Optional[str] = None     # Populated from joined customer
    customer_phone: Optional[str] = None    # Populated from joined customer
    items: Optional[List[OrderItemSchema]] = None
    status: str
    total_amount: Optional[Decimal] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class OrderDetailResponse(OrderResponse):
    """Full order detail including related customer and message thread."""

    customer: Optional[CustomerResponse] = None
    messages: Optional[List[MessageResponse]] = None
    raw_message: Optional[str] = None


class UpdateOrderStatusRequest(BaseModel):
    """Request body for PATCH /api/v1/orders/{id}/status."""

    status: str = Field(
        ..., description="One of: new, confirmed, ready, delivered, cancelled"
    )

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        """Ensure status is one of the recognised values."""
        valid = {"new", "confirmed", "ready", "delivered", "cancelled"}
        if v not in valid:
            raise ValueError(f"Invalid status '{v}'. Must be one of {sorted(valid)}")
        return v


class UpdateOrderNotesRequest(BaseModel):
    """Request body for PATCH /api/v1/orders/{id}/notes."""

    notes: Optional[str] = Field(None, max_length=2000)
    total_amount: Optional[Decimal] = Field(None, ge=0)


class ReplyToOrderRequest(BaseModel):
    """Request body for POST /api/v1/orders/{id}/reply."""

    message: str = Field(..., min_length=1, max_length=4096)
