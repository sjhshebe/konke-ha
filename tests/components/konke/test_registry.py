"""Tests for Home Assistant registry metadata."""

from __future__ import annotations

from custom_components.konke.models import KonkeDevice
from custom_components.konke.registry import device_registry_name, konke_device_info

from .conftest import load_devices


def test_device_name_does_not_duplicate_suggested_area() -> None:
    """Device registry name should not include the room prefix."""
    device = KonkeDevice.from_raw(load_devices()[0])

    assert device.room_name == "客厅"
    assert device_registry_name(device) == "空调左"


def test_device_info_keeps_room_as_suggested_area() -> None:
    """Room information should remain available through HA area metadata."""
    device = KonkeDevice.from_raw(load_devices()[0])

    assert konke_device_info(device) == {
        "identifiers": {("konke", "1001")},
        "manufacturer": "Konke",
        "name": "空调左",
        "model": "空调 (kk-ac)",
        "suggested_area": "客厅",
    }
