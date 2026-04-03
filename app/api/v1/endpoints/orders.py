"""
Order management endpoints.

Routes:
    GET    /api/v1/orders               — List orders (filtered, paginated)
    GET    /api/v1/orders/{id}          — Single order detail with messages
    PATCH  /api/v1/orders/{id}/status   — Update status + notify customer
    PATCH  /api/v1/orders/{id}/notes    — Update internal notes / amount
    POST   /api/v1/orders/{id}/reply    — Send manual WhatsApp reply
"""

from __future__ import annotations

import math
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_shop
from app.core.database import get_async_db
from app.core.logging import get_logger
from app.models.shop import Shop
from app.schemas.common import PaginatedResponse
from app.schemas.order import (
    OrderDetailResponse,
    OrderResponse,
    ReplyToOrderRequest,
    UpdateOrderNotesRequest,
    UpdateOrderStatusRequest,
)
from app.services.order_service import order_service

logger = get_logger(__name__)

router = APIRouter(prefix="/orders", tags=["Orders"])


@router.get(
    "",
    response_model=PaginatedResponse[OrderResponse],
    summary="List orders",
    description="Returns a paginated list of orders for the authenticated shop.",
)
async def list_orders(
    status: Optional[str] = Query(None, description="Filter by status"),
    customer_id: Optional[uuid.UUID] = Query(None, description="Filter by customer"),
    from_date: Optional[datetime] = Query(None, description="Filter from this date (ISO 8601)"),
    to_date: Optional[datetime] = Query(None, description="Filter up to this date (ISO 8601)"),
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    size: int = Query(20, ge=1, le=100, description="Items per page (max 100)"),
    current_shop: Shop = Depends(get_current_shop),
    db: AsyncSession = Depends(get_async_db),
) -> PaginatedResponse[OrderResponse]:
    """Fetch a paginated, optionally filtered list of orders."""
    orders, total = await order_service.list_orders(
        db,
        current_shop.id,
        status=status,
        customer_id=customer_id,
        from_date=from_date,
        to_date=to_date,
        page=page,
        size=size,
    )

    # Enrich with customer name/phone from joined customer
    items = []
    for order in orders:
        resp = OrderResponse.model_validate(order)
        if order.customer:
            resp.customer_name = order.customer.name
            resp.customer_phone = order.customer.phone_number
        items.append(resp)

    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        size=size,
        pages=math.ceil(total / size) if size else 1,
    )


@router.get(
    "/{order_id}",
    response_model=OrderDetailResponse,
    summary="Get order detail",
    description="Returns full order detail including customer info and message thread.",
)
async def get_order(
    order_id: uuid.UUID,
    current_shop: Shop = Depends(get_current_shop),
    db: AsyncSession = Depends(get_async_db),
) -> OrderDetailResponse:
    """Fetch a single order with its complete message thread."""
    order = await order_service.get_order_detail(db, order_id, current_shop.id)
    return OrderDetailResponse.model_validate(order)


@router.patch(
    "/{order_id}/status",
    response_model=OrderDetailResponse,
    summary="Update order status",
    description="Transition an order to a new status and notify the customer via WhatsApp.",
)
async def update_order_status(
    order_id: uuid.UUID,
    payload: UpdateOrderStatusRequest,
    current_shop: Shop = Depends(get_current_shop),
    db: AsyncSession = Depends(get_async_db),
) -> OrderDetailResponse:
    """Update the order's status. Sends a WhatsApp template to the customer."""
    order = await order_service.update_status(db, order_id, current_shop.id, payload.status)
    return OrderDetailResponse.model_validate(order)


@router.patch(
    "/{order_id}/notes",
    response_model=OrderDetailResponse,
    summary="Update order notes",
    description="Update internal shop notes and/or total amount for an order.",
)
async def update_order_notes(
    order_id: uuid.UUID,
    payload: UpdateOrderNotesRequest,
    current_shop: Shop = Depends(get_current_shop),
    db: AsyncSession = Depends(get_async_db),
) -> OrderDetailResponse:
    """Update notes and/or total amount. Does not send any customer notification."""
    order = await order_service.update_notes(
        db, order_id, current_shop.id, payload.notes, payload.total_amount
    )
    return OrderDetailResponse.model_validate(order)


@router.post(
    "/{order_id}/reply",
    response_model=dict,
    summary="Send manual reply",
    description="Send a free-form WhatsApp message to the customer (within 24-hour window).",
)
async def reply_to_order(
    order_id: uuid.UUID,
    payload: ReplyToOrderRequest,
    current_shop: Shop = Depends(get_current_shop),
    db: AsyncSession = Depends(get_async_db),
) -> dict:
    """Send a free-form WhatsApp text reply and log it as an outbound message."""
    sent = await order_service.reply_to_order(
        db, order_id, current_shop.id, payload.message
    )
    return {"sent": sent, "message": "Reply sent" if sent else "Failed to send — check WhatsApp API credentials"}
