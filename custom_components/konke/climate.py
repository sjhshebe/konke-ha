"""Climate platform for Konke Smart."""

from __future__ import annotations

from typing import Any

from homeassistant.components.climate import ClimateEntity
from homeassistant.components.climate.const import (
    ClimateEntityFeature,
    FAN_AUTO,
    FAN_HIGH,
    FAN_LOW,
    FAN_MEDIUM,
    HVACAction,
    HVACMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .capabilities import KonkeCapability
from .command import (
    ACTION_SET_MODE,
    ACTION_SET_TEMPERATURE,
    ACTION_SET_WIND_SPEED,
    ACTION_TURN_OFF,
    ACTION_TURN_ON,
)
from .const import DOMAIN
from .coordinator import KonkeDataUpdateCoordinator
from .entity import KonkeDeviceEntity
from .models import KonkeDevice, current_state_for_raw, maybe_bool
from .options import options_from_entry

_AIR_CONDITIONER_MODE_TO_HVAC = {
    "COLD": HVACMode.COOL,
    "COOL": HVACMode.COOL,
    "DEHUM": HVACMode.DRY,
    "DRY": HVACMode.DRY,
    "HEAT": HVACMode.HEAT,
    "HOT": HVACMode.HEAT,
    "WARM": HVACMode.HEAT,
    "WIND": HVACMode.FAN_ONLY,
    "FAN": HVACMode.FAN_ONLY,
}

_AIR_CONDITIONER_WORK_MODE_TO_HVAC = {
    1: HVACMode.COOL,
    2: HVACMode.HEAT,
    3: HVACMode.FAN_ONLY,
    4: HVACMode.DRY,
}

_AIR_CONDITIONER_HVAC_TO_MODE = {
    HVACMode.COOL: "COLD",
    HVACMode.HEAT: "HOT",
    HVACMode.FAN_ONLY: "WIND",
    HVACMode.DRY: "DEHUM",
}

_AIR_CONDITIONER_FAN_MODES = [FAN_AUTO, FAN_LOW, FAN_MEDIUM, FAN_HIGH]
_AIR_CONDITIONER_FAN_ALIASES = {
    "AUTO": FAN_AUTO,
    "HIGH": FAN_HIGH,
    "LOW": FAN_LOW,
    "MED": FAN_MEDIUM,
    "MIDDLE": FAN_MEDIUM,
    "MID": FAN_MEDIUM,
    "MEDIUM": FAN_MEDIUM,
}
_AIR_CONDITIONER_FAN_TO_KONKE = {
    FAN_AUTO: "AUTO",
    FAN_HIGH: "HIGH",
    FAN_LOW: "LOW",
    FAN_MEDIUM: "MEDIUM",
}

_FLOOR_HEATING_WORK_MODE_TO_HVAC = {
    0: HVACMode.AUTO,
    1: HVACMode.HEAT,
}

_FLOOR_HEATING_HVAC_TO_MODE = {
    HVACMode.AUTO: 0,
    HVACMode.HEAT: 1,
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Konke climate devices from a config entry."""
    coordinator: KonkeDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            KonkeAirConditionerClimate(coordinator, entry, device_id)
            for device_id in _device_ids_for_capability(
                coordinator, entry, KonkeCapability.AIR_CONDITIONER
            )
        ]
        + [
            KonkeFloorHeatingClimate(coordinator, entry, device_id)
            for device_id in _device_ids_for_capability(
                coordinator, entry, KonkeCapability.FLOOR_HEATING
            )
        ]
    )


class KonkeClimateBase(KonkeDeviceEntity, ClimateEntity):
    """Shared behavior for Konke climate entities."""

    _attr_precision = 0.5
    _attr_target_temperature_step = 0.5
    _enable_turn_on_off_backwards_compatibility = False

    def __init__(
        self,
        coordinator: KonkeDataUpdateCoordinator,
        entry: ConfigEntry,
        device_id: str,
        *,
        unique_id_suffix: str,
    ) -> None:
        """Initialize the climate entity."""
        super().__init__(coordinator, entry, device_id)
        self._attr_unique_id = (
            f"{DOMAIN}_{self.konke_home_id}_{unique_id_suffix}_{device_id}"
        )

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
    def current_temperature(self) -> float | None:
        """Return the current temperature."""
        device = self.konke_device
        if device is None:
            return None
        return _float_from_state(
            _current_state(device),
            "curTemp",
            "currentTemperature",
        )

    @property
    def target_temperature(self) -> float | None:
        """Return the target temperature."""
        device = self.konke_device
        if device is None:
            return None
        return _float_from_state(
            _current_state(device),
            "setTemp",
            "temperature",
        )

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

    async def async_turn_on(self) -> None:
        """Turn the climate device on."""
        await self.async_control_device(ACTION_TURN_ON)

    async def async_turn_off(self) -> None:
        """Turn the climate device off."""
        await self.async_control_device(ACTION_TURN_OFF)

    async def _async_set_temperature_value(self, temperature: Any) -> None:
        """Set a numeric target temperature."""
        if temperature is None:
            return
        try:
            value = float(temperature)
        except (TypeError, ValueError) as err:
            raise HomeAssistantError("Konke temperature must be numeric") from err
        await self.async_control_device(
            ACTION_SET_TEMPERATURE,
            extension={"value": value},
        )


class KonkeAirConditionerClimate(KonkeClimateBase):
    """Representation of a Konke air conditioner."""

    _attr_icon = "mdi:air-conditioner"
    _attr_supported_features = (
        ClimateEntityFeature.TURN_ON
        | ClimateEntityFeature.TURN_OFF
        | ClimateEntityFeature.TARGET_TEMPERATURE
        | ClimateEntityFeature.FAN_MODE
    )

    def __init__(
        self,
        coordinator: KonkeDataUpdateCoordinator,
        entry: ConfigEntry,
        device_id: str,
    ) -> None:
        """Initialize the air-conditioner entity."""
        super().__init__(
            coordinator,
            entry,
            device_id,
            unique_id_suffix="climate",
        )

    @property
    def min_temp(self) -> float:
        """Return the minimum supported target temperature."""
        return 16.0

    @property
    def max_temp(self) -> float:
        """Return the maximum supported target temperature."""
        return 30.0

    @property
    def hvac_modes(self) -> list[HVACMode]:
        """Return supported HVAC modes."""
        return [
            HVACMode.OFF,
            HVACMode.COOL,
            HVACMode.HEAT,
            HVACMode.FAN_ONLY,
            HVACMode.DRY,
        ]

    @property
    def hvac_mode(self) -> HVACMode | None:
        """Return the current HVAC mode."""
        device = self.konke_device
        if device is None:
            return HVACMode.OFF
        if device.power_on is False:
            return HVACMode.OFF

        state = _current_state(device)
        mode = _air_conditioner_hvac_mode(state)
        if mode is not None:
            return mode

        if device.power_on is True:
            return HVACMode.COOL
        return HVACMode.OFF

    @property
    def hvac_action(self) -> HVACAction | None:
        """Return the current HVAC action."""
        return _hvac_action_from_mode(self.hvac_mode)

    @property
    def fan_modes(self) -> list[str]:
        """Return supported fan modes."""
        return list(_AIR_CONDITIONER_FAN_MODES)

    @property
    def fan_mode(self) -> str | None:
        """Return the current fan mode."""
        device = self.konke_device
        if device is None:
            return None
        raw_speed = _current_state(device).get("speed") or _current_state(device).get(
            "windSpeed"
        )
        if raw_speed is None:
            return None
        return _AIR_CONDITIONER_FAN_ALIASES.get(str(raw_speed).upper())

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set target temperature."""
        await self._async_set_temperature_value(kwargs.get(ATTR_TEMPERATURE))

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set HVAC mode."""
        if hvac_mode == HVACMode.OFF:
            await self.async_turn_off()
            return

        konke_mode = _AIR_CONDITIONER_HVAC_TO_MODE.get(hvac_mode)
        if konke_mode is None:
            raise HomeAssistantError(
                f"Konke air conditioner does not support HVAC mode: {hvac_mode}"
            )

        if self.hvac_mode == HVACMode.OFF:
            await self.async_control_device(ACTION_TURN_ON, refresh=False)
        await self.async_control_device(
            ACTION_SET_MODE,
            extension={"mode": konke_mode},
        )

    async def async_set_fan_mode(self, fan_mode: str) -> None:
        """Set fan mode."""
        normalized = _AIR_CONDITIONER_FAN_ALIASES.get(str(fan_mode).upper())
        if normalized not in _AIR_CONDITIONER_FAN_MODES:
            raise HomeAssistantError(
                f"Konke air conditioner does not support fan mode: {fan_mode}"
            )
        await self.async_control_device(
            ACTION_SET_WIND_SPEED,
            extension={"speed": _AIR_CONDITIONER_FAN_TO_KONKE[normalized]},
        )


class KonkeFloorHeatingClimate(KonkeClimateBase):
    """Representation of a Konke floor-heating controller."""

    _attr_icon = "mdi:heating-coil"
    _attr_supported_features = (
        ClimateEntityFeature.TURN_ON
        | ClimateEntityFeature.TURN_OFF
        | ClimateEntityFeature.TARGET_TEMPERATURE
    )

    def __init__(
        self,
        coordinator: KonkeDataUpdateCoordinator,
        entry: ConfigEntry,
        device_id: str,
    ) -> None:
        """Initialize the floor-heating entity."""
        super().__init__(
            coordinator,
            entry,
            device_id,
            unique_id_suffix="heating",
        )

    @property
    def min_temp(self) -> float:
        """Return the minimum supported target temperature."""
        return 5.0

    @property
    def max_temp(self) -> float:
        """Return the maximum supported target temperature."""
        return 40.0

    @property
    def hvac_modes(self) -> list[HVACMode]:
        """Return supported HVAC modes."""
        return [HVACMode.OFF, HVACMode.HEAT, HVACMode.AUTO]

    @property
    def hvac_mode(self) -> HVACMode | None:
        """Return the current HVAC mode."""
        device = self.konke_device
        if device is None:
            return HVACMode.OFF
        if device.power_on is False:
            return HVACMode.OFF

        state = _current_state(device)
        power = _power_from_state(state)
        if power is False:
            return HVACMode.OFF

        mode = _floor_heating_hvac_mode(state)
        if mode is not None:
            return mode

        if device.power_on is True:
            return HVACMode.HEAT
        return HVACMode.OFF

    @property
    def hvac_action(self) -> HVACAction | None:
        """Return the current HVAC action."""
        mode = self.hvac_mode
        if mode == HVACMode.OFF:
            return HVACAction.OFF
        if mode == HVACMode.HEAT:
            return HVACAction.HEATING
        if mode == HVACMode.AUTO:
            return HVACAction.IDLE
        return None

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set target temperature."""
        await self._async_set_temperature_value(kwargs.get(ATTR_TEMPERATURE))

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set floor-heating mode."""
        if hvac_mode == HVACMode.OFF:
            await self.async_turn_off()
            return

        konke_mode = _FLOOR_HEATING_HVAC_TO_MODE.get(hvac_mode)
        if konke_mode is None:
            raise HomeAssistantError(
                f"Konke floor heating does not support HVAC mode: {hvac_mode}"
            )

        if self.hvac_mode == HVACMode.OFF:
            await self.async_control_device(ACTION_TURN_ON, refresh=False)
        await self.async_control_device(
            ACTION_SET_MODE,
            extension={"mode": konke_mode},
        )


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


def _power_from_state(state: dict[str, Any]) -> bool | None:
    """Return cached power state from a current-state payload."""
    for key in ("on", "turnOnOff"):
        power = maybe_bool(state.get(key))
        if power is not None:
            return power
    return None


def _air_conditioner_hvac_mode(state: dict[str, Any]) -> HVACMode | None:
    """Return a HA HVAC mode from a Konke air-conditioner state payload."""
    if _power_from_state(state) is False:
        return HVACMode.OFF

    raw_mode = state.get("mode")
    if raw_mode is not None:
        mode = _AIR_CONDITIONER_MODE_TO_HVAC.get(str(raw_mode).upper())
        if mode is not None:
            return mode

    raw_work_mode = state.get("workMode")
    try:
        work_mode = int(raw_work_mode)
    except (TypeError, ValueError):
        return None
    return _AIR_CONDITIONER_WORK_MODE_TO_HVAC.get(work_mode)


def _floor_heating_hvac_mode(state: dict[str, Any]) -> HVACMode | None:
    """Return a HA HVAC mode from a Konke floor-heating state payload."""
    raw_work_mode = state.get("workMode")
    try:
        work_mode = int(raw_work_mode)
    except (TypeError, ValueError):
        return None
    return _FLOOR_HEATING_WORK_MODE_TO_HVAC.get(work_mode)


def _hvac_action_from_mode(mode: HVACMode | None) -> HVACAction | None:
    """Return a generic HA HVAC action from an HVAC mode."""
    if mode == HVACMode.OFF:
        return HVACAction.OFF
    if mode == HVACMode.HEAT:
        return HVACAction.HEATING
    if mode == HVACMode.COOL:
        return HVACAction.COOLING
    if mode == HVACMode.DRY:
        return HVACAction.DRYING
    if mode == HVACMode.FAN_ONLY:
        return HVACAction.FAN
    if mode == HVACMode.AUTO:
        return HVACAction.IDLE
    return None


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
