"""Business logic for managing social platform connections."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ExternalServiceException, NotFoundException, UnauthorizedException
from app.core.logging import get_logger
from app.models.social_connection import (
    SocialConnection,
    SocialConnectionPlatform,
    SocialConnectionStatus,
)
from app.repositories.shop_repo import shop_repo
from app.repositories.social_connection_repo import social_connection_repo
from app.services.meta_oauth_service import meta_oauth_service

logger = get_logger(__name__)


class SocialConnectionService:
    async def connect_whatsapp(
        self,
        db: AsyncSession,
        shop_id: uuid.UUID,
        code: str,
        state: str,
    ) -> SocialConnection:
        """Handle the Meta OAuth flow and persist the WhatsApp connection."""
        validated_shop_id = await meta_oauth_service.validate_state(state)
        if validated_shop_id != shop_id:
            raise UnauthorizedException("OAuth state does not match authenticated shop")

        shop = await shop_repo.get(db, shop_id)
        if not shop or not shop.is_active:
            raise NotFoundException("Shop not found")

        short_token = await meta_oauth_service.exchange_code_for_token(code)
        long_token = await meta_oauth_service.exchange_for_long_lived_token(
            short_token["access_token"]
        )
        expires_in = long_token.get("expires_in")
        expires_at = (
            datetime.utcnow() + timedelta(seconds=expires_in)
            if expires_in
            else None
        )
        scopes = self._extract_scopes(short_token)

        businesses = await meta_oauth_service.get_whatsapp_business_accounts(
            long_token["access_token"]
        )
        waba, business_name = self._pick_business_with_waba(businesses)
        phone_numbers = await meta_oauth_service.get_phone_numbers(
            waba["id"], long_token["access_token"]
        )
        phone = self._pick_phone_number(phone_numbers)

        meta_payload = {
            "business": {
                "id": waba.get("id"),
                "name": business_name,
            },
            "phone": {
                "id": phone.get("id"),
                "display": phone.get("display_phone_number"),
                "verified_name": phone.get("verified_name"),
            },
        }

        connection = await social_connection_repo.get_by_shop_and_platform(
            db, shop_id, SocialConnectionPlatform.WHATSAPP
        )

        token_data = {
            "access_token": long_token["access_token"],
            "refresh_token": long_token.get("refresh_token"),
            "token_expires_at": expires_at,
            "status": SocialConnectionStatus.CONNECTED,
            "error_message": None,
            "last_sync_at": datetime.utcnow(),
            "scopes": scopes,
            "meta": meta_payload,
            "is_active": True,
        }

        if connection:
            updated = await social_connection_repo.update(db, db_obj=connection, updates=token_data)
            logger.info(
                "social_connection_updated",
                shop_id=str(shop_id),
                connection_id=str(updated.id),
            )
            return updated

        obj_in = {
            "shop_id": shop_id,
            "platform": SocialConnectionPlatform.WHATSAPP,
            "platform_account_id": waba.get("id"),
            "phone_number_id": phone.get("id"),
            "display_phone_number": phone.get("display_phone_number"),
            **token_data,
        }
        created = await social_connection_repo.create(db, obj_in=obj_in)
        logger.info(
            "social_connection_created",
            shop_id=str(shop_id),
            connection_id=str(created.id),
        )
        return created

    async def disconnect(
        self,
        db: AsyncSession,
        shop_id: uuid.UUID,
        connection_id: uuid.UUID,
    ) -> None:
        connection = await social_connection_repo.get(db, connection_id)
        if not connection or connection.shop_id != shop_id:
            raise NotFoundException("Connection not found")
        await social_connection_repo.update(
            db,
            db_obj=connection,
            updates={
                "is_active": False,
                "status": SocialConnectionStatus.REVOKED,
                "last_sync_at": datetime.utcnow(),
            },
        )
        logger.info(
            "social_connection_revoked",
            shop_id=str(shop_id),
            connection_id=str(connection_id),
        )

    async def refresh_connection_token(
        self, db: AsyncSession, connection: SocialConnection
    ) -> SocialConnection:
        refreshed = await meta_oauth_service.refresh_token(connection.access_token)
        expires_in = refreshed.get("expires_in")
        expires_at = (
            datetime.utcnow() + timedelta(seconds=expires_in)
            if expires_in
            else None
        )
        return await social_connection_repo.update_token(
            db,
            connection_id=connection.id,
            access_token=refreshed["access_token"],
            expires_at=expires_at,
            refresh_token=refreshed.get("refresh_token"),
        )

    async def list_connections(
        self, db: AsyncSession, shop_id: uuid.UUID
    ) -> List[SocialConnection]:
        return await social_connection_repo.get_active_for_shop(db, shop_id)

    def _extract_scopes(self, token_response: Dict[str, Any]) -> Optional[List[str]]:
        raw = token_response.get("scope")
        if not raw or not isinstance(raw, str):
            return None
        return [scope.strip() for scope in raw.replace(",", " ").split() if scope.strip()]

    def _pick_business_with_waba(
        self, businesses: List[Dict[str, Any]]
    ) -> Tuple[Dict[str, Any], Optional[str]]:
        for business in businesses:
            wabas = (
                business.get("whatsapp_business_accounts", {}).get("data") or []
            )
            if wabas:
                return wabas[0], business.get("name")
        raise ExternalServiceException("Meta OAuth", "No business accounts found on this WhatsApp number")

    def _pick_phone_number(self, numbers: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not numbers:
            raise ExternalServiceException("Meta OAuth", "No phone numbers associated with WABA")
        return numbers[0]


social_connection_service = SocialConnectionService()
