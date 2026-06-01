"""Tests for Konke command payload helpers."""

from __future__ import annotations

import unittest

import hass_shim  # noqa: F401

from custom_components.konke.command import (
    ACTION_SET_MODE,
    ACTION_SET_TEMPERATURE,
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

    def test_build_device_action_body_keeps_extension_object(self) -> None:
        """Control extension payloads are sent as JSON objects."""
        self.assertEqual(
            build_device_action_body(
                user_device_id="1001",
                action_name=ACTION_SET_TEMPERATURE,
                extension={"value": 25.0},
            ),
            {
                "userDeviceId": 1001,
                "name": "SetTemperature",
                "extension": {"value": 25.0},
            },
        )

    def test_build_device_action_body_allows_integer_mode(self) -> None:
        """Floor-heating modes use numeric extension values."""
        self.assertEqual(
            build_device_action_body(
                user_device_id="3001",
                action_name=ACTION_SET_MODE,
                extension={"mode": 0},
            ),
            {
                "userDeviceId": 3001,
                "name": "SetMode",
                "extension": {"mode": 0},
            },
        )

    def test_air_conditioner_turn_off_action(self) -> None:
        """Air conditioner turn-off action is explicit and stable."""
        self.assertEqual(
            air_conditioner_turn_off_action({"userDeviceId": "1001"}),
            (1001, "TurnOff"),
        )
