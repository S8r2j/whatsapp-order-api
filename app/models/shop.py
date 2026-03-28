"""
Shop model — represents a registered business using the platform.

Sensitive columns (name, phone_number, email) are encrypted at rest using the
EncryptedString TypeDecorator. The ``email_hash`` and ``phone_hash`` columns
store SHA-256 digests of the normalised plaintext values for fast lookups
without decrypting every row.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Boolean, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.encryption import EncryptedString
from app.models.base import UUIDAuditBase

if TYPE_CHECKING:
    from app.models.customer import Customer
    from app.models.message import Message
    from app.models.order import Order
    from app.models.social_connection import SocialConnection


class Shop(UUIDAuditBase):
    """A shop (tenant) that owns customers, orders, and messages."""

    __tablename__ = "shops"

    # ── Encrypted fields ────────────────────────────────────────────────────
    name: Mapped[str] = mapped_column(EncryptedString, nullable=False)
    email: Mapped[str] = mapped_column(EncryptedString, nullable=False)
    phone_number: Mapped[Optional[str]] = mapped_column(EncryptedString, nullable=True)

    # ── Hash indexes for fast lookups (SHA-256 of normalised plaintext) ─────
    email_hash: Mapped[str] = mapped_column(Text, unique=True, nullable=False, index=True)
    phone_hash: Mapped[Optional[str]] = mapped_column(Text, unique=True, nullable=True, index=True)

    # ── Non-sensitive fields ────────────────────────────────────────────────
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    business_hours: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # ── Relationships ───────────────────────────────────────────────────────
    customers: Mapped[List["Customer"]] = relationship(
        "Customer", back_populates="shop", cascade="all, delete-orphan"
    )
    orders: Mapped[List["Order"]] = relationship(
        "Order", back_populates="shop", cascade="all, delete-orphan"
    )
    messages: Mapped[List["Message"]] = relationship(
        "Message", back_populates="shop", cascade="all, delete-orphan"
    )
    social_connections: Mapped[List["SocialConnection"]] = relationship(
        "SocialConnection",
        back_populates="shop",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Shop id={self.id}>"
