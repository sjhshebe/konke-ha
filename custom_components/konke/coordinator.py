"""Data coordinator for the Konke Smart integration."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import KonkeApiClient
from .const import (
    CONF_ACCESS_TOKEN,
    CONF_COUNTRY_CODE,
    CONF_HOME_ID,
    CONF_REFRESH_TOKEN,
    CONF_REGION_ID,
    CONF_TOKEN_EXPIRES_AT,
    DOMAIN,
)
from .options import allow_password_reauth_from_entry, options_from_entry
from .profile import (
    DEFAULT_COUNTRY_CODE,
    DEFAULT_REGION_ID,
)
from .exceptions import KonkeApiError, KonkeAuthError

_LOGGER = logging.getLogger(__name__)


class KonkeDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinate Konke Smart data."""

    config_entry: ConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        client: KonkeApiClient,
    ) -> None:
        """Initialize coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            config_entry=config_entry,
            update_interval=options_from_entry(config_entry).scan_interval,
        )
        self.client = client

    def _update_entry_tokens(
        self,
        *,
        access_token: str | None = None,
        refresh_token: str | None = None,
        token_expires_at: str | None = None,
    ) -> None:
        """Persist new tokens on the config entry."""
        updates: dict[str, Any] = {}
        if access_token and access_token != self.config_entry.data.get(CONF_ACCESS_TOKEN):
            updates[CONF_ACCESS_TOKEN] = access_token
        if refresh_token and refresh_token != self.config_entry.data.get(CONF_REFRESH_TOKEN):
            updates[CONF_REFRESH_TOKEN] = refresh_token
        if token_expires_at and token_expires_at != self.config_entry.data.get(
            CONF_TOKEN_EXPIRES_AT
        ):
            updates[CONF_TOKEN_EXPIRES_AT] = token_expires_at
        if updates:
            self.hass.config_entries.async_update_entry(
                self.config_entry,
                data={**self.config_entry.data, **updates},
            )

    def _token_expires_soon(self) -> bool:
        """Return true when the stored token should be renewed proactively."""
        expires_at = self.config_entry.data.get(CONF_TOKEN_EXPIRES_AT)
        if not expires_at:
            return False
        try:
            expires = datetime.fromisoformat(expires_at)
        except (TypeError, ValueError):
            return False
        return datetime.utcnow() + timedelta(days=7) >= expires

    async def async_refresh_auth(self) -> bool:
        """Refresh authorization using refresh token or stored credentials."""
        try:
            if self.config_entry.data.get(CONF_REFRESH_TOKEN):
                payload = await self.client.refresh_access_token()
                self._update_entry_tokens(
                    access_token=self.client.access_token,
                    refresh_token=self.client.refresh_token,
                    token_expires_at=self.client.expires_at_from_payload(payload),
                )
                return True
        except KonkeApiError:
            _LOGGER.debug("Konke refreshToken flow failed")

        if not allow_password_reauth_from_entry(self.config_entry):
            _LOGGER.debug(
                "Konke password reauth is disabled; waiting for explicit reauthentication"
            )
            return False

        return await self._async_login_from_entry()

    async def _async_login_from_entry(self) -> bool:
        """Login again using stored username/password, if available."""
        username = self.config_entry.data.get(CONF_USERNAME)
        password = self.config_entry.data.get(CONF_PASSWORD)
        if not username or not password:
            return False

        payload = await self.client.login(
            username,
            password,
            country_code=self.config_entry.data.get(CONF_COUNTRY_CODE, DEFAULT_COUNTRY_CODE),
            region_id=self.config_entry.data.get(CONF_REGION_ID, DEFAULT_REGION_ID),
        )
        token_payload = self.client.extract_token_payload(payload)
        self._update_entry_tokens(
            access_token=token_payload.get("access_token"),
            refresh_token=token_payload.get("refresh_token"),
            token_expires_at=self.client.expires_at_from_payload(payload),
        )
        return True

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from Konke cloud."""
        try:
            if not self.client.access_token:
                await self.async_refresh_auth()
            elif self._token_expires_soon():
                await self.async_refresh_auth()
            return await self.client.fetch_data(
                configured_home_id=self.config_entry.data.get(CONF_HOME_ID)
            )
        except KonkeAuthError as err:
            try:
                if await self.async_refresh_auth():
                    return await self.client.fetch_data(
                        configured_home_id=self.config_entry.data.get(CONF_HOME_ID)
                    )
            except KonkeApiError as login_err:
                raise ConfigEntryAuthFailed from login_err
            raise ConfigEntryAuthFailed from err
        except KonkeApiError as err:
            raise UpdateFailed(str(err)) from err
