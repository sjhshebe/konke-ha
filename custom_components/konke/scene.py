"""Scene platform for Konke Smart."""

from __future__ import annotations

from typing import Any

from homeassistant.components.scene import Scene
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONF_HOME_ID, DOMAIN
from .coordinator import KonkeDataUpdateCoordinator
from .entity import KonkeEntity
from .options import options_from_entry


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Konke scenes from a config entry."""
    if options_from_entry(entry).create_scene_entities is False:
        return
    coordinator: KonkeDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    scenes = coordinator.data.get("scenes_by_id", {})
    async_add_entities(
        KonkeScene(coordinator, entry, scene_id)
        for scene_id in sorted(scenes, key=lambda item: int(item) if item.isdigit() else item)
    )


class KonkeScene(KonkeEntity, Scene):
    """Representation of a Konke scene."""

    def __init__(
        self,
        coordinator: KonkeDataUpdateCoordinator,
        entry: ConfigEntry,
        scene_id: str,
    ) -> None:
        """Initialize the scene."""
        super().__init__(coordinator, entry)
        self._scene_id = str(scene_id)
        home_id = entry.data.get(CONF_HOME_ID)
        self._attr_unique_id = f"{DOMAIN}_{home_id}_scene_{self._scene_id}"

    @property
    def _scene(self) -> dict[str, Any]:
        """Return latest scene data."""
        return self.coordinator.data.get("scenes_by_id", {}).get(self._scene_id, {})

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return super().available and bool(self._scene)

    @property
    def name(self) -> str:
        """Return the scene name."""
        return self._scene.get("sceneName") or f"Scene {self._scene_id}"

    @property
    def icon(self) -> str | None:
        """Return icon for known scene types."""
        name = self.name
        if "离家" in name:
            return "mdi:home-export-outline"
        if "回家" in name:
            return "mdi:home-import-outline"
        if "空调" in name:
            return "mdi:air-conditioner"
        if "新风" in name:
            return "mdi:fan"
        return "mdi:palette-outline"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return scene attributes."""
        scene = self._scene
        return {
            "scene_id": int(self._scene_id) if self._scene_id.isdigit() else self._scene_id,
            "scene_type": scene.get("sceneType"),
            "manual": scene.get("manual"),
            "home_id": scene.get("homeId"),
            "area_id": scene.get("areaId"),
            "area_name": scene.get("areaName"),
            "room_id": scene.get("roomId"),
            "room_name": scene.get("roomName"),
            "actions": scene.get("actionSimpleV2List") or scene.get("actionList"),
            "result_id": scene.get("resultId"),
        }

    async def async_activate(self, **kwargs: Any) -> None:
        """Activate the Konke scene."""
        home_id = self._entry.data.get(CONF_HOME_ID)
        await self.coordinator.client.execute_scene(
            home_id=home_id,
            scene_id=self._scene_id,
        )
        await self.coordinator.async_request_refresh()
