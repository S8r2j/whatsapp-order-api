"""Tests for field-level encryption and lookup hashing."""

from __future__ import annotations

import pytest
from cryptography.fernet import Fernet

from app.core import encryption
from app.core.encryption import EncryptedString, decrypt, encrypt, hash_for_lookup


def test_encrypt_round_trip() -> None:
    ciphertext = encrypt("+9779812345678")
    assert ciphertext != "+9779812345678"
    assert decrypt(ciphertext) == "+9779812345678"


def test_encryption_is_non_deterministic() -> None:
    assert encrypt("same value") != encrypt("same value")


def test_tampered_ciphertext_raises_value_error() -> None:
    ciphertext = encrypt("secret")
    tampered = ciphertext[:-4] + ("AAAA" if not ciphertext.endswith("AAAA") else "BBBB")
    with pytest.raises(ValueError):
        decrypt(tampered)


def test_ciphertext_from_another_key_raises_value_error() -> None:
    foreign = Fernet(Fernet.generate_key()).encrypt(b"secret").decode()
    with pytest.raises(ValueError):
        decrypt(foreign)


def test_lookup_hash_is_normalised_and_deterministic() -> None:
    assert hash_for_lookup("  Shop@Example.com ") == hash_for_lookup("shop@example.com")
    assert len(hash_for_lookup("value")) == 64


def test_lookup_hash_differs_for_different_values() -> None:
    assert hash_for_lookup("+9779812345678") != hash_for_lookup("+9779812345679")


def test_encrypted_column_type_round_trips_and_passes_none_through() -> None:
    column = EncryptedString()
    stored = column.process_bind_param("Ram Bahadur", dialect=None)
    assert stored is not None and stored != "Ram Bahadur"
    assert column.process_result_value(stored, dialect=None) == "Ram Bahadur"
    assert column.process_bind_param(None, dialect=None) is None
    assert column.process_result_value(None, dialect=None) is None


def test_missing_encryption_key_fails_loudly(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(encryption, "_fernet", None)
    monkeypatch.setattr(encryption.settings, "ENCRYPTION_KEY", "")
    with pytest.raises(RuntimeError):
        encrypt("anything")
