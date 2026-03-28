"""
Customer model — a WhatsApp contact who has placed orders with a shop.

phone_number and name are encrypted at rest. phone_hash provides fast
O(1) lookup when processing inbound webhook messages.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.encryption import EncryptedString
from app.models.base import UUIDAuditBase

if TYPE_CHECKING:
    from app.models.shop import Shop
    from app.models.order import Order
    from app.models.message import Message


class Customer(UUIDAuditBase):
    """A customer contact known to a specific shop."""

    __tablename__ = "customers"

    # ── Foreign key ─────────────────────────────────────────────────────────
    shop_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("shops.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ── Encrypted fields ─────────────────────────────────────────────────────
    phone_number: Mapped[str] = mapped_column(EncryptedString, nullable=False)
    name: Mapped[Optional[str]] = mapped_column(EncryptedString, nullable=True)

    # ── Hash index (SHA-256 of normalised phone_number) ───────────────────────
    phone_hash: Mapped[str] = mapped_column(Text, nullable=False, index=True)

    # ── Counters ─────────────────────────────────────────────────────────────
    total_orders: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # ── Relationships ─────────────────────────────────────────────────────────
    shop: Mapped["Shop"] = relationship("Shop", back_populates="customers")
    orders: Mapped[List["Order"]] = relationship(
        "Order", back_populates="customer", cascade="all, delete-orphan"
    )
    messages: Mapped[List["Message"]] = relationship(
        "Message", back_populates="customer", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Customer id={self.id} shop_id={self.shop_id}>"
