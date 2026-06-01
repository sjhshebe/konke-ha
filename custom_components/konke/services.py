"""Service registration for the Konke Smart integration."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.core import HomeAssistant, ServiceCall, SupportsResponse
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv

from .const import (
    ATTR_ENTRY_ID,
    ATTR_ACTION_NAME,
    ATTR_EXTENSION,
    ATTR_EXTRA,
    ATTR_SCENE_ID,
    ATTR_USER_DEVICE_ID,
    CONF_HOME_ID,
    DOMAIN,
    SERVICE_EXECUTE_SCENE,
    SERVICE_RAW_COMMAND,
    SERVICE_REFRESH,
)
from .coordinator import KonkeDataUpdateCoordinator
from .exceptions import KonkeAuthError
from .options import options_from_entry

SERVICE_EXECUTE_SCENE_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_SCENE_ID): cv.positive_int,
        vol.Optional(ATTR_ENTRY_ID): cv.string,
    }
)

SERVICE_REFRESH_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_ENTRY_ID): cv.string,
    }
)

SERVICE_RAW_COMMAND_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_ENTRY_ID): cv.string,
        vol.Required(ATTR_USER_DEVICE_ID): vol.Any(cv.positive_int, cv.string),
        vol.Required(ATTR_ACTION_NAME): cv.string,
        vol.Optional(ATTR_EXTENSION): vol.Any(dict, cv.string),
        vol.Optional(ATTR_EXTRA): dict,
    }
)


def _get_coordinator(
    hass: HomeAssistant,
    entry_id: str | None,
) -> KonkeDataUpdateCoordinator:
    """Return the requested Konke coordinator."""
    coordinators: dict[str, KonkeDataUpdateCoordinator] = hass.data.get(DOMAIN, {})
    if entry_id:
        coordinator = coordinators.get(entry_id)
        if coordinator is None:
            raise HomeAssistantError(f"Konke entry_id not found: {entry_id}")
        return coordinator

    if len(coordinators) != 1:
        raise HomeAssistantError(
            "More than one Konke entry exists; pass entry_id to select one"
        )
    return next(iter(coordinators.values()))


def _home_id_from_coordinator(coordinator: KonkeDataUpdateCoordinator) -> str | int:
    """Return configured or discovered home id."""
    home_id = coordinator.config_entry.data.get(CONF_HOME_ID)
    if not home_id:
        home_id = coordinator.data.get("home", {}).get("homeId")
    if not home_id:
        raise HomeAssistantError("Konke home_id not found")
    return home_id


async def _async_control_device_with_reauth(
    coordinator: KonkeDataUpdateCoordinator,
    *,
    home_id: str | int,
    user_device_id: str | int,
    action_name: str,
    extension: dict[str, Any] | str | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Send one device command, refreshing auth once if needed."""
    try:
        return await coordinator.client.control_device(
            home_id=home_id,
            user_device_id=user_device_id,
            action_name=action_name,
            extension=extension,
            extra=extra,
        )
    except KonkeAuthError:
        if not await coordinator.async_refresh_auth():
            raise
        return await coordinator.client.control_device(
            home_id=home_id,
            user_device_id=user_device_id,
            action_name=action_name,
            extension=extension,
            extra=extra,
        )


async def _async_execute_scene(hass: HomeAssistant, call: ServiceCall) -> None:
    """Execute a Konke scene by ID."""
    entry_id = call.data.get(ATTR_ENTRY_ID)
    scene_id = call.data[ATTR_SCENE_ID]
    coordinator = _get_coordinator(hass, entry_id)

    home_id = _home_id_from_coordinator(coordinator)
    try:
        await coordinator.client.execute_scene(home_id=home_id, scene_id=scene_id)
    except KonkeAuthError:
        if not await coordinator.async_refresh_auth():
            raise
        await coordinator.client.execute_scene(home_id=home_id, scene_id=scene_id)


async def _async_refresh(hass: HomeAssistant, call: ServiceCall) -> dict:
    """Refresh a Konke config entry on demand."""
    coordinator = _get_coordinator(hass, call.data.get(ATTR_ENTRY_ID))
    await coordinator.async_request_refresh()
    return {
        "entry_id": coordinator.config_entry.entry_id,
        "last_update_success": coordinator.last_update_success,
    }


async def _async_raw_command(hass: HomeAssistant, call: ServiceCall) -> dict:
    """Send a raw Konke action command when debug mode is enabled."""
    coordinator = _get_coordinator(hass, call.data.get(ATTR_ENTRY_ID))
    if options_from_entry(coordinator.config_entry).debug_raw_command is not True:
        raise HomeAssistantError(
            "Konke raw_command is disabled; enable debug_raw_command in integration options"
        )

    home_id = _home_id_from_coordinator(coordinator)
    payload = await _async_control_device_with_reauth(
        coordinator,
        home_id=home_id,
        user_device_id=call.data[ATTR_USER_DEVICE_ID],
        action_name=call.data[ATTR_ACTION_NAME],
        extension=call.data.get(ATTR_EXTENSION),
        extra=call.data.get(ATTR_EXTRA),
    )
    await coordinator.async_request_refresh()
    return {
        "entry_id": coordinator.config_entry.entry_id,
        "user_device_id": str(call.data[ATTR_USER_DEVICE_ID]),
        "action_name": call.data[ATTR_ACTION_NAME],
        "response": payload,
    }


def async_register_services(hass: HomeAssistant) -> None:
    """Register Konke domain services."""
    async def async_execute_scene(call: ServiceCall) -> None:
        """Execute a Konke scene by ID."""
        await _async_execute_scene(hass, call)

    async def async_refresh(call: ServiceCall) -> dict:
        """Refresh Konke data."""
        return await _async_refresh(hass, call)

    async def async_raw_command(call: ServiceCall) -> dict:
        """Send a raw Konke command."""
        return await _async_raw_command(hass, call)

    if not hass.services.has_service(DOMAIN, SERVICE_EXECUTE_SCENE):
        hass.services.async_register(
            DOMAIN,
            SERVICE_EXECUTE_SCENE,
            async_execute_scene,
            schema=SERVICE_EXECUTE_SCENE_SCHEMA,
        )
    if not hass.services.has_service(DOMAIN, SERVICE_REFRESH):
        hass.services.async_register(
            DOMAIN,
            SERVICE_REFRESH,
            async_refresh,
            schema=SERVICE_REFRESH_SCHEMA,
            supports_response=SupportsResponse.ONLY,
        )
    if not hass.services.has_service(DOMAIN, SERVICE_RAW_COMMAND):
        hass.services.async_register(
            DOMAIN,
            SERVICE_RAW_COMMAND,
            async_raw_command,
            schema=SERVICE_RAW_COMMAND_SCHEMA,
            supports_response=SupportsResponse.ONLY,
        )
