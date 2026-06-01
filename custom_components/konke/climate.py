"""Climate platform for Konke Smart."""

from __future__ import annotations

from typing import Any

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .capabilities import KonkeCapability
from .const import CONF_HOME_ID, DOMAIN
from .coordinator import KonkeDataUpdateCoordinator
from .entity import KonkeDeviceEntity
from .exceptions import KonkeAuthError
from .models import KonkeDevice, maybe_bool, nested
from .options import options_from_entry

_MODE_TO_HVAC = {
    "AUTO": HVACMode.AUTO,
    "COLD": HVACMode.COOL,
    "COOL": HVACMode.COOL,
    "DRY": HVACMode.DRY,
    "HEAT": HVACMode.HEAT,
    "HOT": HVACMode.HEAT,
    "WARM": HVACMode.HEAT,
    "WIND": HVACMode.FAN_ONLY,
    "FAN": HVACMode.FAN_ONLY,
}

_WORK_MODE_TO_HVAC = {
    0: HVACMode.AUTO,
    1: HVACMode.COOL,
    2: HVACMode.HEAT,
    3: HVACMode.FAN_ONLY,
    4: HVACMode.DRY,
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Konke air conditioners from a config entry."""
    coordinator: KonkeDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    device_ids = coordinator.data.get("device_ids_by_capability", {}).get(
        KonkeCapability.AIR_CONDITIONER.value,
        [],
    )
    if options_from_entry(entry).create_offline_device_entities is False:
        devices_by_id = coordinator.data.get("normalized_devices_by_id", {})
        device_ids = [
            device_id
            for device_id in device_ids
            if devices_by_id.get(device_id) is not None
            and devices_by_id[device_id].online is not False
        ]
    async_add_entities(
        KonkeAirConditionerClimate(coordinator, entry, device_id)
        for device_id in sorted(device_ids, key=_sort_device_id)
    )


class KonkeAirConditionerClimate(KonkeDeviceEntity, ClimateEntity):
    """Representation of a Konke air conditioner."""

    _attr_icon = "mdi:air-conditioner"
    _attr_precision = 0.5
    _attr_supported_features = ClimateEntityFeature.TURN_OFF
    _attr_target_temperature_step = 0.5
    _enable_turn_on_off_backwards_compatibility = False

    def __init__(
        self,
        coordinator: KonkeDataUpdateCoordinator,
        entry: ConfigEntry,
        device_id: str,
    ) -> None:
        """Initialize the climate entity."""
        super().__init__(coordinator, entry, device_id)
        self._attr_unique_id = f"{DOMAIN}_{self.konke_home_id}_climate_{device_id}"

    @property
    def name(self) -> str | None:
        """Return the entity name."""
        device = self.konke_device
        return None if device else self._device_id

    @property
    def temperature_unit(self) -> str:
        """Return the unit of measurement."""
        return UnitOfTemperature.CELSIUS

    @property
    def hvac_modes(self) -> list[HVACMode]:
        """Return supported HVAC modes for state representation."""
        mode = self.hvac_mode
        modes = [HVACMode.OFF]
        if mode and mode is not HVACMode.OFF:
            modes.append(mode)
        if HVACMode.COOL not in modes:
            modes.append(HVACMode.COOL)
        return modes

    @property
    def hvac_mode(self) -> HVACMode | None:
        """Return the current HVAC mode."""
        device = self.konke_device
        if device is None:
            return HVACMode.OFF
        if device.power_on is False:
            return HVACMode.OFF

        state = _current_state(device)
        mode = _state_hvac_mode(state)
        if mode is not None:
            return mode

        if device.power_on is True:
            return HVACMode.COOL
        return HVACMode.OFF

    @property
    def hvac_action(self) -> HVACAction | None:
        """Return the current HVAC action."""
        mode = self.hvac_mode
        if mode is HVACMode.OFF:
            return HVACAction.OFF
        if mode is HVACMode.HEAT:
            return HVACAction.HEATING
        if mode is HVACMode.COOL:
            return HVACAction.COOLING
        if mode is HVACMode.DRY:
            return HVACAction.DRYING
        if mode is HVACMode.FAN_ONLY:
            return HVACAction.FAN
        if mode is HVACMode.AUTO:
            return HVACAction.IDLE
        return None

    @property
    def current_temperature(self) -> float | None:
        """Return the current temperature."""
        device = self.konke_device
        if device is None:
            return None
        state = _current_state(device)
        return _float_from_state(state, "curTemp", "currentTemperature")

    @property
    def target_temperature(self) -> float | None:
        """Return the target temperature."""
        device = self.konke_device
        if device is None:
            return None
        state = _current_state(device)
        return _float_from_state(state, "setTemp", "temperature")

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
            "konke_mode": state.get("mode"),
            "konke_work_mode": state.get("workMode"),
            "konke_fan_speed": state.get("speed") or state.get("windSpeed"),
            "online": device.online,
            "power_on": device.power_on,
        }

    async def async_turn_off(self) -> None:
        """Turn the air conditioner off."""
        device = self.konke_device
        if device is None:
            raise HomeAssistantError(f"Konke device not found: {self._device_id}")

        home_id = self._entry.data.get(CONF_HOME_ID)
        if not home_id:
            home_id = self.coordinator.data.get("home", {}).get("homeId")
        if not home_id:
            raise HomeAssistantError("Konke home_id not found")

        try:
            await self.coordinator.client.turn_off_air_conditioner(
                home_id=home_id,
                device=dict(device.raw),
            )
        except KonkeAuthError:
            if not await self.coordinator.async_refresh_auth():
                raise
            await self.coordinator.client.turn_off_air_conditioner(
                home_id=home_id,
                device=dict(device.raw),
            )
        await self.coordinator.async_request_refresh()

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set HVAC mode.

        Only off is implemented until the corresponding Konke commands have
        been captured and tested.
        """
        if hvac_mode is HVACMode.OFF:
            await self.async_turn_off()
            return
        raise HomeAssistantError(
            "Konke air conditioner currently only supports turning off"
        )


def _current_state(device: KonkeDevice) -> dict[str, Any]:
    """Return the best cached current state payload for a device."""
    current = nested(device.raw, "cache", "extension", "current")
    if isinstance(current, dict):
        return current
    extension = nested(device.raw, "cache", "extension")
    if isinstance(extension, dict):
        return extension
    return {}


def _state_hvac_mode(state: dict[str, Any]) -> HVACMode | None:
    """Return a HA HVAC mode from a Konke cached state payload."""
    power = maybe_bool(state.get("on"))
    if power is None:
        power = maybe_bool(state.get("turnOnOff"))
    if power is False:
        return HVACMode.OFF

    raw_mode = state.get("mode")
    if raw_mode is not None:
        mode = _MODE_TO_HVAC.get(str(raw_mode).upper())
        if mode is not None:
            return mode

    raw_work_mode = state.get("workMode")
    try:
        work_mode = int(raw_work_mode)
    except (TypeError, ValueError):
        return None
    return _WORK_MODE_TO_HVAC.get(work_mode)


def _float_from_state(state: dict[str, Any], *keys: str) -> float | None:
    """Return the first numeric state value from a set of keys."""
    for key in keys:
        value = state.get(key)
        try:
            return float(value)
        except (TypeError, ValueError):
            continue
    return None


def _sort_device_id(device_id: str) -> tuple[int, str]:
    """Sort numeric ids naturally."""
    try:
        return (0, f"{int(device_id):020d}")
    except (TypeError, ValueError):
        return (1, str(device_id))
