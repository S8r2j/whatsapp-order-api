"""Add social connections table for multi-tenant WhatsApp OAuth."""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers
revision: str = "0002_add_social_connections"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create enum types — checkfirst=True skips creation if they already exist.
    postgresql.ENUM(
        "whatsapp", "instagram", "facebook", "messenger",
        name="socialconnectionplatform",
    ).create(op.get_bind(), checkfirst=True)

    postgresql.ENUM(
        "connected", "expired", "revoked", "error",
        name="socialconnectionstatus",
    ).create(op.get_bind(), checkfirst=True)

    # create_type=False prevents create_table from trying to recreate the enums.
    social_connection_platform = postgresql.ENUM(
        "whatsapp", "instagram", "facebook", "messenger",
        name="socialconnectionplatform",
        create_type=False,
    )
    social_connection_status = postgresql.ENUM(
        "connected", "expired", "revoked", "error",
        name="socialconnectionstatus",
        create_type=False,
    )

    op.create_table(
        "social_connections",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("shop_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("platform", social_connection_platform, nullable=False),
        sa.Column("platform_account_id", sa.Text(), nullable=False),
        sa.Column("phone_number_id", sa.Text(), nullable=False),
        sa.Column("display_phone_number", sa.Text(), nullable=False),
        sa.Column("access_token", sa.Text(), nullable=False),
        sa.Column("refresh_token", sa.Text(), nullable=True),
        sa.Column("token_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("scopes", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("status", social_connection_status, nullable=False, server_default=sa.text("'connected'")),
        sa.Column("last_sync_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("meta", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.ForeignKeyConstraint(["shop_id"], ["shops.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index("ix_social_connections_shop_id", "social_connections", ["shop_id"])
    op.create_index("ix_social_connections_phone_number_id", "social_connections", ["phone_number_id"])
    op.create_index(
        "uq_social_connections_shop_platform",
        "social_connections",
        ["shop_id", "platform"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("uq_social_connections_shop_platform", table_name="social_connections")
    op.drop_index("ix_social_connections_phone_number_id", table_name="social_connections")
    op.drop_index("ix_social_connections_shop_id", table_name="social_connections")
    op.drop_table("social_connections")
    postgresql.ENUM(name="socialconnectionstatus").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="socialconnectionplatform").drop(op.get_bind(), checkfirst=True)
