"""Shop profile Pydantic schemas."""

from __future__ import annotations

import uuid
from typing import Dict, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class ShopProfileResponse(BaseModel):
    """Full shop profile returned by GET /api/v1/shop/profile."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    email: str
    phone_number: Optional[str] = None
    business_hours: Optional[Dict[str, str]] = None
    is_active: bool


class UpdateShopProfileRequest(BaseModel):
    """Request body for PATCH /api/v1/shop/profile."""

    name: Optional[str] = Field(None, min_length=2, max_length=100)
    phone_number: Optional[str] = Field(None)

    @field_validator("phone_number", mode="before")
    @classmethod
    def normalise_phone(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        v = v.strip().replace(" ", "").replace("-", "")
        return ("+" + v) if v and not v.startswith("+") else v or None


class UpdateBusinessHoursRequest(BaseModel):
    """Request body for PATCH /api/v1/shop/hours.

    Hours are stored as ``{ "mon": "09:00-18:00", "tue": "closed", ... }``.
    """

    hours: Dict[str, str] = Field(
        ...,
        description='Map of weekday abbreviation to hours string. e.g. {"mon": "09:00-18:00"}',
    )

    @field_validator("hours")
    @classmethod
    def validate_days(cls, v: Dict[str, str]) -> Dict[str, str]:
        valid_days = {"mon", "tue", "wed", "thu", "fri", "sat", "sun"}
        for day in v:
            if day.lower() not in valid_days:
                raise ValueError(f"Invalid day key: '{day}'. Must be one of {valid_days}")
        return {k.lower(): val for k, val in v.items()}
