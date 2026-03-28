"""
Order model — a structured order captured from an inbound WhatsApp message.

raw_message and notes are encrypted at rest.
items is stored as JSONB (structured, non-sensitive data).
status follows the lifecycle: new → confirmed → ready → delivered | cancelled.
"""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import ForeignKey, Numeric, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.encryption import EncryptedString
from app.models.base import UUIDAuditBase

if TYPE_CHECKING:
    from app.models.shop import Shop
    from app.models.customer import Customer
    from app.models.message import Message

# Valid order statuses in progression order
ORDER_STATUSES = ("new", "confirmed", "ready", "delivered", "cancelled")


class Order(UUIDAuditBase):
    """An order received via WhatsApp and managed through the dashboard."""

    __tablename__ = "orders"

    # ── Foreign keys ──────────────────────────────────────────────────────────
    shop_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("shops.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("customers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ── Encrypted fields ──────────────────────────────────────────────────────
    raw_message: Mapped[str] = mapped_column(EncryptedString, nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(EncryptedString, nullable=True)

    # ── Structured / non-sensitive fields ─────────────────────────────────────
    items: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True, default=list)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="new", index=True)
    total_amount: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(precision=10, scale=2), nullable=True
    )

    # ── Relationships ─────────────────────────────────────────────────────────
    shop: Mapped["Shop"] = relationship("Shop", back_populates="orders")
    customer: Mapped["Customer"] = relationship("Customer", back_populates="orders")
    messages: Mapped[List["Message"]] = relationship(
        "Message", back_populates="order", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Order id={self.id} status={self.status}>"
