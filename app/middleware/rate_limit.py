"""
Rate limiting configuration.

The slowapi Limiter is initialised in ``app/main.py`` and registered on the
FastAPI app. This module documents the rate-limit strategy and provides
the shared limiter instance for use in endpoint decorators.

Rate limits applied:
  - POST /api/v1/auth/login    : 10 requests per 15 minutes per IP
  - POST /api/v1/auth/register : 10 requests per 15 minutes per IP
  - All other routes           : 200 requests per minute (global default)
"""

from __future__ import annotations

from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config import settings

# Shared limiter instance — imported by auth endpoint module for decorators
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200/minute"],
)
