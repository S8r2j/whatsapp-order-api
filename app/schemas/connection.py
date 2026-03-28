"""Pydantic schemas for social connection APIs."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel
from pydantic import ConfigDict


class SocialConnectionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    shop_id: UUID
    platform: str
    platform_account_id: str
    phone_number_id: str
    display_phone_number: str
    status: str
    token_expires_at: Optional[datetime]
    scopes: Optional[List[str]]
    last_sync_at: Optional[datetime]
    error_message: Optional[str]
    meta: Optional[Dict[str, Any]]
    is_active: bool
    created_at: datetime
    updated_at: datetime


class ConnectMetaResponse(BaseModel):
    oauth_url: str


class ManualConnectRequest(BaseModel):
    """Connect a WhatsApp Business Account manually using credentials from Meta dashboard.
    Used for test/demo accounts that don't appear in the standard OAuth flow.
    """
    phone_number_id: str
    waba_id: str
    display_phone_number: str
    access_token: str
