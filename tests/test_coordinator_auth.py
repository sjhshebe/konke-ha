"""Tests for Konke coordinator authentication policy."""

from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock

import hass_shim  # noqa: F401

from custom_components.konke.const import (
    AUTH_METHOD_PASSWORD,
    AUTH_METHOD_TOKEN,
    CONF_ALLOW_PASSWORD_REAUTH,
    CONF_AUTH_METHOD,
)
from custom_components.konke.coordinator import KonkeDataUpdateCoordinator
from custom_components.konke.exceptions import KonkeAuthError


class CoordinatorAuthTest(unittest.IsolatedAsyncioTestCase):
    """Tests for password reauthentication guardrails."""

    async def test_password_reauth_enabled_by_default_for_password_entries(self) -> None:
        """Password entries recover with stored credentials by default."""
        coordinator = _coordinator(auth_method=AUTH_METHOD_PASSWORD, options={})
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

    async def test_password_reauth_can_be_disabled_explicitly(self) -> None:
        """Stored passwords are not used when the option is explicitly disabled."""
        coordinator = _coordinator(
            auth_method=AUTH_METHOD_PASSWORD,
            options={CONF_ALLOW_PASSWORD_REAUTH: False},
        )
        coordinator.client.refresh_access_token = AsyncMock(
            side_effect=KonkeAuthError("bad token")
        )
        coordinator.client.login = AsyncMock()

        self.assertFalse(await coordinator.async_refresh_auth())
        coordinator.client.login.assert_not_called()

    async def test_token_entries_do_not_password_reauth_by_default(self) -> None:
        """Token entries do not use stored passwords unless explicitly enabled."""
        coordinator = _coordinator(auth_method=AUTH_METHOD_TOKEN, options={})
        coordinator.client.refresh_access_token = AsyncMock(
            side_effect=KonkeAuthError("bad token")
        )
        coordinator.client.login = AsyncMock()

        self.assertFalse(await coordinator.async_refresh_auth())
        coordinator.client.login.assert_not_called()

    async def test_password_reauth_can_be_enabled_explicitly(self) -> None:
        """Stored passwords can still be enabled explicitly for compatible entries."""
        coordinator = _coordinator(
            auth_method=AUTH_METHOD_TOKEN,
            options={CONF_ALLOW_PASSWORD_REAUTH: True},
        )
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


def _coordinator(*, auth_method: str, options: dict) -> KonkeDataUpdateCoordinator:
    hass = SimpleNamespace(
        config_entries=SimpleNamespace(async_update_entry=lambda *args, **kwargs: None)
    )
    entry = SimpleNamespace(
        data={
            "username": "user",
            "password": "password",
            CONF_AUTH_METHOD: auth_method,
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
