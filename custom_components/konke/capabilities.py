"""Konke device capability inference rules."""

from __future__ import annotations

from enum import Enum
from typing import Any, Mapping


class KonkeCapability(str, Enum):
    """Normalized capabilities exposed by Konke devices."""

    AIR_CONDITIONER = "air_conditioner"
    AIR_FRESHER = "air_fresher"
    COVER = "cover"
    FLOOR_HEATING = "floor_heating"
    HVAC_MANAGER = "hvac_manager"
    LIGHT = "light"
    SENSOR = "sensor"
    SWITCH = "switch"
    UNKNOWN = "unknown"


DEVICE_TYPE_MATCHERS: dict[KonkeCapability, dict[str, tuple[str, ...]]] = {
    KonkeCapability.AIR_CONDITIONER: {
        "cate_types": ("AirCondition",),
        "search_terms": ("air_conditional", "fan_coil", "空调"),
    },
    KonkeCapability.FLOOR_HEATING: {
        "cate_types": ("FloorHeating",),
        "search_terms": ("floor_heating",),
    },
    KonkeCapability.AIR_FRESHER: {
        "cate_types": ("AirFresher",),
        "search_terms": ("air_fresher",),
    },
    KonkeCapability.COVER: {
        "cate_types": ("CurtainsMotor",),
        "search_terms": ("curtain",),
    },
    KonkeCapability.HVAC_MANAGER: {
        "cate_types": ("MultiInOneManager",),
        "inner_types": ("multi_one_controller",),
    },
}

PLATFORM_BY_CAPABILITY: dict[KonkeCapability, str] = {
    KonkeCapability.AIR_CONDITIONER: "climate",
    KonkeCapability.FLOOR_HEATING: "climate",
    KonkeCapability.AIR_FRESHER: "fan",
    KonkeCapability.COVER: "cover",
    KonkeCapability.LIGHT: "light",
    KonkeCapability.SENSOR: "sensor",
    KonkeCapability.SWITCH: "switch",
}

POWER_ACTIONS = frozenset({"TurnOn", "TurnOff"})
POWER_ACTION_CAPABILITY_PRIORITY: tuple[KonkeCapability, ...] = (
    KonkeCapability.AIR_CONDITIONER,
    KonkeCapability.FLOOR_HEATING,
    KonkeCapability.AIR_FRESHER,
    KonkeCapability.COVER,
    KonkeCapability.LIGHT,
    KonkeCapability.SWITCH,
)


def capabilities_from_device_profile(
    *,
    cate_type: str | None,
    inner_type: str | None,
    product_id: str | None,
    icon: str | None,
    device_name: str | None,
    action_names: set[str],
) -> set[KonkeCapability]:
    """Infer normalized capabilities from stable device profile fields."""
    searchable = " ".join(
        item
        for item in (cate_type, inner_type, product_id, icon, device_name)
        if item
    )

    capabilities: set[KonkeCapability] = set()
    for capability, matcher in DEVICE_TYPE_MATCHERS.items():
        if cate_type in matcher.get("cate_types", ()):
            capabilities.add(capability)
            continue
        if inner_type in matcher.get("inner_types", ()):
            capabilities.add(capability)
            continue
        if any(term in searchable for term in matcher.get("search_terms", ())):
            capabilities.add(capability)

    if POWER_ACTIONS.issubset(action_names) and not capabilities:
        capabilities.add(KonkeCapability.SWITCH)

    if not capabilities:
        capabilities.add(KonkeCapability.UNKNOWN)
    return capabilities


def capability_for_action(
    action_name: str,
    capabilities: set[KonkeCapability],
) -> KonkeCapability | None:
    """Return the best capability owner for a command name."""
    if len(capabilities) == 1:
        return next(iter(capabilities))
    if action_name in POWER_ACTIONS:
        for capability in POWER_ACTION_CAPABILITY_PRIORITY:
            if capability in capabilities:
                return capability
    return None


def platform_for_capability(capability: KonkeCapability) -> str | None:
    """Return the intended Home Assistant platform for a capability."""
    return PLATFORM_BY_CAPABILITY.get(capability)


def capability_matches_device_type(
    capability: KonkeCapability,
    *,
    cate_type: str | None,
    inner_type: str | None,
    product_id: str | None,
    icon: str | None,
    device_name: str | None,
) -> bool:
    """Return true when a raw device profile matches a capability."""
    return capability in capabilities_from_device_profile(
        cate_type=cate_type,
        inner_type=inner_type,
        product_id=product_id,
        icon=icon,
        device_name=device_name,
        action_names=set(),
    )
