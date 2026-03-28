"""
Field-level encryption utilities using Fernet symmetric encryption.

All sensitive database columns (phone numbers, names, message bodies, emails)
use the EncryptedString SQLAlchemy TypeDecorator, which transparently encrypts
on write and decrypts on read.

A SHA-256 hash index is stored alongside encrypted phone numbers to allow
O(1) lookups without decrypting every row.

Key management:
- The ENCRYPTION_KEY env var must be a valid Fernet key.
- Generate one with: python scripts/generate_encryption_key.py
- The key is loaded once at module import and never logged.
"""

from __future__ import annotations

import hashlib
from typing import Any, Optional

from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy import Text, TypeDecorator

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# ── Fernet instance (loaded once, never re-created) ───────────────────────────

_fernet: Optional[Fernet] = None


def _get_fernet() -> Fernet:
    """Return the module-level Fernet instance, initialising on first call."""
    global _fernet
    if _fernet is None:
        key = settings.ENCRYPTION_KEY
        if not key:
            raise RuntimeError(
                "ENCRYPTION_KEY is not set. "
                "Run `python scripts/generate_encryption_key.py` to generate one."
            )
        _fernet = Fernet(key.encode())
    return _fernet


# ── Low-level helpers ─────────────────────────────────────────────────────────

def encrypt(value: str) -> str:
    """Encrypt a plaintext string and return the ciphertext as a UTF-8 string."""
    return _get_fernet().encrypt(value.encode()).decode()


def decrypt(value: str) -> str:
    """Decrypt a Fernet ciphertext string and return the plaintext.

    Raises:
        ValueError: When the ciphertext is invalid or the key has changed.
    """
    try:
        return _get_fernet().decrypt(value.encode()).decode()
    except InvalidToken as exc:
        logger.error("decryption_failed", reason="InvalidToken")
        raise ValueError("Failed to decrypt field — key mismatch or corrupted data") from exc


def hash_for_lookup(value: str) -> str:
    """Return a deterministic SHA-256 hex digest of the normalised value.

    Used as a fast equality-lookup index alongside encrypted columns so we
    never have to decrypt every row to find a match.

    The value is lowercased and stripped before hashing for consistency.
    """
    normalised = value.strip().lower()
    return hashlib.sha256(normalised.encode()).hexdigest()


# ── SQLAlchemy TypeDecorator ───────────────────────────────────────────────────

class EncryptedString(TypeDecorator):
    """SQLAlchemy column type that transparently encrypts on write and decrypts
    on read using Fernet symmetric encryption.

    Usage in a model::

        class Customer(Base):
            phone_number: Mapped[str] = mapped_column(EncryptedString)
    """

    impl = Text
    cache_ok = True

    def process_bind_param(self, value: Any, dialect: Any) -> Optional[str]:
        """Encrypt the value before it is written to the database."""
        if value is not None:
            return encrypt(str(value))
        return None

    def process_result_value(self, value: Any, dialect: Any) -> Optional[str]:
        """Decrypt the value after it is read from the database."""
        if value is not None:
            return decrypt(value)
        return None
