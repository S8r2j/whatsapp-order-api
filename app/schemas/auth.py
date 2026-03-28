"""Authentication-related Pydantic request/response schemas."""

from __future__ import annotations

import uuid
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class RegisterRequest(BaseModel):
    """Request body for POST /api/v1/auth/register."""

    name: str = Field(..., min_length=2, max_length=100, description="Business display name")
    email: EmailStr = Field(..., description="Login email address")
    password: str = Field(..., min_length=8, max_length=128, description="Account password")
    phone_number: Optional[str] = Field(
        None, description="WhatsApp number linked to this shop (E.164 format)"
    )

    @field_validator("phone_number", mode="before")
    @classmethod
    def normalise_phone(cls, v: Optional[str]) -> Optional[str]:
        """Strip whitespace and ensure leading + is present."""
        if v is None:
            return v
        v = v.strip().replace(" ", "").replace("-", "")
        if v and not v.startswith("+"):
            v = "+" + v
        return v or None


class LoginRequest(BaseModel):
    """Request body for POST /api/v1/auth/login."""

    email: EmailStr
    password: str = Field(..., min_length=1)


class ShopResponse(BaseModel):
    """Public shop data included in auth responses."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    email: str
    phone_number: Optional[str] = None
    business_hours: Optional[dict] = None


class TokenResponse(BaseModel):
    """Response body for successful login / register."""

    access_token: str
    token_type: str = "bearer"
    shop: ShopResponse


class RefreshRequest(BaseModel):
    """Request body for POST /api/v1/auth/refresh."""

    token: str
