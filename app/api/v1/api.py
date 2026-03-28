"""
API v1 router — aggregates all endpoint routers under /api/v1.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.endpoints import auth, connections, conversations, customers, orders, shops, webhook

api_router = APIRouter(prefix="/api/v1")

# ── Public routes (no auth required) ─────────────────────────────────────────
api_router.include_router(auth.router)
api_router.include_router(webhook.router)
api_router.include_router(connections.router)

# ── Protected routes (JWT required via Depends(get_current_shop)) ─────────────
api_router.include_router(conversations.router)
api_router.include_router(orders.router)
api_router.include_router(customers.router)
api_router.include_router(shops.router)
