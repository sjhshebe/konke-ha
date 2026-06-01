"""Tests for Konke diagnostics."""

from __future__ import annotations

import json

import pytest

from custom_components.konke.diagnostics import async_get_config_entry_diagnostics


@pytest.mark.asyncio
async def test_diagnostics_redacts_credentials(
    hass,
    config_entry,
    konke_client_patch,
) -> None:
    """Diagnostics redact sensitive entry data."""
    config_entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    diagnostics = await async_get_config_entry_diagnostics(hass, config_entry)
    encoded = json.dumps(diagnostics, ensure_ascii=False)

    assert "fake-access-token" not in encoded
    assert "fake-refresh-token" not in encoded
    assert diagnostics["entry"]["data"]["access_token"] == "**REDACTED**"
    assert diagnostics["entry"]["data"]["refresh_token"] == "**REDACTED**"
