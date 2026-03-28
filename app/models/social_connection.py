"""ORM model for social platform connections per shop."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Index,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.encryption import EncryptedString
from app.models.base import UUIDAuditBase

if TYPE_CHECKING:
    from app.models.shop import Shop


class SocialConnectionPlatform(str, enum.Enum):
    """Supported social platforms for connections."""

    WHATSAPP = "whatsapp"
    INSTAGRAM = "instagram"
    FACEBOOK = "facebook"
    MESSENGER = "messenger"


class SocialConnectionStatus(str, enum.Enum):
    """Lifecycle status tracked for each connection."""

    CONNECTED = "connected"
    EXPIRED = "expired"
    REVOKED = "revoked"
    ERROR = "error"


class SocialConnection(UUIDAuditBase):
    __tablename__ = "social_connections"
    __table_args__ = (
        UniqueConstraint("shop_id", "platform", name="uq_social_connections_shop_platform"),
        Index("ix_social_connections_shop_id", "shop_id"),
        Index("ix_social_connections_phone_number_id", "phone_number_id"),
    )

    shop_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("shops.id", ondelete="CASCADE"), nullable=False
    )
    platform: Mapped[SocialConnectionPlatform] = mapped_column(
        SAEnum(SocialConnectionPlatform, name="socialconnectionplatform", values_callable=lambda obj: [e.value for e in obj]), nullable=False
    )
    platform_account_id: Mapped[str] = mapped_column(Text, nullable=False)
    phone_number_id: Mapped[str] = mapped_column(Text, nullable=False)
    display_phone_number: Mapped[str] = mapped_column(Text, nullable=False)
    access_token: Mapped[str] = mapped_column(EncryptedString, nullable=False)
    refresh_token: Mapped[str | None] = mapped_column(EncryptedString, nullable=True)
    token_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    scopes: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    status: Mapped[SocialConnectionStatus] = mapped_column(
        SAEnum(SocialConnectionStatus, name="socialconnectionstatus", values_callable=lambda obj: [e.value for e in obj]), nullable=False, default=SocialConnectionStatus.CONNECTED
    )
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    meta: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    shop: Mapped["Shop"] = relationship("Shop", back_populates="social_connections")

    @property
    def is_token_expired(self) -> bool:
        return bool(self.token_expires_at and datetime.utcnow() >= self.token_expires_at)

    @property
    def needs_refresh(self) -> bool:
        if not self.token_expires_at:
            return False
        return datetime.utcnow() + timedelta(days=7) >= self.token_expires_at
