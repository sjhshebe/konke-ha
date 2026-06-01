"""Cover platform for Konke Smart."""

from __future__ import annotations

from typing import Any

from homeassistant.components.cover import (
    CoverDeviceClass,
    CoverEntity,
    CoverEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .capabilities import KonkeCapability
from .command import ACTION_PAUSE, ACTION_TURN_OFF, ACTION_TURN_ON
from .const import DOMAIN
from .coordinator import KonkeDataUpdateCoordinator
from .entity import KonkeDeviceEntity
from .models import KonkeDevice, current_state_for_raw
from .options import options_from_entry


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Konke cover devices from a config entry."""
    coordinator: KonkeDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        KonkeCurtainCover(coordinator, entry, device_id)
        for device_id in _device_ids_for_capability(
            coordinator, entry, KonkeCapability.COVER
        )
    )


class KonkeCurtainCover(KonkeDeviceEntity, CoverEntity):
    """Representation of a Konke motorized cover."""

    _attr_device_class = CoverDeviceClass.CURTAIN
    _attr_supported_features = (
        CoverEntityFeature.OPEN
        | CoverEntityFeature.CLOSE
        | CoverEntityFeature.STOP
    )

    def __init__(
        self,
        coordinator: KonkeDataUpdateCoordinator,
        entry: ConfigEntry,
        device_id: str,
    ) -> None:
        """Initialize the cover entity."""
        super().__init__(coordinator, entry, device_id)
        self._attr_unique_id = f"{DOMAIN}_{self.konke_home_id}_cover_{device_id}"

    @property
    def name(self) -> str | None:
        """Return the entity name."""
        device = self.konke_device
        return None if device else self._device_id

    @property
    def current_cover_position(self) -> int | None:
        """Return current cover position where 0 is closed and 100 is open."""
        device = self.konke_device
        if device is None:
            return None
        position = _int_from_state(_current_state(device), "position")
        if position is None:
            return None
        return max(0, min(100, position))

    @property
    def is_closed(self) -> bool | None:
        """Return if the cover is fully closed."""
        position = self.current_cover_position
        if position is None:
            return None
        return position <= 0

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return debug attributes for the mapped Konke device."""
        device = self.konke_device
        if device is None:
            return {}
        state = _current_state(device)
        return {
            "user_device_id": device.user_device_id,
            "room_id": device.room_id,
            "room_name": device.room_name,
            "node_id": device.node_id,
            "parent_user_device_id": device.parent_user_device_id,
            "cate_type": device.cate_type,
            "inner_type": device.inner_type,
            "product_id": device.product_id,
            "konke_operation_mode": state.get("operationMode"),
            "konke_work_mode": state.get("workMode"),
            "konke_route_state": state.get("routeState"),
            "online": device.online,
        }

    async def async_open_cover(self, **kwargs: Any) -> None:
        """Open the cover."""
        await self.async_control_device(ACTION_TURN_ON)

    async def async_close_cover(self, **kwargs: Any) -> None:
        """Close the cover."""
        await self.async_control_device(ACTION_TURN_OFF)

    async def async_stop_cover(self, **kwargs: Any) -> None:
        """Stop the cover."""
        await self.async_control_device(ACTION_PAUSE)


def _device_ids_for_capability(
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
    return sorted(device_ids, key=_sort_device_id)


def _current_state(device: KonkeDevice) -> dict[str, Any]:
    """Return the best cached current state payload for a device."""
    return current_state_for_raw(device.raw)


def _int_from_state(state: dict[str, Any], *keys: str) -> int | None:
    """Return the first integer state value from a set of keys."""
    for key in keys:
        value = state.get(key)
        try:
            return int(value)
        except (TypeError, ValueError):
            continue
    return None


def _sort_device_id(device_id: str) -> tuple[int, str]:
    """Sort numeric ids naturally."""
    try:
        return (0, f"{int(device_id):020d}")
    except (TypeError, ValueError):
        return (1, str(device_id))
