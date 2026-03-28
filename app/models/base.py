"""
Shared base mixin for all SQLAlchemy models.

Every model inherits ``UUIDAuditBase`` which provides:
- ``id``: UUID primary key, server-generated.
- ``created_at``: Timestamp set once on INSERT.
- ``updated_at``: Timestamp updated automatically on every UPDATE.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class UUIDAuditBase(Base):
    """Abstract base that every concrete model should inherit from.

    Provides UUID primary key and audit timestamps handled at the database
    level (no application-side datetime manipulation required).
    """

    __abstract__ = True

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
