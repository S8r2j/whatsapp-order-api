"""
Shop profile endpoints.

Routes:
    GET    /api/v1/shop/profile  — Fetch current shop profile
    PATCH  /api/v1/shop/profile  — Update shop name and/or phone number
    PATCH  /api/v1/shop/hours    — Update business hours
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_shop
from app.core.database import get_async_db
from app.core.encryption import hash_for_lookup
from app.core.exceptions import ConflictException
from app.core.logging import get_logger
from app.models.shop import Shop
from app.repositories.shop_repo import shop_repo
from app.schemas.shop import ShopProfileResponse, UpdateBusinessHoursRequest, UpdateShopProfileRequest

logger = get_logger(__name__)

router = APIRouter(prefix="/shop", tags=["Shop Profile"])


@router.get(
    "/profile",
    response_model=ShopProfileResponse,
    summary="Get shop profile",
    description="Returns the authenticated shop's profile information.",
)
async def get_shop_profile(
    current_shop: Shop = Depends(get_current_shop),
) -> ShopProfileResponse:
    """Return the current shop's profile."""
    return ShopProfileResponse.model_validate(current_shop)


@router.patch(
    "/profile",
    response_model=ShopProfileResponse,
    summary="Update shop profile",
    description="Update the shop's display name and/or WhatsApp phone number.",
)
async def update_shop_profile(
    payload: UpdateShopProfileRequest,
    current_shop: Shop = Depends(get_current_shop),
    db: AsyncSession = Depends(get_async_db),
) -> ShopProfileResponse:
    """Update the shop's name and/or phone number."""
    updates: dict = {}

    if payload.name is not None:
        updates["name"] = payload.name

    if payload.phone_number is not None:
        # Check uniqueness via hash index
        existing = await shop_repo.get_by_phone(db, payload.phone_number)
        if existing and existing.id != current_shop.id:
            raise ConflictException("This phone number is already registered to another shop")
        updates["phone_number"] = payload.phone_number
        updates["phone_hash"] = hash_for_lookup(payload.phone_number)

    updated_shop = await shop_repo.update(db, db_obj=current_shop, updates=updates)
    logger.info("shop_profile_updated", shop_id=str(current_shop.id))
    return ShopProfileResponse.model_validate(updated_shop)


@router.patch(
    "/hours",
    response_model=ShopProfileResponse,
    summary="Update business hours",
    description='Update business hours. Format: {"mon": "09:00-18:00", "tue": "closed"}',
)
async def update_business_hours(
    payload: UpdateBusinessHoursRequest,
    current_shop: Shop = Depends(get_current_shop),
    db: AsyncSession = Depends(get_async_db),
) -> ShopProfileResponse:
    """Replace the shop's business_hours JSONB field."""
    updated_shop = await shop_repo.update(
        db, db_obj=current_shop, updates={"business_hours": payload.hours}
    )
    logger.info("business_hours_updated", shop_id=str(current_shop.id))
    return ShopProfileResponse.model_validate(updated_shop)
