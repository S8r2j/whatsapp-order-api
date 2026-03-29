"""
Application configuration loaded from environment variables.

All settings are validated at startup via Pydantic Settings.
Missing required variables will raise a clear error before the app starts.
"""

from __future__ import annotations

from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central application configuration sourced from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ────────────────────────────────────────────────────────────
    APP_NAME: str = "WhatsApp Order Manager"
    ENVIRONMENT: str = "development"
    DEBUG: bool = False

    # ── Database ───────────────────────────────────────────────────────────────
    DATABASE_URL: str  # e.g. postgresql+asyncpg://user:pass@host:5432/db

    # ── Security / Encryption ──────────────────────────────────────────────────
    ENCRYPTION_KEY: str        # Fernet key — generate with scripts/generate_encryption_key.py
    JWT_SECRET_KEY: str        # Random 64-char hex string
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 10080  # 7 days

    # ── Meta App Credentials (requires Business app + WhatsApp product) ─────────
    META_APP_ID: str
    META_APP_SECRET: str

    # ── OAuth URLs ─────────────────────────────────────────────────────────────
    FRONTEND_URL: str = "http://localhost:5173"
    BACKEND_URL: str = "http://localhost:8000"

    # ── WhatsApp / Meta Cloud API ───────────────────────────────────────────────
    WEBHOOK_VERIFY_TOKEN: str = ""
    WHATSAPP_API_VERSION: str = "v18.0"

    # ── OAuth state token expiry ────────────────────────────────────────────────
    OAUTH_STATE_EXPIRE_MINUTES: int = 10
    # ── Redis / Celery ─────────────────────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/1"

    # ── CORS ───────────────────────────────────────────────────────────────────
    # Stored as a plain string so pydantic-settings v2 never attempts JSON
    # parsing on it. Use the `cors_origins` property everywhere in the app.
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:5173"

    # ── Rate Limiting ──────────────────────────────────────────────────────────
    RATE_LIMIT_LOGIN: str = "10/15minutes"

    # ── Error Monitoring ───────────────────────────────────────────────────────
    SENTRY_DSN: str = ""

    @property
    def cors_origins(self) -> List[str]:
        """Return the CORS origins as a list, split on commas."""
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        """Return True when running in production environment."""
        return self.ENVIRONMENT.lower() == "production"

    @property
    def oauth_redirect_uri(self) -> str:
        """Return the fully qualified redirect URI Meta should call after OAuth."""
        return f"{self.BACKEND_URL}/api/v1/auth/meta/callback"


@lru_cache
def get_settings() -> Settings:
    """Return a cached singleton Settings instance."""
    return Settings()


# Module-level singleton for convenience imports
settings = get_settings()
