"""Tests for Konke integration setup and services."""

from __future__ import annotations

import pytest

from custom_components.konke.const import DOMAIN


@pytest.mark.asyncio
async def test_setup_entry_creates_entities(
    hass,
    config_entry,
    konke_client_patch,
    entity_id_lookup,
) -> None:
    """The integration creates standard HA entities from fixture devices."""
    config_entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    entity_ids = [
        entity_id_lookup("climate", "konke_home-1_climate_1001"),
        entity_id_lookup("climate", "konke_home-1_heating_3001"),
        entity_id_lookup("cover", "konke_home-1_cover_4001"),
        entity_id_lookup("fan", "konke_home-1_fan_5001"),
        entity_id_lookup("scene", "konke_home-1_scene_10"),
    ]
    assert None not in entity_ids
    states = set(hass.states.async_entity_ids())
    assert set(entity_ids) <= states
    assert entity_id_lookup("scene", "konke_home-1_scene_20") is None
    assert DOMAIN in hass.data
    assert config_entry.entry_id in hass.data[DOMAIN]


@pytest.mark.asyncio
async def test_unload_entry_removes_coordinator(
    hass,
    config_entry,
    konke_client_patch,
) -> None:
    """Unloading the integration removes the coordinator."""
    config_entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    assert config_entry.entry_id in hass.data[DOMAIN]

    assert await hass.config_entries.async_unload(config_entry.entry_id)
    await hass.async_block_till_done()
    assert config_entry.entry_id not in hass.data[DOMAIN]


@pytest.mark.asyncio
async def test_services_registered_without_removed_air_conditioner_services(
    hass,
    config_entry,
    konke_client_patch,
) -> None:
    """Only supported Konke domain services are registered."""
    config_entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    assert hass.services.has_service(DOMAIN, "execute_scene")
    assert hass.services.has_service(DOMAIN, "refresh")
    assert hass.services.has_service(DOMAIN, "raw_command")
    assert not hass.services.has_service(DOMAIN, "list_air_conditioners")
    assert not hass.services.has_service(DOMAIN, "turn_off_air_conditioners")


@pytest.mark.asyncio
async def test_execute_scene_service_uses_client(
    hass,
    config_entry,
    konke_client_patch,
) -> None:
    """The execute_scene service calls the Konke client."""
    config_entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    await hass.services.async_call(
        DOMAIN,
        "execute_scene",
        {"scene_id": 10},
        blocking=True,
    )

    assert konke_client_patch.scene_calls == [
        {"home_id": "home-1", "scene_id": "10"}
    ]
