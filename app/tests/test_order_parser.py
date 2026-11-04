"""Tests for the free-text WhatsApp order parser."""

from __future__ import annotations

import pytest

from app.utils.order_parser import OrderItem, OrderParser


def _as_pairs(items: list[OrderItem]) -> set[tuple[str, int]]:
    return {(item.name, item.qty) for item in items}


@pytest.mark.parametrize(
    ("message", "expected"),
    [
        ("2x momos", {("Momos", 2)}),
        ("3X burger", {("Burger", 3)}),
        ("two plates of rice", {("Rice", 2)}),
        ("1 plate of rice", {("Rice", 1)}),
        ("i want 5 samosas pls", {("Samosas", 5)}),
        ("ten samosas", {("Samosas", 10)}),
    ],
)
def test_parses_single_item_patterns(message: str, expected: set[tuple[str, int]]) -> None:
    assert _as_pairs(OrderParser.parse_order(message)) == expected


def test_parses_multiple_items_in_one_message() -> None:
    items = OrderParser.parse_order("2 momos, 1 tea")
    assert ("Momos", 2) in _as_pairs(items)
    assert ("Tea", 1) in _as_pairs(items)


def test_names_are_title_cased() -> None:
    items = OrderParser.parse_order("4 CHICKEN WINGS")
    assert items[0].name == "Chicken Wings"
    assert items[0].qty == 4


@pytest.mark.parametrize("message", ["", "   ", "hello there", "thanks!", "ok"])
def test_messages_without_orders_return_empty_list(message: str) -> None:
    assert OrderParser.parse_order(message) == []


def test_stop_word_only_candidates_are_ignored() -> None:
    assert OrderParser.parse_order("2 please") == []


def test_very_long_messages_are_truncated_safely() -> None:
    message = "2 momos " + "x" * 10_000
    items = OrderParser.parse_order(message)
    assert len(items) == 1
    assert items[0].qty == 2
    assert items[0].name.startswith("Momos")
    assert len(items[0].name) <= 40


# ── Regression tests for bugs fixed alongside this suite ──────────────────────


def test_unit_phrases_are_not_counted_twice() -> None:
    # Previously returned both "Rice" and "Plate Of Rice".
    assert _as_pairs(OrderParser.parse_order("1 plate of rice")) == {("Rice", 1)}


def test_filler_words_are_not_part_of_item_names() -> None:
    # Previously returned "Momos And" and "Samosas Pls".
    assert _as_pairs(OrderParser.parse_order("2x momos and 1 tea")) == {
        ("Momos", 2),
        ("Tea", 1),
    }
    assert _as_pairs(OrderParser.parse_order("3 burgers with extra cheese")) == {
        ("Burgers", 3),
    }


def test_items_without_separators_are_split_on_the_next_quantity() -> None:
    assert _as_pairs(OrderParser.parse_order("2 momos 1 tea")) == {("Momos", 2), ("Tea", 1)}


def test_duplicate_items_are_merged() -> None:
    assert _as_pairs(OrderParser.parse_order("2 momos, 3 momos")) == {("Momos", 5)}


def test_number_words_inside_other_words_are_ignored() -> None:
    assert OrderParser.parse_order("someone called") == []


def test_zero_quantity_is_ignored() -> None:
    assert OrderParser.parse_order("0 momos") == []


def test_order_item_serialises_to_dict() -> None:
    item = OrderItem(name="Tea", qty=2, notes="no sugar")
    assert item.to_dict() == {"name": "Tea", "qty": 2, "notes": "no sugar"}
