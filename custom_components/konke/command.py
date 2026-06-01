"""Command helpers for Konke Smart devices."""

from __future__ import annotations

from typing import Any

from .exceptions import KonkeCommandError


ACTION_TURN_OFF = "TurnOff"


def build_device_action_body(
    *,
    user_device_id: str | int,
    action_name: str,
    extension: dict[str, Any] | str | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a request body for the Konke device action endpoint."""
    try:
        normalized_user_device_id = int(user_device_id)
    except (TypeError, ValueError) as err:
        raise KonkeCommandError("Device action requires a numeric userDeviceId") from err

    body: dict[str, Any] = {
        "userDeviceId": normalized_user_device_id,
        "name": action_name,
    }
    if extension is not None:
        body["extension"] = extension
    if extra:
        body.update(extra)
    return body


def air_conditioner_turn_off_action(device: dict[str, Any]) -> tuple[int, str]:
    """Return action details for turning off an air conditioner."""
    user_device_id = device.get("userDeviceId")
    if user_device_id is None:
        raise KonkeCommandError("Air conditioner device missing userDeviceId")
    try:
        return int(user_device_id), ACTION_TURN_OFF
    except (TypeError, ValueError) as err:
        raise KonkeCommandError("Air conditioner userDeviceId is not numeric") from err
