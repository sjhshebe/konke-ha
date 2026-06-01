"""Tests for Konke scene entity filtering."""

from __future__ import annotations

import unittest

import hass_shim  # noqa: F401

from custom_components.konke.scene import (
    _scene_ids_for_entities,
    _should_create_scene_entity,
)


class SceneTest(unittest.TestCase):
    """Tests for scene helpers."""

    def test_multicontrol_scenes_are_not_exposed(self) -> None:
        """Internal multi-control scenes should not become HA scene entities."""
        self.assertFalse(_should_create_scene_entity({"sceneType": "MultiControl"}))
        self.assertFalse(_should_create_scene_entity({"sceneType": "multicontrol"}))

    def test_normal_scenes_are_exposed(self) -> None:
        """Normal and external scenes stay visible."""
        self.assertTrue(_should_create_scene_entity({"sceneType": "Normal"}))
        self.assertTrue(_should_create_scene_entity({"sceneType": "ExternalScene"}))
        self.assertTrue(_should_create_scene_entity({}))

    def test_scene_ids_filter_internal_scenes(self) -> None:
        """Only user-facing scenes are returned for entity setup."""
        self.assertEqual(
            _scene_ids_for_entities(
                {
                    "20": {"sceneType": "MultiControl"},
                    "3": {"sceneType": "Normal"},
                    "11": {"sceneType": "ExternalScene"},
                }
            ),
            ["3", "11"],
        )
