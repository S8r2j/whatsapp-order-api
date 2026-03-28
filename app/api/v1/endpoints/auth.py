"""
Authentication endpoints.

Routes:
    POST /api/v1/auth/register  — Create a new shop account
    POST /api/v1/auth/login     — Authenticate and receive a JWT
    POST /api/v1/auth/refresh   — Exchange a valid token for a new one

Rate limits (enforced by slowapi):
    /register — 10 requests per 15 minutes per IP
    /login    — 10 requests per 15 minutes per IP
"""

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_async_db
from app.core.logging import get_logger
from app.core.security import extract_shop_id
from app.middleware.rate_limit import limiter as _limiter
from app.schemas.auth import LoginRequest, RefreshRequest, RegisterRequest, TokenResponse
from app.services.auth_service import auth_service

logger = get_logger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=201,
    summary="Register a new shop",
    description="Create a new shop account. Returns a JWT on success. Rate limited to 10/15min.",
)
@_limiter.limit(settings.RATE_LIMIT_LOGIN)
async def register(
    request: Request,
    payload: RegisterRequest,
    db: AsyncSession = Depends(get_async_db),
) -> TokenResponse:
    """Register a new shop and return an access token."""
    token, shop = await auth_service.register(db, payload)
    logger.info("register_success", email_domain=payload.email.split("@")[-1])
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        shop=shop,  # type: ignore[arg-type]
    )


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Authenticate shop",
    description="Login with email and password. Returns a JWT access token. Rate limited to 10/15min.",
)
@_limiter.limit(settings.RATE_LIMIT_LOGIN)
async def login(
    request: Request,
    payload: LoginRequest,
    db: AsyncSession = Depends(get_async_db),
) -> TokenResponse:
    """Authenticate a shop owner and return an access token."""
    token, shop = await auth_service.login(db, payload.email, payload.password)
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        shop=shop,  # type: ignore[arg-type]
    )


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Refresh access token",
    description="Exchange a valid token for a new one with a fresh expiry.",
)
async def refresh(
    payload: RefreshRequest,
    db: AsyncSession = Depends(get_async_db),
) -> TokenResponse:
    """Issue a new JWT for an already-authenticated shop."""
    shop_id = extract_shop_id(payload.token)
    token, shop = await auth_service.refresh_token(db, shop_id)
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        shop=shop,  # type: ignore[arg-type]
    )
