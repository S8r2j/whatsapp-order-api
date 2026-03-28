"""
Custom business-level validation functions.

These go beyond Pydantic schema checks and operate on domain rules
(e.g. valid order status transitions).
"""

from __future__ import annotations

from typing import Optional

# Valid order status values
ORDER_STATUSES = frozenset({"new", "confirmed", "ready", "delivered", "cancelled"})

# Allowed forward progressions — "cancelled" can be reached from any state
STATUS_TRANSITIONS: dict[str, set[str]] = {
    "new":       {"confirmed", "cancelled"},
    "confirmed": {"ready", "cancelled"},
    "ready":     {"delivered", "cancelled"},
    "delivered": set(),       # Terminal state — no further transitions
    "cancelled": set(),       # Terminal state
}


def is_valid_order_status(status: str) -> bool:
    """Return True if the given string is a recognised order status."""
    return status in ORDER_STATUSES


def is_valid_status_transition(current: str, new: str) -> bool:
    """Return True if transitioning from *current* to *new* is allowed.

    Args:
        current: The order's current status.
        new: The requested new status.

    Returns:
        True when the transition is valid, False otherwise.
    """
    allowed = STATUS_TRANSITIONS.get(current, set())
    return new in allowed


def validate_phone_number(phone: Optional[str]) -> Optional[str]:
    """Normalise and minimally validate an E.164 phone number.

    Args:
        phone: The raw phone string (may include spaces, dashes).

    Returns:
        The normalised phone string (leading +, digits only), or None.

    Raises:
        ValueError: If the number is structurally invalid.
    """
    if not phone:
        return None
    cleaned = phone.strip().replace(" ", "").replace("-", "")
    if not cleaned.startswith("+"):
        cleaned = "+" + cleaned
    digits_only = cleaned[1:]
    if not digits_only.isdigit():
        raise ValueError(f"Phone number contains non-digit characters: {phone!r}")
    if not (7 <= len(digits_only) <= 15):
        raise ValueError(f"Phone number length is out of range (7–15 digits): {phone!r}")
    return cleaned
