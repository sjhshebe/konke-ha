"""Tests for normalized Konke device models."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

import hass_shim  # noqa: F401

from custom_components.konke.api import _merge_device_cache
from custom_components.konke.capabilities import KonkeCapability
from custom_components.konke.models import (
    KonkeDevice,
    build_device_indexes,
    current_state_for_raw,
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

        self.assertEqual(
            sorted(indexes["devices_by_id"]),
            ["1001", "2001", "3001", "4001"],
        )
        self.assertEqual(
            indexes["device_ids_by_capability"][KonkeCapability.AIR_CONDITIONER.value],
            ["1001"],
        )
        self.assertEqual(
            indexes["device_ids_by_capability"][KonkeCapability.FLOOR_HEATING.value],
            ["3001"],
        )
        self.assertEqual(
            indexes["device_ids_by_capability"][KonkeCapability.COVER.value],
            ["4001"],
        )
        self.assertEqual(
            indexes["device_ids_by_capability"][KonkeCapability.SWITCH.value],
            ["2001"],
        )
        self.assertEqual(
            {
                (item["device_id"], item["capability"], item["platform"])
                for item in indexes["entities"]
            },
            {
                ("1001", "air_conditioner", "climate"),
                ("2001", "switch", "switch"),
                ("3001", KonkeCapability.FLOOR_HEATING.value, "climate"),
                ("4001", "cover", "cover"),
            },
        )

    def test_current_state_merges_extension_and_current(self) -> None:
        """Sparse current snapshots do not hide stable extension values."""
        raw = {
            "cache": {
                "extension": {
                    "operationMode": 2,
                    "position": 99,
                    "current": {
                        "operationMode": 1,
                        "updateTime": 123,
                    },
                },
            },
        }

        self.assertEqual(
            current_state_for_raw(raw),
            {
                "operationMode": 1,
                "position": 99,
                "updateTime": 123,
            },
        )

    def test_properties_keep_extension_values_missing_from_current(self) -> None:
        """Device summaries include parent extension values absent from current."""
        raw = load_devices()[3]
        raw["cache"]["extension"] = {
            "operationMode": 2,
            "position": 99,
            "current": {
                "operationMode": 1,
                "updateTime": 123,
            },
        }
        device = KonkeDevice.from_raw(raw)

        properties = {prop.key: prop for prop in device.properties}
        self.assertEqual(properties["position"].value, 99)
        self.assertEqual(properties["position"].source, "cache.extension")
        self.assertEqual(properties["operationMode"].value, 1)
        self.assertEqual(properties["operationMode"].source, "cache.extension.current")

    def test_device_cache_merge_preserves_device_shape(self) -> None:
        """Area cache snapshots are merged into device cache extension."""
        devices = [
            {
                "userDeviceId": 4001,
                "deviceName": "窗帘",
                "cache": {
                    "isOnline": True,
                    "extension": {
                        "operationMode": 1,
                        "current": {
                            "operationMode": 2,
                            "updateTime": 123,
                        },
                    },
                },
            }
        ]
        merged = _merge_device_cache(
            devices,
            [
                {
                    "userDeviceId": 4001,
                    "roomId": 1,
                    "operationMode": 2,
                    "position": 99,
                    "routeState": 1,
                    "isOnline": True,
                }
            ],
        )

        self.assertEqual(merged[0]["userDeviceId"], 4001)
        self.assertEqual(merged[0]["cache"]["extension"]["position"], 99)
        self.assertEqual(merged[0]["cache"]["extension"]["routeState"], 1)
        self.assertEqual(
            merged[0]["cache"]["extension"]["current"],
            {
                "operationMode": 2,
                "updateTime": 123,
            },
        )
