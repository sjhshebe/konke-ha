"""Device registry helpers for the Konke Smart integration."""

from __future__ import annotations

from typing import Any, Mapping

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr

from .const import CONF_HOME_ID, DOMAIN
from .coordinator import KonkeDataUpdateCoordinator
from .models import KonkeDevice
from .options import options_from_entry

MANUFACTURER = "Konke"


def home_identifier(home_id: str | int) -> tuple[str, str]:
    """Return the Home Assistant device identifier for a Konke home."""
    return (DOMAIN, str(home_id))


def device_identifier(device_id: str | int) -> tuple[str, str]:
    """Return the Home Assistant device identifier for a Konke device."""
    return (DOMAIN, str(device_id))


def home_device_info(
    *,
    home: Mapping[str, Any],
    home_id: str | int | None,
    entry_title: str,
) -> dict[str, Any]:
    """Return HA device info for the Konke home hub."""
    resolved_home_id = str(home.get("homeId") or home_id)
    return {
        "identifiers": {home_identifier(resolved_home_id)},
        "manufacturer": MANUFACTURER,
        "name": home.get("homeName") or entry_title,
        "model": "Konke Smart Cloud",
    }


def konke_device_info(
    device: KonkeDevice,
    *,
    devices_by_id: Mapping[str, KonkeDevice] | None = None,
) -> dict[str, Any]:
    """Return HA device info for a normalized Konke device."""
    info: dict[str, Any] = {
        "identifiers": {device_identifier(device.user_device_id)},
        "manufacturer": MANUFACTURER,
        "name": device_registry_name(device),
    }

    model = device_model(device)
    if model:
        info["model"] = model
    if device.suggested_area:
        info["suggested_area"] = device.suggested_area

    sw_version = firmware_version(device)
    if sw_version:
        info["sw_version"] = sw_version

    if devices_by_id:
        parent_id = device.parent_key
        if (
            parent_id
            and parent_id != device.user_device_id
            and parent_id in devices_by_id
        ):
            info["via_device"] = device_identifier(parent_id)

    return info


def device_registry_name(device: KonkeDevice) -> str:
    """Return the device name shown on the HA device page."""
    return device.name or device.user_device_id


def device_model(device: KonkeDevice) -> str | None:
    """Return a stable model string for a Konke device."""
    if device.type_name and device.product_id and device.type_name != device.product_id:
        return f"{device.type_name} ({device.product_id})"
    return device.model or device.type_name or device.product_id or device.cate_type


def firmware_version(device: KonkeDevice) -> str | None:
    """Return firmware/software version from known raw fields."""
    for key in ("currentVersion", "firmwareVersion", "softwareVersion", "version"):
        value = device.raw.get(key)
        if value:
            return str(value)
    return None


def async_register_konke_devices(
    hass: HomeAssistant,
    entry: ConfigEntry,
    coordinator: KonkeDataUpdateCoordinator,
) -> None:
    """Register known Konke devices in the HA device registry."""
    registry = dr.async_get(hass)
    data = coordinator.data or {}
    home = data.get("home", {})
    home_id = home.get("homeId") or entry.data.get(CONF_HOME_ID)
    if home_id:
        registry.async_get_or_create(
            config_entry_id=entry.entry_id,
            **home_device_info(
                home=home,
                home_id=home_id,
                entry_title=entry.title,
            ),
        )

    devices_by_id: Mapping[str, KonkeDevice] = data.get("normalized_devices_by_id", {})
    create_offline = options_from_entry(entry).create_offline_device_entities
    for device in sorted(
        devices_by_id.values(),
        key=lambda item: (
            item.parent_user_device_id is not None,
            _numeric_sort_key(item.user_device_id),
        ),
    ):
        if not create_offline and device.online is False:
            continue
        registry.async_get_or_create(
            config_entry_id=entry.entry_id,
            **konke_device_info(device, devices_by_id=devices_by_id),
        )


def _numeric_sort_key(value: str) -> tuple[int, str]:
    """Sort numeric ids naturally."""
    try:
        return (0, f"{int(value):020d}")
    except (TypeError, ValueError):
        return (1, str(value))
