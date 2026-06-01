"""Helpers for Konke air conditioner devices."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .capabilities import KonkeCapability, capability_matches_device_type


def _nested(data: Mapping[str, Any], *keys: str) -> Any:
    """Return a nested value from a dict."""
    value: Any = data
    for key in keys:
        if not isinstance(value, Mapping):
            return None
        value = value.get(key)
    return value


def _as_string_set(values: list[Any] | tuple[Any, ...] | None) -> set[str]:
    """Normalize a list-like value to a set of non-empty strings."""
    if not values:
        return set()
    return {str(value) for value in values if str(value)}


def _maybe_str(value: Any) -> str | None:
    """Return a non-empty string value."""
    if value is None:
        return None
    normalized = str(value)
    return normalized or None


def is_air_conditioner(device: Mapping[str, Any]) -> bool:
    """Return true when a Konke device looks like an air conditioner."""
    cate_type = (
        _nested(device, "device", "cateType")
        or _nested(device, "device", "deviceType", "cateType")
    )
    device_type = _nested(device, "device", "deviceType") or {}
    return capability_matches_device_type(
        KonkeCapability.AIR_CONDITIONER,
        cate_type=str(cate_type) if cate_type is not None else None,
        inner_type=_maybe_str(device_type.get("innerType")),
        product_id=_maybe_str(device_type.get("productId")),
        icon=_maybe_str(device.get("icon")),
        device_name=_maybe_str(device.get("deviceName")),
    )


def is_online(device: Mapping[str, Any]) -> bool | None:
    """Return cached online state, if present."""
    values = (
        _nested(device, "cache", "isOnline"),
        _nested(device, "cache", "extension", "online"),
        _nested(device, "cache", "extension", "current", "online"),
    )
    for value in values:
        if isinstance(value, bool):
            return value

    online_state = (
        _nested(device, "cache", "extension", "onlineState")
        or _nested(device, "cache", "extension", "current", "onlineState")
    )
    if isinstance(online_state, str):
        return online_state.upper() == "ONLINE"
    return None


def is_on(device: Mapping[str, Any]) -> bool | None:
    """Return cached power state, if present."""
    for path in (
        ("cache", "extension", "current", "on"),
        ("cache", "extension", "on"),
        ("cache", "extension", "current", "turnOnOff"),
        ("cache", "extension", "turnOnOff"),
    ):
        value = _nested(device, *path)
        if isinstance(value, bool):
            return value
    return None


def summarize_air_conditioner(device: dict[str, Any]) -> dict[str, Any]:
    """Return a stable, safe summary of an air conditioner device."""
    device_type = _nested(device, "device", "deviceType") or {}
    cache = device.get("cache") or {}
    cache_extension = cache.get("extension") if isinstance(cache, dict) else {}
    current = cache_extension.get("current") if isinstance(cache_extension, dict) else {}
    return {
        "user_device_id": device.get("userDeviceId"),
        "device_id": _nested(device, "device", "deviceId"),
        "device_name": device.get("deviceName"),
        "room_id": device.get("roomId"),
        "room_name": device.get("roomName"),
        "area_id": device.get("areaId"),
        "area_name": device.get("areaName"),
        "node_id": device.get("nodeId"),
        "parent_user_device_id": device.get("parentUserDeviceId"),
        "gw_id": device.get("gwId"),
        "udid": device.get("UDID"),
        "origin_product_id": device.get("originProductId"),
        "product_id": device_type.get("productId"),
        "type_id": device_type.get("typeId"),
        "inner_type": device_type.get("innerType"),
        "type_name": device_type.get("typeName"),
        "action_list": device_type.get("actionList") or [],
        "online": is_online(device),
        "on": is_on(device),
        "current": current if isinstance(current, dict) else {},
    }


def filter_air_conditioners(
    devices: list[dict[str, Any]],
    *,
    include_room_names: list[Any] | tuple[Any, ...] | None = None,
    exclude_room_names: list[Any] | tuple[Any, ...] | None = None,
    include_room_ids: list[Any] | tuple[Any, ...] | None = None,
    exclude_room_ids: list[Any] | tuple[Any, ...] | None = None,
    include_offline: bool = False,
    only_on: bool = False,
) -> list[dict[str, Any]]:
    """Filter Konke devices down to air conditioners matching room constraints."""
    include_names = _as_string_set(include_room_names)
    exclude_names = _as_string_set(exclude_room_names)
    include_ids = _as_string_set(include_room_ids)
    exclude_ids = _as_string_set(exclude_room_ids)

    matched: list[dict[str, Any]] = []
    for device in devices:
        if not is_air_conditioner(device):
            continue

        room_name = str(device.get("roomName") or "")
        room_id = str(device.get("roomId") or "")
        if include_names and room_name not in include_names:
            continue
        if exclude_names and room_name in exclude_names:
            continue
        if include_ids and room_id not in include_ids:
            continue
        if exclude_ids and room_id in exclude_ids:
            continue

        online = is_online(device)
        if not include_offline and online is False:
            continue
        power = is_on(device)
        if only_on and power is not True:
            continue

        matched.append(device)
    return matched
