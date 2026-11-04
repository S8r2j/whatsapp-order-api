"""Security tests for the WhatsApp webhook endpoints."""

from __future__ import annotations

import hashlib
import hmac
import json

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.database import get_async_db
from app.main import app

# A status-update delivery: valid Meta shape, but no messages, so the handler
# returns before touching the database.
STATUS_PAYLOAD = {
    "object": "whatsapp_business_account",
    "entry": [{"changes": [{"value": {"statuses": [{"status": "delivered"}]}}]}],
}


def _sign(body: bytes, secret: str | None = None) -> str:
    key = (secret or settings.META_APP_SECRET).encode()
    return "sha256=" + hmac.new(key, body, hashlib.sha256).hexdigest()


async def _no_db():
    yield None


@pytest.fixture
def client():
    app.dependency_overrides[get_async_db] = _no_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.pop(get_async_db, None)


def test_correctly_signed_delivery_is_accepted(client: TestClient) -> None:
    body = json.dumps(STATUS_PAYLOAD).encode()
    response = client.post(
        "/api/v1/webhook",
        content=body,
        headers={"Content-Type": "application/json", "X-Hub-Signature-256": _sign(body)},
    )
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.parametrize(
    "signature",
    [
        None,  # header missing
        "sha256=" + "0" * 64,  # wrong digest
        "md5=abc",  # wrong scheme
    ],
)
def test_unsigned_or_badly_signed_delivery_is_rejected(
    client: TestClient, signature: str | None
) -> None:
    body = json.dumps(STATUS_PAYLOAD).encode()
    headers = {"Content-Type": "application/json"}
    if signature is not None:
        headers["X-Hub-Signature-256"] = signature
    response = client.post("/api/v1/webhook", content=body, headers=headers)
    assert response.status_code == 403


def test_signature_from_another_secret_is_rejected(client: TestClient) -> None:
    body = json.dumps(STATUS_PAYLOAD).encode()
    response = client.post(
        "/api/v1/webhook",
        content=body,
        headers={"X-Hub-Signature-256": _sign(body, secret="attacker-secret")},
    )
    assert response.status_code == 403


def test_tampered_body_is_rejected(client: TestClient) -> None:
    body = json.dumps(STATUS_PAYLOAD).encode()
    signature = _sign(body)
    tampered = body.replace(b"delivered", b"read")
    response = client.post(
        "/api/v1/webhook", content=tampered, headers={"X-Hub-Signature-256": signature}
    )
    assert response.status_code == 403


def test_empty_verify_token_never_matches(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "WEBHOOK_VERIFY_TOKEN", "")
    response = client.get(
        "/api/v1/webhook",
        params={"hub.mode": "subscribe", "hub.verify_token": "", "hub.challenge": "x"},
    )
    assert response.status_code == 403


def test_debug_endpoint_is_hidden_unless_debug_is_enabled(client: TestClient) -> None:
    assert settings.DEBUG is False
    assert client.get("/api/v1/webhook/debug").status_code == 404


def test_debug_endpoint_is_hidden_in_production_even_with_debug_on(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "DEBUG", True)
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    assert client.get("/api/v1/webhook/debug").status_code == 404
