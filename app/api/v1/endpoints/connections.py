"""Endpoints for managing social connections and OAuth callbacks."""

from __future__ import annotations

from typing import List
from urllib.parse import urlencode
import uuid

from fastapi import APIRouter, Depends, Query, Response
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_shop
from app.core.config import settings
from app.core.database import get_async_db
from app.core.logging import get_logger
from app.core.exceptions import AppException, NotFoundException
from app.models.shop import Shop
from app.repositories import social_connection_repo
from app.schemas.connection import ConnectMetaResponse, ManualConnectRequest, SocialConnectionResponse
from app.models.social_connection import SocialConnectionPlatform, SocialConnectionStatus
from app.services.meta_oauth_service import meta_oauth_service
from app.services.social_connection_service import social_connection_service

logger = get_logger(__name__)

router = APIRouter(tags=["Connections"])


def _settings_redirect_url(status: str, reason: str | None = None) -> str:
    params = [("connection", status)]
    if reason:
        params.append(("reason", reason))
    query = urlencode(params)
    return f"{settings.FRONTEND_URL}/dashboard/settings?{query}" if query else settings.FRONTEND_URL


@router.get(
    "/connections",
    response_model=List[SocialConnectionResponse],
    summary="List social connections",
)
async def list_connections(
    current_shop: Shop = Depends(get_current_shop),
    db: AsyncSession = Depends(get_async_db),
) -> List[SocialConnectionResponse]:
    connections = await social_connection_service.list_connections(db, current_shop.id)
    return [SocialConnectionResponse.model_validate(conn) for conn in connections]


@router.get(
    "/connections/{connection_id}",
    response_model=SocialConnectionResponse,
    summary="Get a social connection",
)
async def get_connection(
    connection_id: uuid.UUID,
    current_shop: Shop = Depends(get_current_shop),
    db: AsyncSession = Depends(get_async_db),
) -> SocialConnectionResponse:
    connection = await social_connection_repo.get(db, connection_id)
    if not connection or connection.shop_id != current_shop.id:
        raise NotFoundException("Connection not found")
    return SocialConnectionResponse.model_validate(connection)


@router.delete(
    "/connections/{connection_id}",
    summary="Disconnect a connection",
    status_code=204,
)
async def delete_connection(
    connection_id: uuid.UUID,
    current_shop: Shop = Depends(get_current_shop),
    db: AsyncSession = Depends(get_async_db),
) -> Response:
    await social_connection_service.disconnect(db, current_shop.id, connection_id)
    return Response(status_code=204)


@router.get(
    "/auth/meta/connect",
    response_model=ConnectMetaResponse,
    summary="Generate Meta OAuth URL",
)
async def connect_meta(
    current_shop: Shop = Depends(get_current_shop),
) -> ConnectMetaResponse:
    url = await meta_oauth_service.generate_authorization_url(current_shop.id)
    return ConnectMetaResponse(oauth_url=url)


@router.get(
    "/auth/meta/callback",
    summary="Handle Meta OAuth callback",
)
async def meta_callback(
    code: str | None = Query(None),
    state: str | None = Query(None),
    error: str | None = Query(None),
    db: AsyncSession = Depends(get_async_db),
) -> RedirectResponse:
    if error:
        return RedirectResponse(_settings_redirect_url("error", error))

    if not code or not state:
        return RedirectResponse(_settings_redirect_url("error", "missing_code_or_state"))

    try:
        shop_id = await meta_oauth_service.validate_state(state)
        await social_connection_service.connect_whatsapp(db, shop_id, code, state)
        return RedirectResponse(_settings_redirect_url("success"))
    except AppException as exc:
        logger.warning("meta_callback_failed", error=str(exc))
        return RedirectResponse(_settings_redirect_url("error", str(exc)))
    except Exception as exc:  # pragma: no cover - best-effort
        import traceback
        logger.error("meta_callback_unexpected", error=str(exc), trace=traceback.format_exc())
        reason = str(exc) if settings.ENVIRONMENT == "development" else "unexpected_error"
        return RedirectResponse(_settings_redirect_url("error", reason))


@router.post(
    "/connections/manual",
    response_model=SocialConnectionResponse,
    summary="Manually connect a WhatsApp Business Account",
    description="Use this for Meta test/demo accounts that don't appear in standard OAuth. "
                "Provide the Phone Number ID, WABA ID, and access token from Meta dashboard.",
)
async def manual_connect(
    body: ManualConnectRequest,
    current_shop: Shop = Depends(get_current_shop),
    db: AsyncSession = Depends(get_async_db),
) -> SocialConnectionResponse:
    from datetime import datetime

    existing = await social_connection_repo.get_by_shop_and_platform(
        db, current_shop.id, SocialConnectionPlatform.WHATSAPP
    )

    data = {
        "access_token": body.access_token,
        "phone_number_id": body.phone_number_id,
        "display_phone_number": body.display_phone_number,
        "platform_account_id": body.waba_id,
        "status": SocialConnectionStatus.CONNECTED,
        "is_active": True,
        "last_sync_at": datetime.utcnow(),
        "error_message": None,
    }

    if existing:
        connection = await social_connection_repo.update(db, db_obj=existing, updates=data)
    else:
        connection = await social_connection_repo.create(db, obj_in={
            "shop_id": current_shop.id,
            "platform": SocialConnectionPlatform.WHATSAPP,
            **data,
        })

    logger.info("manual_connection_saved", shop_id=str(current_shop.id), phone_number_id=body.phone_number_id)
    return SocialConnectionResponse.model_validate(connection)
