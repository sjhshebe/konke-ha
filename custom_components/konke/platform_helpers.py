"""Shared helpers for Home Assistant platform entities."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry

from .capabilities import KonkeCapability
from .coordinator import KonkeDataUpdateCoordinator
from .models import KonkeDevice, current_state_for_raw, maybe_bool
from .options import options_from_entry


def device_ids_for_capability(
    coordinator: KonkeDataUpdateCoordinator,
    entry: ConfigEntry,
    capability: KonkeCapability,
) -> list[str]:
    """Return sorted device ids for a capability, honoring offline options."""
    device_ids = list(
        coordinator.data.get("device_ids_by_capability", {}).get(capability.value, [])
    )
    if options_from_entry(entry).create_offline_device_entities is False:
        devices_by_id = coordinator.data.get("normalized_devices_by_id", {})
        device_ids = [
            device_id
            for device_id in device_ids
            if devices_by_id.get(device_id) is not None
            and devices_by_id[device_id].online is not False
        ]
    return sorted(device_ids, key=sort_numeric_id)


def device_name_or_id(device: KonkeDevice | None, fallback_id: str) -> str | None:
    """Return None for named HA device entities, or the id when missing."""
    return None if device else fallback_id


def device_state(device: KonkeDevice) -> dict[str, Any]:
    """Return the best cached current state payload for a device."""
    return current_state_for_raw(device.raw)


def optional_device_state(device: KonkeDevice | None) -> dict[str, Any]:
    """Return current state for an optional device."""
    if device is None:
        return {}
    return device_state(device)


def device_base_attributes(
    device: KonkeDevice,
    *,
    include_power_on: bool = True,
) -> dict[str, Any]:
    """Return common diagnostic attributes for a mapped Konke device."""
    attributes = {
        "user_device_id": device.user_device_id,
        "room_id": device.room_id,
        "room_name": device.room_name,
        "node_id": device.node_id,
        "parent_user_device_id": device.parent_user_device_id,
        "cate_type": device.cate_type,
        "inner_type": device.inner_type,
        "product_id": device.product_id,
        "online": device.online,
    }
    if include_power_on:
        attributes["power_on"] = device.power_on
    return attributes


def power_from_state(state: dict[str, Any], *keys: str) -> bool | None:
    """Return cached power state from a current-state payload."""
    for key in keys or ("on", "turnOnOff"):
        power = maybe_bool(state.get(key))
        if power is not None:
            return power
    return None


def int_from_state(state: dict[str, Any], *keys: str) -> int | None:
    """Return the first integer state value from a set of keys."""
    for key in keys:
        value = state.get(key)
        try:
            return int(value)
        except (TypeError, ValueError):
            continue
    return None


def float_from_state(state: dict[str, Any], *keys: str) -> float | None:
    """Return the first numeric state value from a set of keys."""
    for key in keys:
        value = state.get(key)
        try:
            return float(value)
        except (TypeError, ValueError):
            continue
    return None


def sort_numeric_id(value: str) -> tuple[int, str]:
    """Sort numeric ids naturally."""
    try:
        return (0, f"{int(value):020d}")
    except (TypeError, ValueError):
        return (1, str(value))
