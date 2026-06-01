"""Konke device to Home Assistant platform mappings."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

from homeassistant.const import Platform

from .capabilities import KonkeCapability
from .device_profiles import DEVICE_PROFILES
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


def _profile_mappings() -> tuple[KonkeDeviceMapping, ...]:
    """Return platform mappings for verified device profiles."""
    mappings: list[KonkeDeviceMapping] = []
    for profile in DEVICE_PROFILES:
        if profile.platform is None:
            continue
        capability = KonkeCapability(profile.capability)
        mappings.append(
            KonkeDeviceMapping(
                key=profile.key,
                platform=profile.platform,
                capability=capability,
                is_match=has_capability(capability),
            )
        )
    return tuple(mappings)


DEVICE_MAPPINGS: tuple[KonkeDeviceMapping, ...] = (
    *_profile_mappings(),
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
