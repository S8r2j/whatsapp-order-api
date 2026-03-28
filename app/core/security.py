"""
JWT token creation/verification and password hashing utilities.

JWT payload structure:
    {
        "sub": "<shop_uuid>",   # subject — the authenticated shop's ID
        "iat": <unix_ts>,       # issued-at timestamp
        "exp": <unix_ts>,       # expiry timestamp
        "jti": "<uuid4>"        # unique token ID (for future revocation support)
    }
"""

from __future__ import annotations

import base64
import hashlib
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict

import bcrypt as _bcrypt
from jose import JWTError, jwt

from app.core.config import settings
from app.core.exceptions import UnauthorizedException
from app.core.logging import get_logger

logger = get_logger(__name__)

# ── Password hashing ──────────────────────────────────────────────────────────

_BCRYPT_ROUNDS = 12


def _pre_hash(password: str) -> bytes:
    """SHA-256 pre-hash so bcrypt never receives more than 44 ASCII bytes.

    bcrypt raises on input beyond 72 bytes. Pre-hashing with SHA-256 + base64
    gives a fixed 44-byte value regardless of input length while preserving
    the full entropy of the original password.
    """
    digest = hashlib.sha256(password.encode("utf-8")).digest()
    return base64.b64encode(digest)


def hash_password(plain_password: str) -> str:
    """Return a bcrypt hash of the given plaintext password (12 rounds)."""
    hashed = _bcrypt.hashpw(_pre_hash(plain_password), _bcrypt.gensalt(rounds=_BCRYPT_ROUNDS))
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Return True if the plain password matches the stored bcrypt hash."""
    return _bcrypt.checkpw(_pre_hash(plain_password), hashed_password.encode("utf-8"))


# ── JWT utilities ─────────────────────────────────────────────────────────────

def create_access_token(
    subject: str,
    expires_delta: timedelta | None = None,
    extra_claims: Dict[str, Any] | None = None,
) -> str:
    """Create a signed JWT access token.

    Args:
        subject: The entity this token represents (typically shop_id as str).
        expires_delta: Override the default expiry window.
        extra_claims: Additional claims to include in the payload.

    Returns:
        A signed JWT string.
    """
    now = datetime.now(tz=timezone.utc)
    expire = now + (
        expires_delta
        if expires_delta is not None
        else timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )

    payload: Dict[str, Any] = {
        "sub": subject,
        "iat": now,
        "exp": expire,
        "jti": str(uuid.uuid4()),  # unique token ID
    }
    if extra_claims:
        payload.update(extra_claims)

    token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    logger.debug("token_created", subject=subject, expires_at=expire.isoformat())
    return token


def decode_access_token(token: str) -> Dict[str, Any]:
    """Decode and validate a JWT access token.

    Args:
        token: The raw JWT string from the Authorization header.

    Returns:
        The decoded payload dictionary.

    Raises:
        UnauthorizedException: If the token is invalid, expired, or missing required claims.
    """
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
    except JWTError as exc:
        logger.warning("token_decode_failed", reason=str(exc))
        raise UnauthorizedException("Invalid or expired token") from exc

    if payload.get("sub") is None:
        logger.warning("token_missing_sub_claim")
        raise UnauthorizedException("Token missing subject claim")

    return payload


def extract_shop_id(token: str) -> str:
    """Convenience wrapper — decode a token and return the shop_id (sub claim).

    Args:
        token: The raw JWT string.

    Returns:
        The shop UUID as a string.

    Raises:
        UnauthorizedException: On any validation failure.
    """
    payload = decode_access_token(token)
    return str(payload["sub"])
