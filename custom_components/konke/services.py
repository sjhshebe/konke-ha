"""Service registration for the Konke Smart integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.core import HomeAssistant, ServiceCall, SupportsResponse
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv

from .air_conditioner import filter_air_conditioners, summarize_air_conditioner
from .const import (
    ATTR_DRY_RUN,
    ATTR_ENTRY_ID,
    ATTR_EXCLUDE_ROOM_IDS,
    ATTR_EXCLUDE_ROOM_NAMES,
    ATTR_ACTION_NAME,
    ATTR_EXTENSION,
    ATTR_EXTRA,
    ATTR_INCLUDE_OFFLINE,
    ATTR_INCLUDE_ROOM_IDS,
    ATTR_INCLUDE_ROOM_NAMES,
    ATTR_ONLY_ON,
    ATTR_SCENE_ID,
    ATTR_USER_DEVICE_ID,
    CONF_HOME_ID,
    DOMAIN,
    SERVICE_EXECUTE_SCENE,
    SERVICE_LIST_AIR_CONDITIONERS,
    SERVICE_RAW_COMMAND,
    SERVICE_REFRESH,
    SERVICE_TURN_OFF_AIR_CONDITIONERS,
)
from .coordinator import KonkeDataUpdateCoordinator
from .exceptions import KonkeApiError, KonkeAuthError
from .options import options_from_entry

_LOGGER = logging.getLogger(__name__)

SERVICE_EXECUTE_SCENE_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_SCENE_ID): cv.positive_int,
        vol.Optional(ATTR_ENTRY_ID): cv.string,
    }
)

ROOM_FILTER_SCHEMA = {
    vol.Optional(ATTR_ENTRY_ID): cv.string,
    vol.Optional(ATTR_INCLUDE_ROOM_NAMES, default=[]): vol.All(cv.ensure_list, [cv.string]),
    vol.Optional(ATTR_EXCLUDE_ROOM_NAMES, default=[]): vol.All(cv.ensure_list, [cv.string]),
    vol.Optional(ATTR_INCLUDE_ROOM_IDS, default=[]): vol.All(cv.ensure_list, [cv.string]),
    vol.Optional(ATTR_EXCLUDE_ROOM_IDS, default=[]): vol.All(cv.ensure_list, [cv.string]),
    vol.Optional(ATTR_INCLUDE_OFFLINE, default=False): cv.boolean,
    vol.Optional(ATTR_ONLY_ON, default=False): cv.boolean,
}

SERVICE_LIST_AIR_CONDITIONERS_SCHEMA = vol.Schema(ROOM_FILTER_SCHEMA)

SERVICE_TURN_OFF_AIR_CONDITIONERS_SCHEMA = vol.Schema(
    {
        **ROOM_FILTER_SCHEMA,
        vol.Optional(ATTR_DRY_RUN, default=False): cv.boolean,
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


def _air_conditioners_from_call(
    coordinator: KonkeDataUpdateCoordinator,
    call: ServiceCall,
) -> list[dict]:
    """Return air conditioners matching a service call's filters."""
    return filter_air_conditioners(
        coordinator.data.get("devices", []),
        include_room_names=call.data.get(ATTR_INCLUDE_ROOM_NAMES),
        exclude_room_names=call.data.get(ATTR_EXCLUDE_ROOM_NAMES),
        include_room_ids=call.data.get(ATTR_INCLUDE_ROOM_IDS),
        exclude_room_ids=call.data.get(ATTR_EXCLUDE_ROOM_IDS),
        include_offline=call.data.get(ATTR_INCLUDE_OFFLINE, False),
        only_on=call.data.get(ATTR_ONLY_ON, False),
    )


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


async def _turn_off_one_air_conditioner(
    coordinator: KonkeDataUpdateCoordinator,
    home_id: str | int,
    device: dict,
) -> dict:
    """Turn off one air conditioner, refreshing auth once if needed."""
    try:
        payload = await coordinator.client.turn_off_air_conditioner(
            home_id=home_id,
            device=device,
        )
    except KonkeAuthError:
        if not await coordinator.async_refresh_auth():
            raise
        payload = await coordinator.client.turn_off_air_conditioner(
            home_id=home_id,
            device=device,
        )
    return payload


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


async def _async_list_air_conditioners(
    hass: HomeAssistant,
    call: ServiceCall,
) -> dict:
    """List air conditioners matching room filters."""
    coordinator = _get_coordinator(hass, call.data.get(ATTR_ENTRY_ID))
    devices = _air_conditioners_from_call(coordinator, call)
    return {
        "count": len(devices),
        "devices": [summarize_air_conditioner(device) for device in devices],
    }


async def _async_turn_off_air_conditioners(
    hass: HomeAssistant,
    call: ServiceCall,
) -> dict:
    """Turn off air conditioners matching room filters."""
    coordinator = _get_coordinator(hass, call.data.get(ATTR_ENTRY_ID))
    home_id = _home_id_from_coordinator(coordinator)

    devices = _air_conditioners_from_call(coordinator, call)
    dry_run = call.data.get(ATTR_DRY_RUN, False)
    summaries = [summarize_air_conditioner(device) for device in devices]
    if dry_run:
        return {
            "dry_run": True,
            "count": len(devices),
            "devices": summaries,
        }

    results: list[dict] = []
    failures: list[dict] = []
    for device, summary in zip(devices, summaries, strict=False):
        try:
            payload = await _turn_off_one_air_conditioner(coordinator, home_id, device)
        except KonkeApiError as err:
            failures.append({**summary, "error": str(err)})
            continue
        results.append({**summary, "response": payload})

    await coordinator.async_request_refresh()
    if failures and not results:
        raise HomeAssistantError(
            f"Failed to turn off all Konke air conditioners: {failures}"
        )
    if failures:
        _LOGGER.warning("Some Konke air conditioners failed to turn off: %s", failures)
    return {
        "dry_run": False,
        "count": len(devices),
        "succeeded": len(results),
        "failed": len(failures),
        "devices": summaries,
        "results": results,
        "failures": failures,
    }


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

    async def async_list_air_conditioners(call: ServiceCall) -> dict:
        """List air conditioners matching room filters."""
        return await _async_list_air_conditioners(hass, call)

    async def async_turn_off_air_conditioners(call: ServiceCall) -> dict:
        """Turn off air conditioners matching room filters."""
        return await _async_turn_off_air_conditioners(hass, call)

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
    if not hass.services.has_service(DOMAIN, SERVICE_LIST_AIR_CONDITIONERS):
        hass.services.async_register(
            DOMAIN,
            SERVICE_LIST_AIR_CONDITIONERS,
            async_list_air_conditioners,
            schema=SERVICE_LIST_AIR_CONDITIONERS_SCHEMA,
            supports_response=SupportsResponse.ONLY,
        )
    if not hass.services.has_service(DOMAIN, SERVICE_TURN_OFF_AIR_CONDITIONERS):
        hass.services.async_register(
            DOMAIN,
            SERVICE_TURN_OFF_AIR_CONDITIONERS,
            async_turn_off_air_conditioners,
            schema=SERVICE_TURN_OFF_AIR_CONDITIONERS_SCHEMA,
            supports_response=SupportsResponse.OPTIONAL,
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
