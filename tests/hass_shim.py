"""Import shim for pure unit tests outside a Home Assistant test runtime."""

from __future__ import annotations

import sys
import types
from enum import Enum
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CUSTOM_COMPONENTS = ROOT / "custom_components"
KONKE = CUSTOM_COMPONENTS / "konke"

custom_components = sys.modules.setdefault(
    "custom_components",
    types.ModuleType("custom_components"),
)
custom_components.__path__ = [str(CUSTOM_COMPONENTS)]

konke = sys.modules.setdefault(
    "custom_components.konke",
    types.ModuleType("custom_components.konke"),
)
konke.__path__ = [str(KONKE)]

homeassistant = sys.modules.setdefault(
    "homeassistant",
    types.ModuleType("homeassistant"),
)
homeassistant.config_entries = sys.modules.setdefault(
    "homeassistant.config_entries",
    types.ModuleType("homeassistant.config_entries"),
)


class _ConfigEntry:
    pass


homeassistant.config_entries.ConfigEntry = _ConfigEntry

homeassistant.const = sys.modules.setdefault(
    "homeassistant.const",
    types.ModuleType("homeassistant.const"),
)
homeassistant.const.CONF_PASSWORD = "password"
homeassistant.const.CONF_USERNAME = "username"


class _Platform(str, Enum):
    CLIMATE = "climate"
    COVER = "cover"
    FAN = "fan"
    LIGHT = "light"
    SCENE = "scene"
    SENSOR = "sensor"
    SWITCH = "switch"


homeassistant.const.Platform = _Platform

homeassistant.core = sys.modules.setdefault(
    "homeassistant.core",
    types.ModuleType("homeassistant.core"),
)


class _HomeAssistant:
    pass


homeassistant.core.HomeAssistant = _HomeAssistant

http_mod = sys.modules.setdefault(
    "aio" + "http",
    types.ModuleType("aio" + "http"),
)


class _AioClientError(Exception):
    pass


class _AioResponse:
    pass


class _AioSession:
    pass


http_mod.ClientError = _AioClientError
http_mod.ClientResponse = _AioResponse
setattr(http_mod, "Client" + "Session", _AioSession)

homeassistant.exceptions = sys.modules.setdefault(
    "homeassistant.exceptions",
    types.ModuleType("homeassistant.exceptions"),
)


class _ConfigEntryAuthFailed(Exception):
    pass


class _HomeAssistantError(Exception):
    pass


homeassistant.exceptions.ConfigEntryAuthFailed = _ConfigEntryAuthFailed
homeassistant.exceptions.HomeAssistantError = _HomeAssistantError

helpers = sys.modules.setdefault(
    "homeassistant.helpers",
    types.ModuleType("homeassistant.helpers"),
)
helpers.entity_platform = sys.modules.setdefault(
    "homeassistant.helpers.entity_platform",
    types.ModuleType("homeassistant.helpers.entity_platform"),
)
helpers.entity_platform.AddEntitiesCallback = object
helpers.entity_registry = sys.modules.setdefault(
    "homeassistant.helpers.entity_registry",
    types.ModuleType("homeassistant.helpers.entity_registry"),
)


class _EntityRegistry:
    def __init__(self) -> None:
        self.removed: list[str] = []

    def async_get_entity_id(self, platform, domain, unique_id):
        return None

    def async_remove(self, entity_id) -> None:
        self.removed.append(entity_id)


helpers.entity_registry.async_get = lambda hass: _EntityRegistry()
helpers.device_registry = sys.modules.setdefault(
    "homeassistant.helpers.device_registry",
    types.ModuleType("homeassistant.helpers.device_registry"),
)


class _DeviceRegistry:
    def async_get_or_create(self, *args, **kwargs):
        return None


helpers.device_registry.async_get = lambda hass: _DeviceRegistry()
helpers.update_coordinator = sys.modules.setdefault(
    "homeassistant.helpers.update_coordinator",
    types.ModuleType("homeassistant.helpers.update_coordinator"),
)


class _DataUpdateCoordinator:
    @classmethod
    def __class_getitem__(cls, item):
        return cls

    def __init__(
        self,
        hass,
        logger,
        *,
        name,
        config_entry=None,
        update_interval=None,
    ) -> None:
        self.hass = hass
        self.logger = logger
        self.name = name
        self.config_entry = config_entry
        self.update_interval = update_interval


class _UpdateFailed(Exception):
    pass


class _CoordinatorEntity:
    @classmethod
    def __class_getitem__(cls, item):
        return cls

    def __init__(self, coordinator) -> None:
        self.coordinator = coordinator

    @property
    def available(self):
        return True


helpers.update_coordinator.CoordinatorEntity = _CoordinatorEntity
helpers.update_coordinator.DataUpdateCoordinator = _DataUpdateCoordinator
helpers.update_coordinator.UpdateFailed = _UpdateFailed

homeassistant.components = sys.modules.setdefault(
    "homeassistant.components",
    types.ModuleType("homeassistant.components"),
)
homeassistant.components.scene = sys.modules.setdefault(
    "homeassistant.components.scene",
    types.ModuleType("homeassistant.components.scene"),
)


class _Scene:
    pass


homeassistant.components.scene.Scene = _Scene
