"""Initial schema — shops, customers, orders, messages

Revision ID: 0001
Revises:
Create Date: 2026-03-18 00:00:00.000000

Creates all four core tables with:
- UUID primary keys (PostgreSQL native uuid type)
- Encrypted TEXT columns for sensitive fields
- Hash index columns for fast lookups on encrypted fields
- Foreign keys with CASCADE deletes
- Composite and single-column indexes for common query patterns
- Timestamps with server-side defaults
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers
revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── shops ──────────────────────────────────────────────────────────────────
    op.create_table(
        "shops",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("name", sa.Text(), nullable=False, comment="Encrypted business display name"),
        sa.Column("email", sa.Text(), nullable=False, comment="Encrypted login email"),
        sa.Column("phone_number", sa.Text(), nullable=True, comment="Encrypted WhatsApp number"),
        sa.Column("email_hash", sa.Text(), nullable=False, comment="SHA-256 of normalised email for fast lookup"),
        sa.Column("phone_hash", sa.Text(), nullable=True, comment="SHA-256 of normalised phone for fast lookup"),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("business_hours", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email_hash"),
        sa.UniqueConstraint("phone_hash"),
    )
    op.create_index("ix_shops_email_hash", "shops", ["email_hash"])
    op.create_index("ix_shops_phone_hash", "shops", ["phone_hash"])

    # ── customers ──────────────────────────────────────────────────────────────
    op.create_table(
        "customers",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("shop_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("phone_number", sa.Text(), nullable=False, comment="Encrypted phone number"),
        sa.Column("name", sa.Text(), nullable=True, comment="Encrypted display name"),
        sa.Column("phone_hash", sa.Text(), nullable=False, comment="SHA-256 for O(1) lookup"),
        sa.Column("total_orders", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["shop_id"], ["shops.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_customers_shop_id", "customers", ["shop_id"])
    op.create_index("ix_customers_phone_hash", "customers", ["phone_hash"])
    op.create_index("ix_customers_shop_phone", "customers", ["shop_id", "phone_hash"])

    # ── orders ─────────────────────────────────────────────────────────────────
    op.create_table(
        "orders",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("shop_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("raw_message", sa.Text(), nullable=False, comment="Encrypted original message"),
        sa.Column("items", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("status", sa.Text(), server_default=sa.text("'new'"), nullable=False),
        sa.Column("total_amount", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True, comment="Encrypted internal notes"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["shop_id"], ["shops.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_orders_shop_id", "orders", ["shop_id"])
    op.create_index("ix_orders_customer_id", "orders", ["customer_id"])
    op.create_index("ix_orders_status", "orders", ["status"])
    op.create_index("ix_orders_shop_status", "orders", ["shop_id", "status"])
    op.create_index("ix_orders_created_at", "orders", ["created_at"])

    # ── messages ───────────────────────────────────────────────────────────────
    op.create_table(
        "messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("shop_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("order_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("direction", sa.Text(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False, comment="Encrypted message body"),
        sa.Column("wa_message_id", sa.Text(), nullable=True, comment="Meta message ID for deduplication"),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["shop_id"], ["shops.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("wa_message_id"),
    )
    op.create_index("ix_messages_shop_id", "messages", ["shop_id"])
    op.create_index("ix_messages_customer_id", "messages", ["customer_id"])
    op.create_index("ix_messages_order_id", "messages", ["order_id"])
    op.create_index("ix_messages_wa_message_id", "messages", ["wa_message_id"])


def downgrade() -> None:
    op.drop_table("messages")
    op.drop_table("orders")
    op.drop_table("customers")
    op.drop_table("shops")
