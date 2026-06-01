"""Fan platform for Konke Smart."""

from __future__ import annotations

import asyncio
from typing import Any

from homeassistant.components.fan import FanEntity, FanEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .capabilities import KonkeCapability
from .command import ACTION_SET_MODE, ACTION_TURN_OFF, ACTION_TURN_ON
from .const import DOMAIN
from .coordinator import KonkeDataUpdateCoordinator
from .entity import KonkeDeviceEntity
from .platform_helpers import (
    device_base_attributes,
    device_ids_for_capability,
    device_name_or_id,
    device_state,
    float_from_state,
    int_from_state,
    optional_device_state,
    power_from_state,
)

ACTION_ADJUST_DOWN_WIND_SPEED = "AdjustDownWindSpeed"
ACTION_ADJUST_UP_WIND_SPEED = "AdjustUpWindSpeed"

_SPEED_RANGE = range(1, 4)
_SPEED_REFRESH_ATTEMPTS = 5
_SPEED_REFRESH_DELAY = 1
_PERCENTAGE_TO_SPEED = {
    33: 1,
    66: 2,
    100: 3,
}
_SPEED_TO_PERCENTAGE = {
    1: 33,
    2: 66,
    3: 100,
}
_PRESET_MODE_TO_KONKE = {
    "auto": 0,
    "manual": 1,
}
_KONKE_MODE_TO_PRESET = {
    0: "auto",
    1: "manual",
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Konke fan devices from a config entry."""
    coordinator: KonkeDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        KonkeFreshAirFan(coordinator, entry, device_id)
        for device_id in device_ids_for_capability(
            coordinator,
            entry,
            KonkeCapability.AIR_FRESHER,
        )
    )


class KonkeFreshAirFan(KonkeDeviceEntity, FanEntity):
    """Representation of a Konke fresh-air device."""

    _attr_icon = "mdi:air-filter"
    _attr_preset_modes = list(_PRESET_MODE_TO_KONKE)
    _attr_speed_count = len(_SPEED_RANGE)
    _attr_supported_features = (
        FanEntityFeature.TURN_ON
        | FanEntityFeature.TURN_OFF
        | FanEntityFeature.SET_SPEED
        | FanEntityFeature.PRESET_MODE
    )

    def __init__(
        self,
        coordinator: KonkeDataUpdateCoordinator,
        entry: ConfigEntry,
        device_id: str,
    ) -> None:
        """Initialize the fresh-air fan entity."""
        super().__init__(coordinator, entry, device_id)
        self._attr_unique_id = f"{DOMAIN}_{self.konke_home_id}_fan_{device_id}"

    @property
    def name(self) -> str | None:
        """Return the entity name."""
        return device_name_or_id(self.konke_device, self._device_id)

    @property
    def is_on(self) -> bool | None:
        """Return whether the fresh-air device is on."""
        device = self.konke_device
        if device is None:
            return None
        state_power = power_from_state(device_state(device), "turnOnOff")
        if state_power is not None:
            return state_power
        return device.power_on

    @property
    def percentage(self) -> int | None:
        """Return the current fan speed as a percentage."""
        speed = _speed_from_state(optional_device_state(self.konke_device))
        if speed is None:
            return None
        return _SPEED_TO_PERCENTAGE.get(speed)

    @property
    def preset_mode(self) -> str | None:
        """Return the current fresh-air work mode."""
        mode = _mode_from_state(optional_device_state(self.konke_device))
        if mode is None:
            return None
        return _KONKE_MODE_TO_PRESET.get(mode)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return debug attributes for the mapped Konke device."""
        device = self.konke_device
        if device is None:
            return {}
        state = device_state(device)
        return {
            **device_base_attributes(device),
            "current_temperature": float_from_state(state, "currentTemperature"),
            "konke_work_mode": state.get("workMode"),
            "konke_wind_speed": state.get("windSpeed"),
            "timing_off_time": state.get("timingOffTime"),
            "strainer_work_time": state.get("strainerWorkTime"),
            "strainer_alarm_time": state.get("strainerAlarmTime"),
        }

    async def async_turn_on(
        self,
        percentage: int | None = None,
        preset_mode: str | None = None,
        **kwargs: Any,
    ) -> None:
        """Turn the fresh-air device on."""
        await self.async_control_device(ACTION_TURN_ON, refresh=False)
        if preset_mode is not None:
            await self.async_set_preset_mode(preset_mode)
        elif percentage is not None:
            await self.async_set_percentage(percentage)
        else:
            await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the fresh-air device off."""
        await self.async_control_device(ACTION_TURN_OFF)

    async def async_set_percentage(self, percentage: int) -> None:
        """Set fresh-air wind speed by stepping up or down."""
        if percentage <= 0:
            await self.async_turn_off()
            return

        target_speed = _speed_from_percentage(percentage)
        if target_speed is None:
            raise HomeAssistantError(
                f"Konke fresh-air fan does not support percentage: {percentage}"
            )

        device = self.konke_device
        if device is None:
            raise HomeAssistantError(f"Konke device not found: {self._device_id}")
        current_speed = _speed_from_state(device_state(device))
        if current_speed is None:
            raise HomeAssistantError("Konke fresh-air fan speed is unavailable")

        if self.is_on is False:
            await self.async_control_device(ACTION_TURN_ON)
            current_speed = self._current_speed()
            if current_speed is None:
                raise HomeAssistantError("Konke fresh-air fan speed is unavailable")
        if current_speed == target_speed:
            return

        for _ in range(len(_SPEED_RANGE) - 1):
            current_speed = self._current_speed()
            if current_speed is None:
                raise HomeAssistantError("Konke fresh-air fan speed is unavailable")
            if current_speed == target_speed:
                return
            next_speed = (
                current_speed + 1
                if target_speed > current_speed
                else current_speed - 1
            )
            step_action = (
                ACTION_ADJUST_UP_WIND_SPEED
                if target_speed > current_speed
                else ACTION_ADJUST_DOWN_WIND_SPEED
            )
            await self.async_control_device(step_action)
            if not await self._async_wait_for_speed(next_speed):
                raise HomeAssistantError(
                    "Konke fresh-air fan speed did not update to "
                    f"{next_speed}; current speed is {self._current_speed()}"
                )

        current_speed = self._current_speed()
        if current_speed != target_speed:
            raise HomeAssistantError(
                "Konke fresh-air fan speed did not reach "
                f"{target_speed}; current speed is {current_speed}"
            )

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set fresh-air work mode."""
        mode = _PRESET_MODE_TO_KONKE.get(str(preset_mode).lower())
        if mode is None:
            raise HomeAssistantError(
                f"Konke fresh-air fan does not support preset mode: {preset_mode}"
            )

        if self.is_on is False:
            await self.async_control_device(ACTION_TURN_ON, refresh=False)
        await self.async_control_device(
            ACTION_SET_MODE,
            extension={"mode": mode},
        )

    def _current_speed(self) -> int | None:
        """Return the latest known wind speed."""
        device = self.konke_device
        if device is None:
            return None
        return _speed_from_state(device_state(device))

    async def _async_wait_for_speed(self, speed: int) -> bool:
        """Wait until the cloud cache reports a wind speed."""
        if self._current_speed() == speed:
            return True
        for _ in range(_SPEED_REFRESH_ATTEMPTS):
            await asyncio.sleep(_SPEED_REFRESH_DELAY)
            await self.coordinator.async_request_refresh()
            if self._current_speed() == speed:
                return True
        return False


def _speed_from_percentage(percentage: int | None) -> int | None:
    """Return Konke wind speed for a Home Assistant fan percentage."""
    if percentage is None or percentage <= 0:
        return None
    closest_percentage = min(
        _PERCENTAGE_TO_SPEED,
        key=lambda item: abs(item - percentage),
    )
    return _PERCENTAGE_TO_SPEED[closest_percentage]


def _speed_from_state(state: dict[str, Any]) -> int | None:
    """Return normalized Konke wind speed from state."""
    return int_from_state(state, "windSpeed")


def _mode_from_state(state: dict[str, Any]) -> int | None:
    """Return normalized Konke work mode from state."""
    return int_from_state(state, "workMode")
