"""Tests for Konke fan platform helpers."""

from __future__ import annotations

import unittest

import hass_shim  # noqa: F401

from custom_components.konke.fan import (
    _mode_from_state,
    _speed_from_percentage,
    _speed_from_state,
)


class FanTest(unittest.TestCase):
    """Tests for fresh-air fan mapping helpers."""

    def test_speed_from_percentage_uses_three_valid_steps(self) -> None:
        """Home Assistant percentages map to confirmed Konke speed steps."""
        self.assertIsNone(_speed_from_percentage(0))
        self.assertEqual(_speed_from_percentage(1), 1)
        self.assertEqual(_speed_from_percentage(33), 1)
        self.assertEqual(_speed_from_percentage(50), 2)
        self.assertEqual(_speed_from_percentage(66), 2)
        self.assertEqual(_speed_from_percentage(80), 2)
        self.assertEqual(_speed_from_percentage(100), 3)

    def test_state_helpers_normalize_numeric_strings(self) -> None:
        """Fresh-air state helpers accept numeric cache values and strings."""
        self.assertEqual(_speed_from_state({"windSpeed": "3"}), 3)
        self.assertEqual(_mode_from_state({"workMode": "1"}), 1)
        self.assertIsNone(_speed_from_state({"windSpeed": "unknown"}))
