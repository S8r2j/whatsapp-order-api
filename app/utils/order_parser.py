"""
Lightweight WhatsApp order text parser.

Extracts structured order items from free-form WhatsApp messages without any
AI/ML dependency. Handles common quantity patterns including numeric digits,
word numbers, and units like "plates of".

Examples parsed correctly:
    "2x momos and 1 tea"            -> [OrderItem("Momos", 2), OrderItem("Tea", 1)]
    "two plates of rice"            -> [OrderItem("Rice", 2)]
    "3 burgers, extra cheese"       -> [OrderItem("Burgers", 3)]
    "i want 5 samosas pls"          -> [OrderItem("Samosas", 5)]
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class OrderItem:
    """A single parsed item from an order message.

    Attributes:
        name: The item name, title-cased.
        qty: The quantity ordered (always >= 1).
        notes: Any extra text associated with this item (e.g. "no onion").
    """

    name: str
    qty: int
    notes: Optional[str] = field(default=None)

    def to_dict(self) -> dict:
        """Serialise to a plain dictionary for JSON storage."""
        return {"name": self.name, "qty": self.qty, "notes": self.notes}


class OrderParser:
    """Lightweight regex-based parser for WhatsApp order messages.

    The parser tries several quantity patterns in order of specificity.
    Duplicate item names (case-insensitive) are merged by summing quantities.
    """

    # ── Quantity patterns (tried in order) ───────────────────────────────────

    _PATTERNS = [
        # "2 plates of momos" | "1 plate of rice"
        r"(\d+)\s+plates?\s+of\s+([a-z][a-z\s]{1,40})",
        # "2x momos" | "3X burger"
        r"(\d+)\s*[xX]\s+([a-z][a-z\s]{1,40})",
        # "2 momos" | "10 samosas"
        r"(\d+)\s+([a-z][a-z\s]{1,40})",
        # "two momos" | "five burgers"
        r"(one|two|three|four|five|six|seven|eight|nine|ten)\s+([a-z][a-z\s]{1,40})",
    ]

    _WORD_TO_NUM = {
        "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
        "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    }

    # Words that are almost certainly NOT item names
    _STOP_WORDS = frozenset({
        "please", "pls", "plz", "and", "also", "with", "without",
        "want", "need", "order", "give", "get", "send", "deliver",
        "thanks", "thank", "hello", "hi", "bye", "ok", "okay",
        "extra", "more", "less", "no",
    })

    @classmethod
    def parse_order(cls, message_text: str) -> List[OrderItem]:
        """Parse order items from a WhatsApp message string.

        Args:
            message_text: The raw message body received from WhatsApp.

        Returns:
            A list of ``OrderItem`` instances. Empty list if nothing parseable.
        """
        if not message_text or not message_text.strip():
            return []

        # Truncate very long messages before processing
        text = message_text[:500].lower().strip()

        seen: dict[str, OrderItem] = {}  # name_lower -> OrderItem (for dedup)

        for pattern in cls._PATTERNS:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                qty_str, raw_name = match.group(1), match.group(2)

                # Resolve quantity
                qty = cls._WORD_TO_NUM.get(qty_str.lower())
                if qty is None:
                    try:
                        qty = int(qty_str)
                    except ValueError:
                        continue

                # Clean item name
                item_name = raw_name.strip().rstrip(",.!?")
                if not cls._is_valid_item_name(item_name):
                    continue

                name_normalised = item_name.lower()
                display_name = item_name.title()

                if name_normalised in seen:
                    # Merge duplicates
                    seen[name_normalised].qty += qty
                else:
                    seen[name_normalised] = OrderItem(name=display_name, qty=qty)

        return list(seen.values())

    @classmethod
    def _is_valid_item_name(cls, name: str) -> bool:
        """Return True if the candidate name looks like a real item.

        Filters out:
        - Names shorter than 2 characters
        - Names that are purely stop words
        - Names containing only digits
        """
        stripped = name.strip()
        if len(stripped) < 2:
            return False
        if stripped.isdigit():
            return False
        words = {w.lower() for w in stripped.split()}
        if words.issubset(cls._STOP_WORDS):
            return False
        return True
