"""Tests for Konke coordinator authentication policy."""

from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock

import hass_shim  # noqa: F401

from custom_components.konke.const import CONF_ALLOW_PASSWORD_REAUTH
from custom_components.konke.coordinator import KonkeDataUpdateCoordinator
from custom_components.konke.exceptions import KonkeAuthError


class CoordinatorAuthTest(unittest.IsolatedAsyncioTestCase):
    """Tests for password reauthentication guardrails."""

    async def test_password_reauth_disabled_by_default(self) -> None:
        """Stored passwords are not used for background login by default."""
        coordinator = _coordinator(options={})
        coordinator.client.refresh_access_token = AsyncMock(
            side_effect=KonkeAuthError("bad token")
        )
        coordinator.client.login = AsyncMock()

        self.assertFalse(await coordinator.async_refresh_auth())
        coordinator.client.login.assert_not_called()

    async def test_password_reauth_requires_explicit_option(self) -> None:
        """Stored passwords are only used when explicitly enabled."""
        coordinator = _coordinator(options={CONF_ALLOW_PASSWORD_REAUTH: True})
        coordinator.client.refresh_access_token = AsyncMock(
            side_effect=KonkeAuthError("bad token")
        )
        coordinator.client.login = AsyncMock(
            return_value={
                "data": {
                    "userToken": {
                        "accessToken": "new-access",
                        "refreshToken": "new-refresh",
                    }
                }
            }
        )

        self.assertTrue(await coordinator.async_refresh_auth())
        coordinator.client.login.assert_awaited_once()


def _coordinator(*, options: dict) -> KonkeDataUpdateCoordinator:
    hass = SimpleNamespace(
        config_entries=SimpleNamespace(async_update_entry=lambda *args, **kwargs: None)
    )
    entry = SimpleNamespace(
        data={
            "username": "user",
            "password": "password",
            "refresh_token": "refresh-token",
        },
        options=options,
    )
    client = SimpleNamespace(
        access_token="old-access",
        refresh_token="refresh-token",
        extract_token_payload=lambda payload: {
            "access_token": payload["data"]["userToken"]["accessToken"],
            "refresh_token": payload["data"]["userToken"]["refreshToken"],
        },
        expires_at_from_payload=lambda payload: None,
    )
    return KonkeDataUpdateCoordinator(hass, entry, client)
