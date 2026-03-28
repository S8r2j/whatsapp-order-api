"""Meta OAuth flow helpers for WhatsApp Business connections."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, List
from urllib.parse import urlencode
import uuid

import httpx
from jose import JWTError, jwt

from app.core.config import settings
from app.core.exceptions import ExternalServiceException, UnauthorizedException
from app.core.logging import get_logger

logger = get_logger(__name__)

OAUTH_SCOPES = "whatsapp_business_management,whatsapp_business_messaging,business_management"


class MetaOAuthService:
    """Encapsulates Meta OAuth handshake and token refresh logic."""

    def __init__(self) -> None:
        self._oauth_dialog = (
            f"https://www.facebook.com/{settings.WHATSAPP_API_VERSION}/dialog/oauth"
        )
        self._api_base = f"https://graph.facebook.com/{settings.WHATSAPP_API_VERSION}"

    async def generate_authorization_url(self, shop_id: uuid.UUID) -> str:
        """Build the Meta OAuth consent URL for the given shop."""
        now = datetime.utcnow()
        state_payload = {
            "shop_id": str(shop_id),
            "nonce": str(uuid.uuid4()),
            "exp": now + timedelta(minutes=settings.OAUTH_STATE_EXPIRE_MINUTES),
        }
        signed_state = jwt.encode(
            state_payload,
            settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM,
        )
        params = {
            "client_id": settings.META_APP_ID,
            "redirect_uri": settings.oauth_redirect_uri,
            "scope": OAUTH_SCOPES,
            "state": signed_state,
            "response_type": "code",
        }
        return f"{self._oauth_dialog}?{urlencode(params)}"

    async def validate_state(self, state: str) -> uuid.UUID:
        """Validate the signed OAuth state token and extract the shop_id."""
        try:
            payload = jwt.decode(
                state,
                settings.JWT_SECRET_KEY,
                algorithms=[settings.JWT_ALGORITHM],
            )
        except JWTError as exc:
            logger.warning("oauth_state_invalid", error=str(exc))
            raise UnauthorizedException("Invalid OAuth state") from exc

        shop_id = payload.get("shop_id")
        if not shop_id:
            raise UnauthorizedException("OAuth state missing shop_id")

        try:
            return uuid.UUID(shop_id)
        except ValueError as exc:
            logger.warning("oauth_state_bad_shop_id", shop_id=shop_id)
            raise UnauthorizedException("Invalid shop_id in OAuth state") from exc

    async def exchange_code_for_token(self, code: str) -> Dict[str, Any]:
        """Exchange the short-lived code for a user access token."""
        url = f"{self._api_base}/oauth/access_token"
        params = {
            "client_id": settings.META_APP_ID,
            "client_secret": settings.META_APP_SECRET,
            "redirect_uri": settings.oauth_redirect_uri,
            "code": code,
        }
        return await self._http_request("post", url, params, context="exchange_code")

    async def exchange_for_long_lived_token(self, short_lived_token: str) -> Dict[str, Any]:
        """Exchange the short-lived token for a long-lived token (valid ~60 days)."""
        url = f"{self._api_base}/oauth/access_token"
        params = {
            "grant_type": "fb_exchange_token",
            "client_id": settings.META_APP_ID,
            "client_secret": settings.META_APP_SECRET,
            "fb_exchange_token": short_lived_token,
        }
        return await self._http_request("get", url, params, context="long_lived_exchange")

    async def get_whatsapp_business_accounts(self, access_token: str) -> List[Dict[str, Any]]:
        """Return the list of WhatsApp Business Accounts the user manages.

        Meta does not allow fetching ``whatsapp_business_accounts`` as a nested
        field on ``/me/businesses``.  We use a two-step approach instead:
          1. ``GET /me/businesses?fields=id,name`` — list the businesses.
          2. For each business, ``GET /{biz_id}/whatsapp_business_accounts`` — list WABAs.

        The returned structure mirrors what the rest of the service layer expects:
        ``[{"id": biz_id, "name": biz_name, "whatsapp_business_accounts": {"data": [...]}}]``
        """
        # Step 1: list businesses via Business Manager
        biz_response = await self._http_request(
            "get",
            f"{self._api_base}/me/businesses",
            {"access_token": access_token, "fields": "id,name"},
            context="list_businesses",
        )
        businesses: List[Dict[str, Any]] = biz_response.get("data", [])

        # Step 2: fetch WABAs for each business and stitch them in
        result: List[Dict[str, Any]] = []
        for biz in businesses:
            biz_id = biz.get("id")
            try:
                waba_response = await self._http_request(
                    "get",
                    f"{self._api_base}/{biz_id}/whatsapp_business_accounts",
                    {"access_token": access_token, "fields": "id,name"},
                    context=f"list_wabas_for_{biz_id}",
                )
                wabas = waba_response.get("data", [])
            except ExternalServiceException:
                logger.warning("waba_fetch_failed_for_business", biz_id=biz_id)
                wabas = []

            result.append({
                "id": biz_id,
                "name": biz.get("name"),
                "whatsapp_business_accounts": {"data": wabas},
            })

        return result

    async def get_phone_numbers(self, waba_id: str, access_token: str) -> List[Dict[str, Any]]:
        """Return the phone numbers associated with a WhatsApp Business Account."""
        url = f"{self._api_base}/{waba_id}/phone_numbers"
        params = {
            "access_token": access_token,
            "fields": "id,display_phone_number,verified_name",
        }
        response = await self._http_request("get", url, params, context="list_phone_numbers")
        return response.get("data", [])

    async def refresh_token(self, current_token: str) -> Dict[str, Any]:
        """Refresh the long-lived token (must be called before it expires)."""
        return await self.exchange_for_long_lived_token(current_token)

    async def _http_request(
        self,
        method: str,
        url: str,
        params: Dict[str, Any],
        *,
        context: str,
    ) -> Dict[str, Any]:
        """Helper that issues an HTTP request and handles Meta API errors."""
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.request(method, url, params=params)
        except httpx.RequestError as exc:
            logger.error("meta_oauth_request_failed", context=context, error=str(exc))
            raise ExternalServiceException("Meta OAuth", str(exc)) from exc

        if response.status_code != 200:
            logger.error(
                "meta_oauth_bad_response",
                context=context,
                status_code=response.status_code,
                body=response.text[:300],
            )
            raise ExternalServiceException("Meta OAuth", response.text)

        return response.json()


meta_oauth_service = MetaOAuthService()
