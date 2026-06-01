"""Runtime option helpers for Konke Smart config entries."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from typing import Any, Mapping

from homeassistant.config_entries import ConfigEntry

from .const import (
    CONF_ALLOW_PASSWORD_REAUTH,
    CONF_CREATE_OFFLINE_DEVICE_ENTITIES,
    CONF_CREATE_SCENE_ENTITIES,
    CONF_DEBUG_RAW_COMMAND,
    CONF_SCAN_INTERVAL,
)

DEFAULT_SCAN_INTERVAL_MINUTES = 10
DEFAULT_SCAN_INTERVAL = timedelta(minutes=DEFAULT_SCAN_INTERVAL_MINUTES)
DEFAULT_CREATE_SCENE_ENTITIES = True
DEFAULT_CREATE_OFFLINE_DEVICE_ENTITIES = True
DEFAULT_DEBUG_RAW_COMMAND = False
DEFAULT_ALLOW_PASSWORD_REAUTH = False


@dataclass(frozen=True)
class KonkeOptions:
    """Normalized runtime options stored on a Home Assistant config entry."""

    scan_interval_minutes: int
    create_scene_entities: bool
    create_offline_device_entities: bool
    debug_raw_command: bool
    allow_password_reauth: bool

    @property
    def scan_interval(self) -> timedelta:
        """Return the polling interval as a timedelta."""
        return timedelta(minutes=self.scan_interval_minutes)


def options_from_entry(config_entry: ConfigEntry) -> KonkeOptions:
    """Return normalized options for a config entry."""
    return options_from_mapping(config_entry.options)


def options_from_mapping(options: Mapping[str, Any]) -> KonkeOptions:
    """Return normalized options from an options mapping."""
    return KonkeOptions(
        scan_interval_minutes=_positive_int(
            options.get(CONF_SCAN_INTERVAL),
            DEFAULT_SCAN_INTERVAL_MINUTES,
        ),
        create_scene_entities=_bool_option(
            options.get(CONF_CREATE_SCENE_ENTITIES),
            DEFAULT_CREATE_SCENE_ENTITIES,
        ),
        create_offline_device_entities=_bool_option(
            options.get(CONF_CREATE_OFFLINE_DEVICE_ENTITIES),
            DEFAULT_CREATE_OFFLINE_DEVICE_ENTITIES,
        ),
        debug_raw_command=_bool_option(
            options.get(CONF_DEBUG_RAW_COMMAND),
            DEFAULT_DEBUG_RAW_COMMAND,
        ),
        allow_password_reauth=_bool_option(
            options.get(CONF_ALLOW_PASSWORD_REAUTH),
            DEFAULT_ALLOW_PASSWORD_REAUTH,
        ),
    )


def _positive_int(value: Any, default: int) -> int:
    """Return a positive integer option, falling back to default."""
    try:
        normalized = int(value)
    except (TypeError, ValueError):
        return default
    return normalized if normalized > 0 else default


def _bool_option(value: Any, default: bool) -> bool:
    """Return a boolean option, falling back to default when unset."""
    if value is None:
        return default
    return bool(value)
