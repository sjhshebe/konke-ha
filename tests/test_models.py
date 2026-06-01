"""Tests for normalized Konke device models."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

import hass_shim  # noqa: F401

from custom_components.konke.capabilities import KonkeCapability
from custom_components.konke.models import (
    KonkeDevice,
    build_device_indexes,
)


FIXTURES = Path(__file__).parent / "fixtures"


def load_devices() -> list[dict]:
    """Load sanitized fixture devices."""
    return json.loads((FIXTURES / "devices.json").read_text())


class ModelTest(unittest.TestCase):
    """Tests for normalized models."""

    def test_air_conditioner_model_has_stable_fields(self) -> None:
        """Air conditioner fixtures produce stable normalized fields."""
        device = KonkeDevice.from_raw(load_devices()[0])

        self.assertEqual(device.user_device_id, "1001")
        self.assertEqual(device.name, "空调左")
        self.assertEqual(device.room_name, "客厅")
        self.assertIs(device.online, True)
        self.assertIs(device.power_on, True)
        self.assertIn(KonkeCapability.AIR_CONDITIONER, device.capabilities)
        self.assertEqual(
            [command.action_name for command in device.commands],
            ["TurnOn", "TurnOff"],
        )
        self.assertGreaterEqual(
            {prop.key for prop in device.properties},
            {
                "on",
                "curTemp",
                "setTemp",
                "workMode",
                "speed",
            },
        )

    def test_build_device_indexes_exposes_entities(self) -> None:
        """Device indexes expose capability and entity descriptors."""
        indexes = build_device_indexes(load_devices())

        self.assertEqual(sorted(indexes["devices_by_id"]), ["1001", "2001"])
        self.assertEqual(indexes["device_ids_by_capability"]["air_conditioner"], ["1001"])
        self.assertEqual(indexes["device_ids_by_capability"]["switch"], ["2001"])
        self.assertEqual(
            {
                (item["device_id"], item["capability"], item["platform"])
                for item in indexes["entities"]
            },
            {
                ("1001", "air_conditioner", "climate"),
                ("2001", "switch", "switch"),
            },
        )
