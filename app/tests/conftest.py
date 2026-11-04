"""Shared pytest configuration.

Settings are read from the environment when ``app.core.config`` is first
imported, so the required variables are set here before any app module loads.
No real database, Redis or Meta credentials are needed: the database engine is
created lazily and the tests below never open a connection.
"""

from __future__ import annotations

import os

from cryptography.fernet import Fernet

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost:5432/test")
os.environ.setdefault("ENCRYPTION_KEY", Fernet.generate_key().decode())
os.environ.setdefault("JWT_SECRET_KEY", "test-jwt-secret-not-for-production")
os.environ.setdefault("META_APP_ID", "test-app-id")
os.environ.setdefault("META_APP_SECRET", "test-app-secret")
os.environ.setdefault("WEBHOOK_VERIFY_TOKEN", "test-verify-token")
os.environ.setdefault("ENVIRONMENT", "test")
