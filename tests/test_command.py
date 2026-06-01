"""Tests for Konke command payload helpers."""

from __future__ import annotations

import unittest

import hass_shim  # noqa: F401

from custom_components.konke.command import (
    ACTION_TURN_OFF,
    air_conditioner_turn_off_action,
    build_device_action_body,
)
from custom_components.konke.exceptions import KonkeCommandError


class CommandTest(unittest.TestCase):
    """Tests for command payload helpers."""

    def test_build_device_action_body_normalizes_id(self) -> None:
        """Command body uses numeric userDeviceId and action name."""
        self.assertEqual(
            build_device_action_body(
                user_device_id="1001",
                action_name=ACTION_TURN_OFF,
            ),
            {
                "userDeviceId": 1001,
                "name": "TurnOff",
            },
        )

    def test_build_device_action_body_rejects_non_numeric_id(self) -> None:
        """Non-numeric ids cannot be sent to the current control endpoint."""
        with self.assertRaises(KonkeCommandError):
            build_device_action_body(user_device_id="abc", action_name=ACTION_TURN_OFF)

    def test_air_conditioner_turn_off_action(self) -> None:
        """Air conditioner turn-off action is explicit and stable."""
        self.assertEqual(
            air_conditioner_turn_off_action({"userDeviceId": "1001"}),
            (1001, "TurnOff"),
        )
