"""
WhatsApp Cloud API integration service.

Wraps Meta's Graph API for sending template and free-form messages.
All calls are async (httpx) with 3-attempt exponential backoff on transient
network errors.

Pre-approved template names (register these in Meta Business Manager):
    - order_received   : "Thank you! Your order has been received."
    - order_confirmed  : "Your order is confirmed! We are preparing it now."
    - order_ready      : "Your order is ready for pickup / out for delivery!"
    - order_delivered  : "Your order has been delivered. Thank you!"
    - order_cancelled  : "Sorry, your order has been cancelled."
"""

from __future__ import annotations

import asyncio
from typing import Optional

import httpx

from app.core.config import settings
from app.core.logging import get_logger
from app.models.social_connection import SocialConnection

logger = get_logger(__name__)

# Map order status -> pre-approved template name
STATUS_TEMPLATE_MAP: dict[str, str] = {
    "confirmed": "order_confirmed",
    "ready": "order_ready",
    "delivered": "order_delivered",
    "cancelled": "order_cancelled",
}

_MAX_RETRIES = 3
_RETRY_BACKOFF_BASE = 1.0  # seconds


class WhatsAppService:
    """Async client for the WhatsApp Cloud API (Meta Graph API).

    Instantiate once per request or as an application-scoped singleton.
    """

    def _build_headers(self, access_token: str) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

    def _messages_url(self, phone_number_id: str) -> str:
        return f"https://graph.facebook.com/{settings.WHATSAPP_API_VERSION}/{phone_number_id}/messages"

    async def send_template_message_for_shop(
        self,
        phone_number: str,
        template_name: str,
        connection: SocialConnection,
        language_code: str = "en",
    ) -> bool:
        payload = {
            "messaging_product": "whatsapp",
            "to": phone_number,
            "type": "template",
            "template": {
                "name": template_name,
                "language": {"code": language_code},
            },
        }
        return await self._post_with_retry(
            payload,
            context=f"template:{template_name}",
            url=self._messages_url(connection.phone_number_id),
            headers=self._build_headers(connection.access_token),
        )

    async def send_text_message_for_shop(
        self,
        phone_number: str,
        message: str,
        connection: SocialConnection,
    ) -> bool:
        payload = {
            "messaging_product": "whatsapp",
            "to": phone_number,
            "type": "text",
            "text": {"body": message[:4096]},
        }
        return await self._post_with_retry(
            payload,
            context="text_message",
            url=self._messages_url(connection.phone_number_id),
            headers=self._build_headers(connection.access_token),
        )

    async def notify_status_change_for_shop(
        self,
        phone_number: str,
        new_status: str,
        connection: SocialConnection,
    ) -> bool:
        template_name = STATUS_TEMPLATE_MAP.get(new_status)
        if not template_name:
            logger.debug(
                "no_template_for_status",
                status=new_status,
                note="No customer notification sent for this transition",
            )
            return True

        return await self.send_template_message_for_shop(
            phone_number, template_name, connection
        )

    # ── Internal helpers ──────────────────────────────────────────────────────

    async def _post_with_retry(
        self,
        payload: dict,
        *,
        context: str,
        url: str | None = None,
        headers: dict[str, str] | None = None,
    ) -> bool:
        """POST to the WhatsApp messages endpoint with exponential backoff retry.

        Args:
            payload: The complete JSON request body.
            context: Short string for log context (template name, etc.).

        Returns:
            True on HTTP 2xx, False after all retries exhausted.
        """
        assert url is not None, "url must be provided"
        assert headers is not None, "headers must be provided"

        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    response = await client.post(url, headers=headers, json=payload)

                if response.status_code == 200:
                    logger.info(
                        "whatsapp_message_sent",
                        context=context,
                        to=payload.get("to"),
                        attempt=attempt,
                    )
                    return True

                # Non-retryable 4xx error
                if 400 <= response.status_code < 500:
                    logger.error(
                        "whatsapp_client_error",
                        context=context,
                        status_code=response.status_code,
                        response_body=response.text[:300],
                    )
                    return False

                # 5xx — retryable
                logger.warning(
                    "whatsapp_server_error_retrying",
                    context=context,
                    attempt=attempt,
                    status_code=response.status_code,
                )

            except httpx.TimeoutException:
                logger.warning("whatsapp_timeout", context=context, attempt=attempt)
            except httpx.RequestError as exc:
                logger.warning("whatsapp_request_error", context=context, attempt=attempt, error=str(exc))

            if attempt < _MAX_RETRIES:
                backoff = _RETRY_BACKOFF_BASE * (2 ** (attempt - 1))
                await asyncio.sleep(backoff)

        logger.error("whatsapp_all_retries_failed", context=context)
        return False


# Application-scoped singleton
whatsapp_service = WhatsAppService()
