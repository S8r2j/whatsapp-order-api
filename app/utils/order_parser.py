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

    The message is split into segments on separators ("," "and" "&" new lines
    and similar), and each segment is scanned once with a single pattern, so
    overlapping matches can no longer count the same item twice. An item name
    ends at the first stop word, so filler such as "pls" or "and" never becomes
    part of a name. Duplicate item names (case-insensitive) are merged by
    summing quantities.
    """

    _WORD_TO_NUM = {
        "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
        "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    }

    # Separators between items: "2 momos, 1 tea", "2x momos and 1 tea", ...
    _SEGMENT_SPLIT = re.compile(r"[,;\n&+]|\b(?:and|also)\b")

    # quantity, optional "x" multiplier, optional unit ("plates of"), item name.
    # "2 plates of momos" | "two plates of rice" | "2x momos" | "10 samosas"
    _ITEM_PATTERN = re.compile(
        r"(?<![a-z0-9])(\d+|(?:one|two|three|four|five|six|seven|eight|nine|ten)\b)"
        r"\s*(?:x\s+)?"
        r"(?:(?:plates?|pieces?|pcs|cups?|glasses?|bottles?|packets?)\s+(?:of\s+)?)?"
        r"([a-z][a-z\s]*)"
    )

    _MAX_NAME_WORDS = 4
    _MAX_NAME_LENGTH = 40

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

        for segment in cls._SEGMENT_SPLIT.split(text):
            for match in cls._ITEM_PATTERN.finditer(segment):
                qty_str, raw_name = match.group(1), match.group(2)

                qty = cls._WORD_TO_NUM.get(qty_str)
                if qty is None:
                    qty = int(qty_str)
                if qty < 1:
                    continue

                item_name = cls._clean_item_name(raw_name)
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
    def _clean_item_name(cls, raw_name: str) -> str:
        """Keep the words before the first stop word, capped in length.

        "samosas pls" -> "samosas", "momos with extra cheese" -> "momos".
        """
        words: list[str] = []
        for word in re.findall(r"[a-z]+", raw_name):
            if word in cls._STOP_WORDS:
                break
            words.append(word)
            if len(words) == cls._MAX_NAME_WORDS:
                break
        return " ".join(words)[: cls._MAX_NAME_LENGTH].strip()

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
