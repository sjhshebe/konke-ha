"""Tests for Konke fan platform helpers."""

from __future__ import annotations

from custom_components.konke.fan import (
    _mode_from_state,
    _speed_from_percentage,
    _speed_from_state,
)


def test_speed_from_percentage_uses_three_valid_steps() -> None:
    """Home Assistant percentages map to confirmed Konke speed steps."""
    assert _speed_from_percentage(0) is None
    assert _speed_from_percentage(1) == 1
    assert _speed_from_percentage(33) == 1
    assert _speed_from_percentage(50) == 2
    assert _speed_from_percentage(66) == 2
    assert _speed_from_percentage(80) == 2
    assert _speed_from_percentage(100) == 3


def test_state_helpers_normalize_numeric_strings() -> None:
    """Fresh-air state helpers accept numeric cache values and strings."""
    assert _speed_from_state({"windSpeed": "3"}) == 3
    assert _mode_from_state({"workMode": "1"}) == 1
    assert _speed_from_state({"windSpeed": "unknown"}) is None
