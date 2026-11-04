"""Tests for order-status rules and phone-number validation."""

from __future__ import annotations

import pytest

from app.utils.validators import (
    ORDER_STATUSES,
    is_valid_order_status,
    is_valid_status_transition,
    validate_phone_number,
)


@pytest.mark.parametrize("status", sorted(ORDER_STATUSES))
def test_known_statuses_are_valid(status: str) -> None:
    assert is_valid_order_status(status)


def test_unknown_status_is_invalid() -> None:
    assert not is_valid_order_status("shipped")


@pytest.mark.parametrize(
    ("current", "new"),
    [
        ("new", "confirmed"),
        ("confirmed", "ready"),
        ("ready", "delivered"),
        ("new", "cancelled"),
        ("ready", "cancelled"),
    ],
)
def test_allowed_transitions(current: str, new: str) -> None:
    assert is_valid_status_transition(current, new)


@pytest.mark.parametrize(
    ("current", "new"),
    [
        ("new", "delivered"),  # cannot skip steps
        ("confirmed", "new"),  # cannot go backwards
        ("delivered", "cancelled"),  # terminal state
        ("cancelled", "new"),  # terminal state
        ("unknown", "new"),  # unknown starting state
    ],
)
def test_disallowed_transitions(current: str, new: str) -> None:
    assert not is_valid_status_transition(current, new)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("+977 9812345678", "+9779812345678"),
        ("977-981-234-5678", "+9779812345678"),
        ("+14155552671", "+14155552671"),
    ],
)
def test_phone_numbers_are_normalised(raw: str, expected: str) -> None:
    assert validate_phone_number(raw) == expected


@pytest.mark.parametrize("raw", [None, ""])
def test_empty_phone_returns_none(raw: str | None) -> None:
    assert validate_phone_number(raw) is None


@pytest.mark.parametrize("raw", ["+97798abc5678", "+12345", "+1234567890123456"])
def test_invalid_phone_numbers_raise(raw: str) -> None:
    with pytest.raises(ValueError):
        validate_phone_number(raw)
