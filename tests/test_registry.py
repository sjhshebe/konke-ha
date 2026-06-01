"""Tests for Home Assistant registry metadata."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

import hass_shim  # noqa: F401

from custom_components.konke.models import KonkeDevice
from custom_components.konke.registry import device_registry_name, konke_device_info

FIXTURES = Path(__file__).parent / "fixtures"


def load_devices() -> list[dict]:
    """Load sanitized fixture devices."""
    return json.loads((FIXTURES / "devices.json").read_text())


class RegistryTest(unittest.TestCase):
    """Tests for registry metadata helpers."""

    def test_device_name_does_not_duplicate_suggested_area(self) -> None:
        """Device registry name should not include the room prefix."""
        device = KonkeDevice.from_raw(load_devices()[0])

        self.assertEqual(device.room_name, "客厅")
        self.assertEqual(device_registry_name(device), "空调左")

    def test_device_info_keeps_room_as_suggested_area(self) -> None:
        """Room information should remain available through HA area metadata."""
        device = KonkeDevice.from_raw(load_devices()[0])

        self.assertEqual(
            konke_device_info(device),
            {
                "identifiers": {("konke", "1001")},
                "manufacturer": "Konke",
                "name": "空调左",
                "model": "空调 (kk-ac)",
                "suggested_area": "客厅",
            },
        )
