"""Tests for Konke cloud API request constants."""

from __future__ import annotations

import unittest

import hass_shim  # noqa: F401

from custom_components.konke.api import _SCENE_TYPES_FOR_SYNC


class ApiTest(unittest.TestCase):
    """Tests for API request choices."""

    def test_scene_sync_does_not_request_internal_multi_control(self) -> None:
        """Scene sync should only request user-facing scene types."""
        self.assertEqual(_SCENE_TYPES_FOR_SYNC, "Normal,ExternalScene")
        self.assertNotIn("MultiControl", _SCENE_TYPES_FOR_SYNC)
