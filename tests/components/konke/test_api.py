"""Tests for Konke cloud API request constants."""

from __future__ import annotations

from custom_components.konke.api import _SCENE_TYPES_FOR_SYNC


def test_scene_sync_does_not_request_internal_multi_control() -> None:
    """Scene sync should only request user-facing scene types."""
    assert _SCENE_TYPES_FOR_SYNC == "Normal,ExternalScene"
    assert "MultiControl" not in _SCENE_TYPES_FOR_SYNC
