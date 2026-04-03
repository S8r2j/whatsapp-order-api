"""
Customer management endpoints.

Routes:
    GET    /api/v1/customers        — List customers (paginated)
    GET    /api/v1/customers/{id}   — Customer detail with recent orders
    PATCH  /api/v1/customers/{id}   — Update customer name
"""

from __future__ import annotations

import math
import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_shop
from app.core.database import get_async_db
from app.models.shop import Shop
from app.schemas.common import PaginatedResponse
from app.schemas.customer import CustomerResponse, UpdateCustomerRequest
from app.schemas.order import OrderResponse
from app.services.customer_service import customer_service

router = APIRouter(prefix="/customers", tags=["Customers"])


@router.get(
    "",
    response_model=PaginatedResponse[CustomerResponse],
    summary="List customers",
    description="Returns a paginated list of all customers for the authenticated shop.",
)
async def list_customers(
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=200),
    current_shop: Shop = Depends(get_current_shop),
    db: AsyncSession = Depends(get_async_db),
) -> PaginatedResponse[CustomerResponse]:
    """List all customers for the authenticated shop."""
    customers, total = await customer_service.list_customers(
        db, current_shop.id, page=page, size=size
    )
    return PaginatedResponse(
        items=[CustomerResponse.model_validate(c) for c in customers],
        total=total,
        page=page,
        size=size,
        pages=math.ceil(total / size) if size else 1,
    )


@router.get(
    "/{customer_id}",
    response_model=CustomerResponse,
    summary="Get customer detail",
    description="Returns a customer's profile and their recent orders.",
)
async def get_customer(
    customer_id: uuid.UUID,
    current_shop: Shop = Depends(get_current_shop),
    db: AsyncSession = Depends(get_async_db),
) -> CustomerResponse:
    """Fetch a single customer profile."""
    customer = await customer_service.get_customer(db, customer_id, current_shop.id)
    return CustomerResponse.model_validate(customer)


@router.get(
    "/{customer_id}/orders",
    response_model=PaginatedResponse[OrderResponse],
    summary="Get customer orders",
    description="Returns paginated orders placed by a specific customer.",
)
async def get_customer_orders(
    customer_id: uuid.UUID,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    current_shop: Shop = Depends(get_current_shop),
    db: AsyncSession = Depends(get_async_db),
) -> PaginatedResponse[OrderResponse]:
    """List orders placed by a specific customer."""
    orders, total = await customer_service.get_customer_orders(
        db, customer_id, current_shop.id, page=page, size=size
    )
    return PaginatedResponse(
        items=[OrderResponse.model_validate(o) for o in orders],
        total=total,
        page=page,
        size=size,
        pages=math.ceil(total / size) if size else 1,
    )


@router.patch(
    "/{customer_id}",
    response_model=CustomerResponse,
    summary="Update customer",
    description="Update a customer's display name.",
)
async def update_customer(
    customer_id: uuid.UUID,
    payload: UpdateCustomerRequest,
    current_shop: Shop = Depends(get_current_shop),
    db: AsyncSession = Depends(get_async_db),
) -> CustomerResponse:
    """Update a customer's display name."""
    customer = await customer_service.update_customer(
        db, customer_id, current_shop.id, payload.name
    )
    return CustomerResponse.model_validate(customer)
