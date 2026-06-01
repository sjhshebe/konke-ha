"""Verified Konke device profiles and protocol mappings."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.const import Platform


@dataclass(frozen=True)
class DeviceProfile:
    """A verified Konke device profile."""

    key: str
    capability: str
    platform: Platform | None = None
    cate_types: tuple[str, ...] = ()
    inner_types: tuple[str, ...] = ()
    product_ids: tuple[str, ...] = ()
    search_terms: tuple[str, ...] = ()


AIR_CONDITIONER_MODE_TO_HVAC_KEY = {
    "COLD": "cool",
    "COOL": "cool",
    "DEHUM": "dry",
    "DRY": "dry",
    "HEAT": "heat",
    "HOT": "heat",
    "WARM": "heat",
    "WIND": "fan_only",
    "FAN": "fan_only",
}
AIR_CONDITIONER_WORK_MODE_TO_HVAC_KEY = {
    1: "cool",
    2: "heat",
    3: "fan_only",
    4: "dry",
}
AIR_CONDITIONER_HVAC_KEY_TO_MODE = {
    "cool": "COLD",
    "heat": "HOT",
    "fan_only": "WIND",
    "dry": "DEHUM",
}
AIR_CONDITIONER_FAN_ALIASES = {
    "AUTO": "auto",
    "HIGH": "high",
    "LOW": "low",
    "MED": "medium",
    "MIDDLE": "medium",
    "MID": "medium",
    "MEDIUM": "medium",
}
AIR_CONDITIONER_FAN_KEY_TO_KONKE = {
    "auto": "AUTO",
    "high": "HIGH",
    "low": "LOW",
    "medium": "MEDIUM",
}

FLOOR_HEATING_WORK_MODE_TO_HVAC_KEY = {
    0: "auto",
    1: "heat",
}
FLOOR_HEATING_HVAC_KEY_TO_MODE = {
    "auto": 0,
    "heat": 1,
}

FRESH_AIR_PRESET_TO_KONKE = {
    "auto": 0,
    "manual": 1,
}
FRESH_AIR_KONKE_MODE_TO_PRESET = {
    0: "auto",
    1: "manual",
}
FRESH_AIR_SPEED_RANGE = range(1, 4)
FRESH_AIR_PERCENTAGE_TO_SPEED = {
    33: 1,
    66: 2,
    100: 3,
}
FRESH_AIR_SPEED_TO_PERCENTAGE = {
    1: 33,
    2: 66,
    3: 100,
}

DEVICE_PROFILES: tuple[DeviceProfile, ...] = (
    DeviceProfile(
        key="air_conditioner",
        capability="air_conditioner",
        platform=Platform.CLIMATE,
        cate_types=("AirCondition",),
        search_terms=("air_conditional", "fan_coil", "空调"),
    ),
    DeviceProfile(
        key="floor_heating",
        capability="floor_heating",
        platform=Platform.CLIMATE,
        cate_types=("FloorHeating",),
        search_terms=("floor_heating",),
    ),
    DeviceProfile(
        key="air_fresher",
        capability="air_fresher",
        platform=Platform.FAN,
        cate_types=("AirFresher",),
        search_terms=("air_fresher",),
    ),
    DeviceProfile(
        key="cover",
        capability="cover",
        platform=Platform.COVER,
        cate_types=("CurtainsMotor",),
        search_terms=("curtain",),
    ),
    DeviceProfile(
        key="hvac_manager",
        capability="hvac_manager",
        cate_types=("MultiInOneManager",),
        inner_types=("multi_one_controller",),
    ),
)

PLATFORM_BY_CAPABILITY = {
    profile.capability: profile.platform.value
    for profile in DEVICE_PROFILES
    if profile.platform is not None
} | {
    "light": Platform.LIGHT.value,
    "sensor": Platform.SENSOR.value,
    "switch": Platform.SWITCH.value,
}


def capabilities_from_profile(
    *,
    cate_type: str | None,
    inner_type: str | None,
    product_id: str | None,
    icon: str | None,
    device_name: str | None,
) -> set[str]:
    """Return capabilities matching a verified device profile."""
    searchable = " ".join(
        item
        for item in (cate_type, inner_type, product_id, icon, device_name)
        if item
    )

    capabilities: set[str] = set()
    for profile in DEVICE_PROFILES:
        if cate_type in profile.cate_types:
            capabilities.add(profile.capability)
            continue
        if inner_type in profile.inner_types:
            capabilities.add(profile.capability)
            continue
        if product_id in profile.product_ids:
            capabilities.add(profile.capability)
            continue
        if any(term in searchable for term in profile.search_terms):
            capabilities.add(profile.capability)
    return capabilities


def profile_for_capability(capability: str) -> DeviceProfile | None:
    """Return the verified profile for a capability."""
    for profile in DEVICE_PROFILES:
        if profile.capability == capability:
            return profile
    return None
