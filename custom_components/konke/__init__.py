"""Konke Smart integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import KonkeApiClient
from .const import (
    CONF_ACCESS_TOKEN,
    CONF_COUNTRY_CODE,
    CONF_REFRESH_TOKEN,
    CONF_REGION_ID,
    CONF_VERSION_HEADER,
    DOMAIN,
    PLATFORMS,
)
from .profile import (
    DEFAULT_COUNTRY_CODE,
    DEFAULT_REGION_ID,
    DEFAULT_VERSION_HEADER,
)
from .coordinator import KonkeDataUpdateCoordinator
from .registry import async_register_konke_devices
from .services import async_register_services


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the Konke Smart integration."""
    hass.data.setdefault(DOMAIN, {})
    async_register_services(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Konke Smart from a config entry."""
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    session = async_get_clientsession(hass)
    client = KonkeApiClient(
        session,
        access_token=entry.data.get(CONF_ACCESS_TOKEN),
        refresh_token=entry.data.get(CONF_REFRESH_TOKEN),
        country_code=entry.data.get(CONF_COUNTRY_CODE, DEFAULT_COUNTRY_CODE),
        region_id=entry.data.get(CONF_REGION_ID, DEFAULT_REGION_ID),
        version_header=entry.data.get(CONF_VERSION_HEADER, DEFAULT_VERSION_HEADER),
    )
    coordinator = KonkeDataUpdateCoordinator(hass, entry, client)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    async_register_konke_devices(hass, entry, coordinator)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a Konke Smart config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
    return unload_ok


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload Konke when options change."""
    await hass.config_entries.async_reload(entry.entry_id)
