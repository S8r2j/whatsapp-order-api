"""
Authentication service — business logic for registration and login.

Sits between the HTTP layer and the repository layer, enforcing all
auth-related business rules.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.encryption import hash_for_lookup
from app.core.exceptions import ConflictException, UnauthorizedException
from app.core.logging import get_logger
from app.core.security import create_access_token, hash_password, verify_password
from app.models.shop import Shop
from app.repositories.shop_repo import shop_repo
from app.schemas.auth import RegisterRequest

logger = get_logger(__name__)


class AuthService:
    """Handles shop registration, login, and token issuance."""

    async def register(self, db: AsyncSession, payload: RegisterRequest) -> tuple[str, Shop]:
        """Register a new shop.

        Steps:
        1. Check email uniqueness via hash index.
        2. Check phone uniqueness (if provided) via hash index.
        3. Hash the password (bcrypt, 12 rounds).
        4. Insert the new shop record with encrypted fields.
        5. Return (access_token, shop).

        Args:
            db: Async database session.
            payload: Validated registration request body.

        Returns:
            Tuple of (JWT access token string, newly created Shop).

        Raises:
            ConflictException: If email or phone already exists.
        """
        # Uniqueness checks using hash indexes (no decryption needed)
        if await shop_repo.email_exists(db, payload.email):
            raise ConflictException("An account with this email already exists")

        if payload.phone_number and await shop_repo.phone_exists(db, payload.phone_number):
            raise ConflictException("This phone number is already linked to another account")

        # Build record
        new_shop = await shop_repo.create(
            db,
            obj_in={
                "name": payload.name,
                "email": payload.email,
                "email_hash": hash_for_lookup(payload.email),
                "phone_number": payload.phone_number,
                "phone_hash": hash_for_lookup(payload.phone_number) if payload.phone_number else None,
                "password_hash": hash_password(payload.password),
                "is_active": True,
            },
        )

        token = create_access_token(subject=str(new_shop.id))
        logger.info("shop_registered", shop_id=str(new_shop.id))
        return token, new_shop

    async def login(self, db: AsyncSession, email: str, password: str) -> tuple[str, Shop]:
        """Authenticate a shop by email + password.

        Args:
            db: Async database session.
            email: The submitted email address.
            password: The submitted plaintext password.

        Returns:
            Tuple of (JWT access token string, authenticated Shop).

        Raises:
            UnauthorizedException: On invalid credentials.
        """
        shop = await shop_repo.get_by_email(db, email)

        # Use constant-time comparison even on miss to prevent timing attacks
        dummy_hash = "$2b$12$AAAAAAAAAAAAAAAAAAAAAA.AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
        stored_hash = shop.password_hash if shop else dummy_hash

        credentials_ok = verify_password(password, stored_hash)

        if not shop or not credentials_ok:
            logger.warning("login_failed", reason="invalid_credentials")
            raise UnauthorizedException("Invalid email or password")

        if not shop.is_active:
            logger.warning("login_failed", reason="account_inactive", shop_id=str(shop.id))
            raise UnauthorizedException("Account is disabled — contact support")

        token = create_access_token(subject=str(shop.id))
        logger.info("shop_logged_in", shop_id=str(shop.id))
        return token, shop

    async def refresh_token(self, db: AsyncSession, shop_id: str) -> tuple[str, Shop]:
        """Issue a new access token for an already-authenticated shop.

        Args:
            db: Async database session.
            shop_id: The shop's UUID string (from the existing token's sub claim).

        Returns:
            Tuple of (new JWT token, shop).

        Raises:
            UnauthorizedException: If the shop no longer exists or is inactive.
        """
        import uuid as _uuid
        shop = await shop_repo.get(db, _uuid.UUID(shop_id))
        if not shop or not shop.is_active:
            raise UnauthorizedException("Shop not found or inactive")

        token = create_access_token(subject=shop_id)
        logger.info("token_refreshed", shop_id=shop_id)
        return token, shop


auth_service = AuthService()
