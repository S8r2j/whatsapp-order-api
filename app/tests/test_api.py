"""HTTP-level tests that need no database: health checks, webhook
verification, and authentication enforcement on protected routes."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app


@pytest.fixture(scope="module")
def client() -> TestClient:
    with TestClient(app) as test_client:
        yield test_client


def test_health_check(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_root(client: TestClient) -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_responses_carry_a_request_id(client: TestClient) -> None:
    response = client.get("/health")
    assert any(header.lower() == "x-request-id" for header in response.headers)


def test_webhook_verification_echoes_challenge_with_correct_token(client: TestClient) -> None:
    response = client.get(
        "/api/v1/webhook",
        params={
            "hub.mode": "subscribe",
            "hub.verify_token": settings.WEBHOOK_VERIFY_TOKEN,
            "hub.challenge": "challenge-123",
        },
    )
    assert response.status_code == 200
    assert response.text == "challenge-123"


@pytest.mark.parametrize(
    "params",
    [
        {"hub.mode": "subscribe", "hub.verify_token": "wrong", "hub.challenge": "x"},
        {"hub.mode": "unsubscribe", "hub.verify_token": "test-verify-token", "hub.challenge": "x"},
        {},
    ],
)
def test_webhook_verification_rejects_bad_requests(client: TestClient, params: dict) -> None:
    response = client.get("/api/v1/webhook", params=params)
    assert response.status_code == 403


def test_orders_require_authentication(client: TestClient) -> None:
    response = client.get("/api/v1/orders")
    assert response.status_code in (401, 403)


def test_orders_reject_an_invalid_token(client: TestClient) -> None:
    response = client.get("/api/v1/orders", headers={"Authorization": "Bearer not-a-jwt"})
    assert response.status_code == 401
