"""AI reply generation service.

Placeholder implementation — returns a fixed acknowledgement message.
Replace ``generate_reply`` body with your LLM integration when ready.
The function signature is the stable API the rest of the app depends on.
"""

from __future__ import annotations

from typing import List

from app.core.logging import get_logger
from app.models.message import Message
from app.models.shop import Shop

logger = get_logger(__name__)

_PLACEHOLDER = (
    "Hi! Thanks for reaching out. We've received your message "
    "and will get back to you shortly. 😊"
)


class AIService:
    async def generate_reply(
        self,
        conversation_history: List[Message],
        shop: Shop,
    ) -> str:
        """Generate a conversational reply given the message history and shop context.

        Args:
            conversation_history: All messages in this conversation, oldest first.
            shop: The shop that owns the WhatsApp number (for product/context data).

        Returns:
            Reply text to send back to the customer.
        """
        # ── TODO: replace with LLM call ───────────────────────────────────────
        # Example future integration:
        #   from app.services.openai_service import openai_service
        #   return await openai_service.chat(conversation_history, shop)
        # ─────────────────────────────────────────────────────────────────────
        logger.info("ai_reply_placeholder", shop_id=str(shop.id))
        return _PLACEHOLDER


ai_service = AIService()
