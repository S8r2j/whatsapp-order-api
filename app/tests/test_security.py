"""Tests for password hashing and JWT handling."""

from __future__ import annotations

from datetime import timedelta

import pytest
from jose import jwt

from app.core.config import settings
from app.core.exceptions import UnauthorizedException
from app.core.security import (
    create_access_token,
    decode_access_token,
    extract_shop_id,
    hash_password,
    verify_password,
)


def test_password_round_trip() -> None:
    hashed = hash_password("correct horse battery staple")
    assert hashed != "correct horse battery staple"
    assert verify_password("correct horse battery staple", hashed)
    assert not verify_password("wrong password", hashed)


def test_passwords_longer_than_bcrypt_limit_are_supported() -> None:
    long_password = "a" * 200
    hashed = hash_password(long_password)
    assert verify_password(long_password, hashed)
    # A different password sharing the first 72 bytes must not match.
    assert not verify_password("a" * 72, hashed)


def test_same_password_hashes_differently_each_time() -> None:
    assert hash_password("secret") != hash_password("secret")


def test_token_round_trip_returns_subject_and_claims() -> None:
    token = create_access_token("shop-123", extra_claims={"role": "owner"})
    payload = decode_access_token(token)
    assert payload["sub"] == "shop-123"
    assert payload["role"] == "owner"
    assert "jti" in payload
    assert extract_shop_id(token) == "shop-123"


def test_each_token_gets_a_unique_id() -> None:
    first = decode_access_token(create_access_token("shop-123"))
    second = decode_access_token(create_access_token("shop-123"))
    assert first["jti"] != second["jti"]


def test_expired_token_is_rejected() -> None:
    token = create_access_token("shop-123", expires_delta=timedelta(seconds=-1))
    with pytest.raises(UnauthorizedException):
        decode_access_token(token)


def test_token_signed_with_another_key_is_rejected() -> None:
    forged = jwt.encode({"sub": "shop-123"}, "attacker-key", algorithm=settings.JWT_ALGORITHM)
    with pytest.raises(UnauthorizedException):
        decode_access_token(forged)


def test_token_without_subject_is_rejected() -> None:
    token = jwt.encode({"role": "owner"}, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    with pytest.raises(UnauthorizedException):
        decode_access_token(token)


def test_garbage_token_is_rejected() -> None:
    with pytest.raises(UnauthorizedException):
        decode_access_token("not-a-jwt")
