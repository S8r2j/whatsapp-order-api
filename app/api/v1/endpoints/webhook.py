"""
WhatsApp webhook endpoints.

Routes:
    GET  /webhook  — Meta webhook verification handshake
    POST /webhook  — Inbound message handler

IMPORTANT: The POST handler ALWAYS returns HTTP 200, even on errors.
If Meta receives any other status code, it will retry indefinitely.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict

from fastapi import APIRouter, BackgroundTasks, Depends, Query, Request, Response
from fastapi.responses import PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_async_db
from app.core.encryption import hash_for_lookup
from app.core.logging import get_logger
from app.repositories.customer_repo import customer_repo
from app.repositories.message_repo import message_repo
from app.repositories.shop_repo import shop_repo
from app.repositories.social_connection_repo import social_connection_repo
from app.services.ai_service import ai_service
from app.services.whatsapp_service import whatsapp_service

logger = get_logger(__name__)

router = APIRouter(tags=["Webhook"])


@router.get(
    "/webhook/debug",
    summary="Debug — show stored social connections and recent messages",
    include_in_schema=False,
)
async def webhook_debug(db: AsyncSession = Depends(get_async_db)) -> Dict[str, Any]:
    """Dev-only: shows what phone_number_ids are stored and recent messages."""
    from sqlalchemy import select, desc
    from app.models.social_connection import SocialConnection
    from app.models.message import Message

    conns_result = await db.execute(select(SocialConnection))
    conns = conns_result.scalars().all()

    msgs_result = await db.execute(
        select(Message).order_by(desc(Message.created_at)).limit(5)
    )
    msgs = msgs_result.scalars().all()

    return {
        "social_connections": [
            {
                "id": str(c.id),
                "platform": c.platform.value if hasattr(c.platform, "value") else str(c.platform),
                "phone_number_id": c.phone_number_id,
                "display_phone_number": c.display_phone_number,
                "status": c.status.value if hasattr(c.status, "value") else str(c.status),
                "is_active": c.is_active,
            }
            for c in conns
        ],
        "recent_messages": [
            {
                "id": str(m.id),
                "direction": m.direction,
                "body": m.body[:80] if m.body else "",
                "wa_message_id": m.wa_message_id,
                "created_at": str(m.created_at),
            }
            for m in msgs
        ],
    }


@router.get(
    "/webhook",
    summary="WhatsApp webhook verification",
)
async def verify_webhook(
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_verify_token: str = Query(None, alias="hub.verify_token"),
    hub_challenge: str = Query(None, alias="hub.challenge"),
) -> Response:
    if hub_mode == "subscribe" and hub_verify_token == settings.WEBHOOK_VERIFY_TOKEN:
        logger.info("webhook_verified")
        return PlainTextResponse(content=hub_challenge, status_code=200)

    logger.warning(
        "webhook_verification_failed",
        mode=hub_mode,
        token_match=(hub_verify_token == settings.WEBHOOK_VERIFY_TOKEN),
    )
    return Response(status_code=403)


@router.post(
    "/webhook",
    summary="WhatsApp inbound message handler",
)
async def handle_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_async_db),
) -> Dict[str, str]:
    try:
        payload = await request.json()
        logger.info("webhook_post_received", payload_preview=str(payload)[:300])
        await _process_webhook(payload, background_tasks, db)
    except Exception as exc:
        logger.error("webhook_processing_error", error=str(exc), exc_info=True)

    return {"status": "ok"}


async def _process_webhook(
    payload: Dict[str, Any],
    background_tasks: BackgroundTasks,
    db: AsyncSession,
) -> None:
    # ── 1. Parse Meta's nested payload ────────────────────────────────────────
    try:
        entry = payload["entry"][0]
        change = entry["changes"][0]["value"]
        messages = change.get("messages")

        if not messages:
            logger.debug("webhook_no_messages", payload_type=str(change.get("statuses", "unknown")))
            return

        raw_msg = messages[0]
        wa_message_id: str = raw_msg["id"]
        from_phone: str = raw_msg["from"]
        message_text: str = raw_msg.get("text", {}).get("body", "")
        timestamp_unix: int = int(raw_msg.get("timestamp", datetime.utcnow().timestamp()))
        sent_at = datetime.utcfromtimestamp(timestamp_unix)

    except (KeyError, IndexError, TypeError) as exc:
        logger.error("webhook_payload_parse_failed", error=str(exc))
        return

    logger.info("webhook_message_received", wa_message_id=wa_message_id, from_phone_tail=from_phone[-4:])

    # ── 2. Deduplicate ─────────────────────────────────────────────────────────
    if await message_repo.wa_message_exists(db, wa_message_id):
        logger.info("webhook_duplicate_skipped", wa_message_id=wa_message_id)
        return

    # ── 3. Resolve shop via the social connection that owns this phone_number_id
    metadata = change.get("metadata", {})
    phone_number_id = metadata.get("phone_number_id")
    if not phone_number_id:
        logger.error("webhook_missing_phone_number_id")
        return

    connection = await social_connection_repo.get_by_phone_number_id(db, phone_number_id)
    if not connection or not connection.is_active:
        logger.error("webhook_no_connection_for_phone_id", phone_number_id=phone_number_id)
        return

    shop = await shop_repo.get(db, connection.shop_id)
    if not shop or not shop.is_active:
        logger.error("webhook_shop_not_found_or_inactive", shop_id=str(connection.shop_id))
        return

    # ── 4. Upsert customer ─────────────────────────────────────────────────────
    phone_hash = hash_for_lookup(from_phone)
    customer = await customer_repo.get_by_phone_for_shop(db, shop.id, from_phone)

    if not customer:
        customer = await customer_repo.create(
            db,
            obj_in={
                "shop_id": shop.id,
                "phone_number": from_phone,
                "phone_hash": phone_hash,
                "total_orders": 0,
            },
        )
        logger.info("new_customer_created", customer_id=str(customer.id))

    # ── 5. Store inbound message ───────────────────────────────────────────────
    await message_repo.create(
        db,
        obj_in={
            "shop_id": shop.id,
            "customer_id": customer.id,
            "direction": "inbound",
            "body": message_text,
            "wa_message_id": wa_message_id,
            "sent_at": sent_at,
        },
    )

    logger.info("message_stored", shop_id=str(shop.id), customer_id=str(customer.id))

    # ── 6. Generate AI reply and send in background ───────────────────────────
    # Load conversation history for context
    conversation_history = await message_repo.get_for_conversation(
        db, shop.id, customer.id, limit=20
    )

    async def _send_ai_reply() -> None:
        try:
            reply_text = await ai_service.generate_reply(conversation_history, shop)
            sent = await whatsapp_service.send_text_message_for_shop(
                from_phone, reply_text, connection
            )
            if sent:
                # Store the outbound reply — use a new DB session from the app
                from app.core.database import AsyncSessionLocal
                async with AsyncSessionLocal() as reply_db:
                    await message_repo.create(
                        reply_db,
                        obj_in={
                            "shop_id": shop.id,
                            "customer_id": customer.id,
                            "direction": "outbound",
                            "body": reply_text,
                            "sent_at": datetime.utcnow(),
                        },
                    )
                    await reply_db.commit()
        except Exception as exc:
            logger.error("ai_reply_failed", error=str(exc), exc_info=True)

    background_tasks.add_task(_send_ai_reply)
