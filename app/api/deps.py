"""
FastAPI dependency injection helpers.

Provides reusable dependencies for:
- Database session injection
- Authenticated shop extraction from JWT bearer token
- Optional rate limiting key extraction
"""

from __future__ import annotations

import structlog
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_db
from app.core.exceptions import UnauthorizedException
from app.core.security import extract_shop_id
from app.models.shop import Shop
from app.repositories.shop_repo import shop_repo

import uuid

security = HTTPBearer()


async def get_current_shop(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_async_db),
) -> Shop:
    """Extract and validate the authenticated shop from the Bearer JWT token.

    Steps:
    1. Decode the JWT and extract the shop_id (``sub`` claim).
    2. Fetch the shop from the database.
    3. Verify the shop exists and is active.
    4. Bind shop_id to the structlog context for request-scoped logging.

    Args:
        credentials: HTTP Bearer token from the Authorization header.
        db: Async database session.

    Returns:
        The authenticated ``Shop`` model instance.

    Raises:
        UnauthorizedException: On invalid token, missing shop, or inactive shop.
    """
    shop_id_str = extract_shop_id(credentials.credentials)

    try:
        shop_uuid = uuid.UUID(shop_id_str)
    except ValueError:
        raise UnauthorizedException("Invalid token payload")

    shop = await shop_repo.get(db, shop_uuid)

    if shop is None:
        raise UnauthorizedException("Shop not found")

    if not shop.is_active:
        raise UnauthorizedException("Account is disabled")

    # Bind shop_id to structlog context so all subsequent log records include it
    structlog.contextvars.bind_contextvars(shop_id=str(shop.id))

    return shop
