"""Tests for Konke standard Home Assistant platform services."""

from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_climate_turn_off_uses_standard_entity_service(
    hass,
    config_entry,
    konke_client_patch,
    entity_id_lookup,
) -> None:
    """climate.turn_off sends a standard Konke TurnOff action."""
    config_entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    entity_id = entity_id_lookup("climate", "konke_home-1_climate_1001")
    assert entity_id is not None
    await hass.services.async_call(
        "climate",
        "turn_off",
        {"entity_id": entity_id},
        blocking=True,
    )

    assert konke_client_patch.commands[-1] == {
        "home_id": "home-1",
        "user_device_id": "1001",
        "action_name": "TurnOff",
        "extension": None,
        "extra": None,
    }


@pytest.mark.asyncio
async def test_cover_open_uses_standard_entity_service(
    hass,
    config_entry,
    konke_client_patch,
    entity_id_lookup,
) -> None:
    """cover.open_cover sends the verified curtain TurnOn action."""
    config_entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    entity_id = entity_id_lookup("cover", "konke_home-1_cover_4001")
    assert entity_id is not None
    await hass.services.async_call(
        "cover",
        "open_cover",
        {"entity_id": entity_id},
        blocking=True,
    )

    assert konke_client_patch.commands[-1]["user_device_id"] == "4001"
    assert konke_client_patch.commands[-1]["action_name"] == "TurnOn"


@pytest.mark.asyncio
async def test_fan_turn_off_uses_standard_entity_service(
    hass,
    config_entry,
    konke_client_patch,
    entity_id_lookup,
) -> None:
    """fan.turn_off sends the verified fresh-air TurnOff action."""
    config_entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    entity_id = entity_id_lookup("fan", "konke_home-1_fan_5001")
    assert entity_id is not None
    await hass.services.async_call(
        "fan",
        "turn_off",
        {"entity_id": entity_id},
        blocking=True,
    )

    assert konke_client_patch.commands[-1]["user_device_id"] == "5001"
    assert konke_client_patch.commands[-1]["action_name"] == "TurnOff"
