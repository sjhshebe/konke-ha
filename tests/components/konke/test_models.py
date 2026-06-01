"""Tests for normalized Konke device models."""

from __future__ import annotations

from custom_components.konke.api import _merge_device_cache
from custom_components.konke.capabilities import KonkeCapability
from custom_components.konke.models import (
    KonkeDevice,
    build_device_indexes,
    current_state_for_raw,
)

from .conftest import load_devices


def test_air_conditioner_model_has_stable_fields() -> None:
    """Air conditioner fixtures produce stable normalized fields."""
    device = KonkeDevice.from_raw(load_devices()[0])

    assert device.user_device_id == "1001"
    assert device.name == "空调左"
    assert device.room_name == "客厅"
    assert device.online is True
    assert device.power_on is True
    assert KonkeCapability.AIR_CONDITIONER in device.capabilities
    assert [command.action_name for command in device.commands] == ["TurnOn", "TurnOff"]
    assert {prop.key for prop in device.properties} >= {
        "on",
        "curTemp",
        "setTemp",
        "workMode",
        "speed",
    }


def test_build_device_indexes_exposes_entities() -> None:
    """Device indexes expose capability and entity descriptors."""
    indexes = build_device_indexes(load_devices())

    assert sorted(indexes["devices_by_id"]) == ["1001", "2001", "3001", "4001", "5001"]
    assert indexes["device_ids_by_capability"][KonkeCapability.AIR_CONDITIONER.value] == [
        "1001"
    ]
    assert indexes["device_ids_by_capability"][KonkeCapability.FLOOR_HEATING.value] == [
        "3001"
    ]
    assert indexes["device_ids_by_capability"][KonkeCapability.COVER.value] == ["4001"]
    assert indexes["device_ids_by_capability"][KonkeCapability.AIR_FRESHER.value] == [
        "5001"
    ]
    assert indexes["device_ids_by_capability"][KonkeCapability.SWITCH.value] == ["2001"]
    assert {
        (item["device_id"], item["capability"], item["platform"])
        for item in indexes["entities"]
    } == {
        ("1001", "air_conditioner", "climate"),
        ("2001", "switch", "switch"),
        ("3001", KonkeCapability.FLOOR_HEATING.value, "climate"),
        ("4001", "cover", "cover"),
        ("5001", KonkeCapability.AIR_FRESHER.value, "fan"),
    }


def test_fresh_air_model_has_state_and_fan_entity() -> None:
    """Fresh-air fixtures produce stable fan capability fields."""
    device = KonkeDevice.from_raw(load_devices()[4])

    assert device.user_device_id == "5001"
    assert device.name == "新风"
    assert device.online is True
    assert device.power_on is True
    assert KonkeCapability.AIR_FRESHER in device.capabilities
    assert {command.action_name for command in device.commands} >= {
        "TurnOn",
        "TurnOff",
        "SetMode",
        "AdjustDownWindSpeed",
        "AdjustUpWindSpeed",
    }
    assert {prop.key for prop in device.properties} >= {
        "turnOnOff",
        "currentTemperature",
        "workMode",
        "windSpeed",
        "strainerWorkTime",
        "strainerAlarmTime",
    }


def test_current_state_merges_extension_and_current() -> None:
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

    assert current_state_for_raw(raw) == {
        "operationMode": 1,
        "position": 99,
        "updateTime": 123,
    }


def test_properties_keep_extension_values_missing_from_current() -> None:
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
    assert properties["position"].value == 99
    assert properties["position"].source == "cache.extension"
    assert properties["operationMode"].value == 1
    assert properties["operationMode"].source == "cache.extension.current"


def test_device_cache_merge_preserves_device_shape() -> None:
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

    assert merged[0]["userDeviceId"] == 4001
    assert merged[0]["cache"]["extension"]["position"] == 99
    assert merged[0]["cache"]["extension"]["routeState"] == 1
    assert merged[0]["cache"]["extension"]["current"] == {
        "operationMode": 2,
        "updateTime": 123,
    }
