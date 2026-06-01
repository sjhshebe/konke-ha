"""Konke device to Home Assistant platform mappings."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

from homeassistant.const import Platform

from .air_conditioner import is_air_conditioner
from .capabilities import KonkeCapability
from .models import capabilities_for_raw_device


def has_capability(capability: KonkeCapability) -> Callable[[Mapping[str, Any]], bool]:
    """Return a predicate that matches a normalized Konke capability."""
    return lambda device: capability in capabilities_for_raw_device(device)


@dataclass(frozen=True)
class KonkeDeviceMapping:
    """Description of how a Konke device maps to Home Assistant."""

    key: str
    platform: Platform
    capability: KonkeCapability
    is_match: Callable[[Mapping[str, Any]], bool]


DEVICE_MAPPINGS: tuple[KonkeDeviceMapping, ...] = (
    KonkeDeviceMapping(
        key="air_conditioner",
        platform=Platform.CLIMATE,
        capability=KonkeCapability.AIR_CONDITIONER,
        is_match=is_air_conditioner,
    ),
    KonkeDeviceMapping(
        key="floor_heating",
        platform=Platform.CLIMATE,
        capability=KonkeCapability.FLOOR_HEATING,
        is_match=has_capability(KonkeCapability.FLOOR_HEATING),
    ),
    KonkeDeviceMapping(
        key="air_fresher",
        platform=Platform.FAN,
        capability=KonkeCapability.AIR_FRESHER,
        is_match=has_capability(KonkeCapability.AIR_FRESHER),
    ),
    KonkeDeviceMapping(
        key="cover",
        platform=Platform.COVER,
        capability=KonkeCapability.COVER,
        is_match=has_capability(KonkeCapability.COVER),
    ),
    KonkeDeviceMapping(
        key="switch",
        platform=Platform.SWITCH,
        capability=KonkeCapability.SWITCH,
        is_match=has_capability(KonkeCapability.SWITCH),
    ),
)


def platforms_for_device(device: Mapping[str, Any]) -> set[Platform]:
    """Return HA platforms that can represent a Konke device."""
    return {
        mapping.platform
        for mapping in DEVICE_MAPPINGS
        if mapping.is_match(device)
    }
