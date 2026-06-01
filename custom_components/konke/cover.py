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
from .platform_helpers import (
    device_base_attributes,
    device_ids_for_capability,
    device_name_or_id,
    device_state,
    int_from_state,
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Konke cover devices from a config entry."""
    coordinator: KonkeDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        KonkeCurtainCover(coordinator, entry, device_id)
        for device_id in device_ids_for_capability(
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
        return device_name_or_id(self.konke_device, self._device_id)

    @property
    def current_cover_position(self) -> int | None:
        """Return current cover position where 0 is closed and 100 is open."""
        device = self.konke_device
        if device is None:
            return None
        position = int_from_state(device_state(device), "position")
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
        state = device_state(device)
        return {
            **device_base_attributes(device, include_power_on=False),
            "konke_operation_mode": state.get("operationMode"),
            "konke_work_mode": state.get("workMode"),
            "konke_route_state": state.get("routeState"),
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

