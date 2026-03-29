"""
Message model — a log of every inbound and outbound WhatsApp message.

body is encrypted at rest.
wa_message_id is the unique ID assigned by Meta and is used for deduplication.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.encryption import EncryptedString
from app.models.base import UUIDAuditBase

if TYPE_CHECKING:
    from app.models.shop import Shop
    from app.models.customer import Customer
    from app.models.order import Order


class Message(UUIDAuditBase):
    """A single WhatsApp message, either received from or sent to a customer."""

    __tablename__ = "messages"

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
    order_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("orders.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # ── Encrypted fields ──────────────────────────────────────────────────────
    body: Mapped[str] = mapped_column(EncryptedString, nullable=False)

    # ── Non-sensitive fields ──────────────────────────────────────────────────
    direction: Mapped[str] = mapped_column(Text, nullable=False)   # inbound | outbound
    wa_message_id: Mapped[Optional[str]] = mapped_column(
        Text, unique=True, nullable=True, index=True
    )
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # ── Relationships ─────────────────────────────────────────────────────────
    shop: Mapped["Shop"] = relationship("Shop", back_populates="messages")
    customer: Mapped["Customer"] = relationship("Customer", back_populates="messages")
    order: Mapped[Optional["Order"]] = relationship("Order", back_populates="messages")

    def __repr__(self) -> str:
        return f"<Message id={self.id} direction={self.direction}>"
