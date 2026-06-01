"""Tests for Konke scene entity filtering."""

from __future__ import annotations

from custom_components.konke.scene import (
    _scene_ids_for_entities,
    _should_create_scene_entity,
)


def test_multicontrol_scenes_are_not_exposed() -> None:
    """Internal multi-control scenes should not become HA scene entities."""
    assert not _should_create_scene_entity({"sceneType": "MultiControl"})
    assert not _should_create_scene_entity({"sceneType": "multicontrol"})


def test_normal_scenes_are_exposed() -> None:
    """Normal and external scenes stay visible."""
    assert _should_create_scene_entity({"sceneType": "Normal"})
    assert _should_create_scene_entity({"sceneType": "ExternalScene"})
    assert _should_create_scene_entity({})


def test_scene_ids_filter_internal_scenes() -> None:
    """Only user-facing scenes are returned for entity setup."""
    assert _scene_ids_for_entities(
        {
            "20": {"sceneType": "MultiControl"},
            "3": {"sceneType": "Normal"},
            "11": {"sceneType": "ExternalScene"},
        }
    ) == ["3", "11"]
