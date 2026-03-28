"""Customer Pydantic schemas."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class CustomerResponse(BaseModel):
    """Customer data returned in API responses."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    shop_id: uuid.UUID
    phone_number: str
    name: Optional[str] = None
    total_orders: int
    created_at: datetime
    updated_at: datetime


class UpdateCustomerRequest(BaseModel):
    """Request body for PATCH /api/v1/customers/{id}."""

    name: Optional[str] = Field(None, min_length=1, max_length=100)
