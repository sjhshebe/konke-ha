"""Client for the Konke Smart cloud API."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta
from typing import Any

from aiohttp import ClientError, ClientResponse, ClientSession

from .command import (
    ACTION_PAUSE,
    ACTION_SET_MODE,
    ACTION_SET_TEMPERATURE,
    ACTION_SET_WIND_SPEED,
    ACTION_TURN_OFF,
    ACTION_TURN_ON,
    air_conditioner_turn_off_action,
    build_device_action_body,
)
from .profile import (
    ACCOUNT_BASE_URL,
    API_BASE_URL,
    APP_KEY,
    APP_TYPE,
    APP_VERSION,
    DEFAULT_COUNTRY_CODE,
    DEFAULT_LANGUAGE,
    DEFAULT_REGION_ID,
    DEFAULT_TIME_ZONE,
    DEFAULT_VERSION_HEADER,
)
from .exceptions import KonkeApiError, KonkeAuthError, KonkeCannotConnect
from .models import build_device_indexes, summarize_device

_LOGGER = logging.getLogger(__name__)


class KonkeApiClient:
    """Small async client for the Konke Smart cloud API."""

    def __init__(
        self,
        session: ClientSession,
        *,
        access_token: str | None = None,
        refresh_token: str | None = None,
        country_code: str = DEFAULT_COUNTRY_CODE,
        region_id: str = DEFAULT_REGION_ID,
        language: str = DEFAULT_LANGUAGE,
        time_zone: str = DEFAULT_TIME_ZONE,
        version_header: str = DEFAULT_VERSION_HEADER,
    ) -> None:
        """Initialize the client."""
        self._session = session
        self.access_token = access_token or ""
        self.refresh_token = refresh_token or ""
        self.country_code = country_code
        self.region_id = region_id
        self.language = language
        self.time_zone = time_zone
        self.version_header = version_header

    @staticmethod
    def extract_token_payload(payload: dict[str, Any]) -> dict[str, Any]:
        """Extract token fields from a login or refresh response."""
        user_token = payload.get("data", {}).get("userToken", {})
        return {
            "access_token": (
                user_token.get("accessToken")
                or payload.get("data", {}).get("accessToken")
                or payload.get("accessToken")
            ),
            "refresh_token": (
                user_token.get("refreshToken")
                or payload.get("data", {}).get("refreshToken")
                or payload.get("refreshToken")
            ),
            "expires_in": (
                user_token.get("expirIn")
                or user_token.get("expiresIn")
                or user_token.get("expireIn")
                or payload.get("data", {}).get("expirIn")
                or payload.get("data", {}).get("expiresIn")
                or payload.get("expiresIn")
                or payload.get("expires_in")
            ),
        }

    @staticmethod
    def expires_at_from_payload(payload: dict[str, Any]) -> str | None:
        """Return an ISO expiry timestamp from a token response."""
        expires_in = KonkeApiClient.extract_token_payload(payload).get("expires_in")
        try:
            seconds = int(expires_in)
        except (TypeError, ValueError):
            return None
        if seconds <= 0:
            return None
        return (datetime.utcnow() + timedelta(seconds=seconds)).isoformat()

    @property
    def masked_token(self) -> str:
        """Return a redacted token for logs."""
        token = self.access_token
        if len(token) <= 8:
            return "***"
        return f"{token[:4]}...{token[-4:]}"

    def _headers(
        self,
        *,
        home_id: str | int | None = None,
        json_content: bool = False,
        include_token: bool = True,
    ) -> dict[str, str]:
        """Build headers used by the Android app."""
        headers = {
            "appKey": APP_KEY,
            "language": self.language,
            "timeZone": self.time_zone,
            "version": self.version_header,
            "User-Agent": "okhttp/4.2.2",
            "Cache-Control": "no-cache",
            "Content-Type": "application/json"
            if json_content
            else "application/x-www-form-urlencoded",
        }
        if home_id is not None:
            headers["homeId"] = str(home_id)
        if include_token:
            headers["Authorization"] = self.access_token
        return headers

    async def _json_or_error(self, response: ClientResponse) -> dict[str, Any]:
        """Parse a Konke JSON response."""
        text = (await response.read()).decode("utf-8", "replace")
        if response.status in (401, 403):
            raise KonkeAuthError(f"HTTP {response.status}: {text[:200]}")
        if response.status >= 400:
            raise KonkeApiError(f"HTTP {response.status}: {text[:200]}")
        try:
            payload: dict[str, Any] = json.loads(text)
        except json.JSONDecodeError as err:
            raise KonkeApiError(f"Invalid JSON response: {text[:200]}") from err

        code = payload.get("code")
        info = payload.get("info") or payload.get("message") or ""
        if code not in (None, 0, 200):
            if code in (401, 403, 4010, 10001, 10002, 10003) or "token" in str(info).lower():
                raise KonkeAuthError(f"Konke auth failed: {code} {info}")
            raise KonkeApiError(f"Konke API failed: {code} {info}")
        return payload

    async def _request(
        self,
        method: str,
        url: str,
        *,
        home_id: str | int | None = None,
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
        include_token: bool = True,
        account_api: bool = False,
    ) -> dict[str, Any]:
        """Send a request to Konke cloud."""
        base_url = ACCOUNT_BASE_URL if account_api else API_BASE_URL
        full_url = f"{base_url}{url}"
        headers = self._headers(
            home_id=home_id,
            json_content=json_body is not None,
            include_token=include_token,
        )
        try:
            async with self._session.request(
                method,
                full_url,
                headers=headers,
                params=params,
                json=json_body,
                timeout=20,
            ) as response:
                return await self._json_or_error(response)
        except KonkeApiError:
            raise
        except ClientError as err:
            raise KonkeCannotConnect(str(err)) from err

    async def login(
        self,
        username: str,
        password: str,
        *,
        country_code: str = DEFAULT_COUNTRY_CODE,
        region_id: str = DEFAULT_REGION_ID,
    ) -> dict[str, Any]:
        """Login with phone/username and password."""
        self.country_code = country_code
        self.region_id = region_id
        payload = await self._request(
            "POST",
            "/login",
            account_api=True,
            include_token=True,
            json_body={
                "username": username,
                "userPassword": password,
                "appType": APP_TYPE,
                "appVersion": APP_VERSION,
                "countryCode": country_code,
                "regionId": region_id,
            },
        )
        token_payload = self.extract_token_payload(payload)
        token = token_payload.get("access_token")
        if not token:
            raise KonkeAuthError("Login response did not contain accessToken")
        self.access_token = token
        self.refresh_token = token_payload.get("refresh_token") or self.refresh_token
        return payload

    async def refresh_access_token(self) -> dict[str, Any]:
        """Refresh access token when Konke exposes a refresh endpoint.

        The current Android app returns refreshToken on login, but the tested
        public account/API endpoints do not expose a working refresh route. This
        method keeps the client ready for endpoint-compatible responses and
        lets callers fall back to username/password login when it fails.
        """
        if not self.refresh_token:
            raise KonkeAuthError("Missing refresh token")

        candidates = (
            (ACCOUNT_BASE_URL, "/refreshToken", {"refreshToken": self.refresh_token}),
            (ACCOUNT_BASE_URL, "/token/refresh", {"refreshToken": self.refresh_token}),
            (ACCOUNT_BASE_URL, "/token/refreshToken", {"refreshToken": self.refresh_token}),
            (
                API_BASE_URL,
                "/token",
                {"grantType": "refresh_token", "refreshToken": self.refresh_token},
            ),
        )
        last_error: KonkeApiError | None = None
        for base_url, path, body in candidates:
            full_url = f"{base_url}{path}"
            headers = self._headers(home_id="0", json_content=True, include_token=False)
            try:
                async with self._session.post(
                    full_url,
                    headers=headers,
                    json=body,
                    timeout=20,
                ) as response:
                    payload = await self._json_or_error(response)
            except KonkeApiError as err:
                last_error = err
                continue
            except ClientError as err:
                last_error = KonkeCannotConnect(str(err))
                continue

            token_payload = self.extract_token_payload(payload)
            token = token_payload.get("access_token")
            if not token:
                last_error = KonkeAuthError("Refresh response did not contain accessToken")
                continue
            self.access_token = token
            self.refresh_token = token_payload.get("refresh_token") or self.refresh_token
            return payload

        raise last_error or KonkeAuthError("Unable to refresh Konke token")

    async def validate_token(self) -> dict[str, Any]:
        """Validate the current access token and return the home index."""
        if not self.access_token:
            raise KonkeAuthError("Missing access token")
        return await self.fetch_home_index(home_id="0")

    async def fetch_home_index(self, *, home_id: str | int = "0") -> dict[str, Any]:
        """Fetch the app home index."""
        return await self._request(
            "GET",
            "/v2/page/index",
            home_id=home_id,
            params={"synUserHostList": "true"},
        )

    async def fetch_scenes(
        self,
        *,
        home_id: str | int,
        room_id: str | int,
    ) -> list[dict[str, Any]]:
        """Fetch scenes for a room."""
        payload = await self._request(
            "GET",
            "/v2/scene",
            home_id=home_id,
            params={
                "orderByField": "sort",
                "orderByType": "asc",
                "roomId": room_id,
                "sceneTypes": "Normal,ExternalScene,MultiControl",
            },
        )
        page = payload.get("data", {}).get("pagePojo", {})
        scenes = page.get("list") or []
        if not isinstance(scenes, list):
            return []
        return scenes

    async def fetch_scene_detail(
        self,
        *,
        home_id: str | int,
        scene_id: str | int,
    ) -> dict[str, Any]:
        """Fetch scene detail."""
        payload = await self._request(
            "GET",
            f"/scene/{scene_id}",
            home_id=home_id,
            params={"timeZone": self.time_zone},
        )
        scene = payload.get("data", {}).get("scene")
        if not isinstance(scene, dict):
            raise KonkeApiError(f"Scene detail missing scene object: {scene_id}")
        return scene

    async def execute_scene(
        self,
        *,
        home_id: str | int,
        scene_id: str | int,
    ) -> dict[str, Any]:
        """Execute a Konke scene."""
        return await self._request(
            "POST",
            "/scene/action",
            home_id=home_id,
            json_body={"sceneId": int(scene_id)},
        )

    async def control_device(
        self,
        *,
        home_id: str | int,
        user_device_id: str | int,
        action_name: str,
        extension: dict[str, Any] | str | None = None,
        extra: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Control a Konke device action."""
        body = build_device_action_body(
            user_device_id=user_device_id,
            action_name=action_name,
            extension=extension,
            extra=extra,
        )
        return await self._request(
            "POST",
            "/device/action/control",
            home_id=home_id,
            json_body=body,
        )

    async def turn_off_air_conditioner(
        self,
        *,
        home_id: str | int,
        device: dict[str, Any],
    ) -> dict[str, Any]:
        """Turn off a Konke air conditioner device."""
        user_device_id, action_name = air_conditioner_turn_off_action(device)
        return await self.control_device(
            home_id=home_id,
            user_device_id=user_device_id,
            action_name=action_name,
        )

    async def turn_on_device(
        self,
        *,
        home_id: str | int,
        user_device_id: str | int,
    ) -> dict[str, Any]:
        """Turn on a Konke device."""
        return await self.control_device(
            home_id=home_id,
            user_device_id=user_device_id,
            action_name=ACTION_TURN_ON,
        )

    async def turn_off_device(
        self,
        *,
        home_id: str | int,
        user_device_id: str | int,
    ) -> dict[str, Any]:
        """Turn off a Konke device."""
        return await self.control_device(
            home_id=home_id,
            user_device_id=user_device_id,
            action_name=ACTION_TURN_OFF,
        )

    async def pause_device(
        self,
        *,
        home_id: str | int,
        user_device_id: str | int,
    ) -> dict[str, Any]:
        """Pause a Konke device."""
        return await self.control_device(
            home_id=home_id,
            user_device_id=user_device_id,
            action_name=ACTION_PAUSE,
        )

    async def set_device_temperature(
        self,
        *,
        home_id: str | int,
        user_device_id: str | int,
        temperature: float,
    ) -> dict[str, Any]:
        """Set target temperature for a Konke climate device."""
        return await self.control_device(
            home_id=home_id,
            user_device_id=user_device_id,
            action_name=ACTION_SET_TEMPERATURE,
            extension={"value": float(temperature)},
        )

    async def set_device_mode(
        self,
        *,
        home_id: str | int,
        user_device_id: str | int,
        mode: str | int,
    ) -> dict[str, Any]:
        """Set mode for a Konke climate device."""
        return await self.control_device(
            home_id=home_id,
            user_device_id=user_device_id,
            action_name=ACTION_SET_MODE,
            extension={"mode": mode},
        )

    async def set_air_conditioner_fan_speed(
        self,
        *,
        home_id: str | int,
        user_device_id: str | int,
        speed: str,
    ) -> dict[str, Any]:
        """Set fan speed for a Konke air conditioner."""
        return await self.control_device(
            home_id=home_id,
            user_device_id=user_device_id,
            action_name=ACTION_SET_WIND_SPEED,
            extension={"speed": speed},
        )

    async def fetch_devices(
        self,
        *,
        home_id: str | int,
        area_id: str | int,
    ) -> list[dict[str, Any]]:
        """Fetch visible devices in an area."""
        payload = await self._request(
            "GET",
            "/user/device",
            home_id=home_id,
            params={
                "areaId": area_id,
                "isVisible": "true",
                "orderByField": "sort",
                "page": 1,
                "orderByType": "desc",
                "pageSize": 100,
            },
        )
        page = payload.get("data", {}).get("pagePojo", {})
        devices = page.get("list") or []
        if not isinstance(devices, list):
            return []
        return devices

    async def fetch_device_cache(
        self,
        *,
        home_id: str | int,
        area_id: str | int,
    ) -> list[dict[str, Any]]:
        """Fetch current device cache snapshots for an area."""
        payload = await self._request(
            "GET",
            "/user/device/cache",
            home_id=home_id,
            params={"areaId": area_id},
        )
        cache_list = payload.get("data", {}).get("cacheList") or []
        if not isinstance(cache_list, list):
            return []
        return [item for item in cache_list if isinstance(item, dict)]

    @staticmethod
    def extract_home(home_index: dict[str, Any]) -> dict[str, Any]:
        """Extract current home from home index payload."""
        home = home_index.get("data", {}).get("home")
        if isinstance(home, dict) and home.get("homeId"):
            return home

        home_list = home_index.get("data", {}).get("homeList") or []
        for item in home_list:
            if isinstance(item, dict) and item.get("isDefault"):
                return item
        if home_list and isinstance(home_list[0], dict):
            return home_list[0]
        raise KonkeApiError("No home found in Konke account")

    @staticmethod
    def extract_rooms(home: dict[str, Any]) -> list[dict[str, Any]]:
        """Extract rooms from a home object."""
        rooms: list[dict[str, Any]] = []
        for area in home.get("areaList") or []:
            if not isinstance(area, dict):
                continue
            area_id = area.get("areaId")
            area_name = area.get("areaName")
            for room in area.get("roomList") or []:
                if not isinstance(room, dict) or not room.get("roomId"):
                    continue
                item = dict(room)
                item.setdefault("areaId", area_id)
                item.setdefault("areaName", area_name)
                rooms.append(item)
        return rooms

    async def fetch_data(self, *, configured_home_id: str | None = None) -> dict[str, Any]:
        """Fetch all data used by the integration."""
        home_index = await self.fetch_home_index(home_id="0")
        home = self.extract_home(home_index)
        home_id = str(configured_home_id or home["homeId"])
        rooms = self.extract_rooms(home)

        scenes_by_id: dict[str, dict[str, Any]] = {}
        for room in rooms:
            room_id = room.get("roomId")
            if not room_id:
                continue
            try:
                room_scenes = await self.fetch_scenes(home_id=home_id, room_id=room_id)
            except KonkeApiError as err:
                _LOGGER.debug("Failed fetching scenes for room %s: %s", room_id, err)
                continue
            for scene in room_scenes:
                scene_id = scene.get("sceneId")
                if scene_id is None:
                    continue
                item = dict(scene)
                item.setdefault("homeId", int(home_id) if home_id.isdigit() else home_id)
                item.setdefault("roomId", room_id)
                item.setdefault("roomName", room.get("roomName"))
                item.setdefault("areaId", room.get("areaId"))
                item.setdefault("areaName", room.get("areaName"))
                scenes_by_id[str(scene_id)] = item

        devices: list[dict[str, Any]] = []
        for area in home.get("areaList") or []:
            area_id = area.get("areaId") if isinstance(area, dict) else None
            if not area_id:
                continue
            try:
                area_devices = await self.fetch_devices(home_id=home_id, area_id=area_id)
            except KonkeApiError as err:
                _LOGGER.debug("Failed fetching devices for area %s: %s", area_id, err)
                continue
            try:
                area_cache = await self.fetch_device_cache(home_id=home_id, area_id=area_id)
            except KonkeApiError as err:
                _LOGGER.debug("Failed fetching device cache for area %s: %s", area_id, err)
                area_cache = []
            devices.extend(_merge_device_cache(area_devices, area_cache))

        device_indexes = build_device_indexes(devices)
        normalized_devices = device_indexes["devices"]
        return {
            "home": home,
            "rooms": rooms,
            "scenes_by_id": scenes_by_id,
            "devices": devices,
            "normalized_devices": normalized_devices,
            "normalized_devices_by_id": device_indexes["devices_by_id"],
            "entities": device_indexes["entities"],
            "device_ids_by_room_id": device_indexes["device_ids_by_room_id"],
            "child_device_ids_by_parent_id": device_indexes[
                "child_device_ids_by_parent_id"
            ],
            "device_ids_by_capability": device_indexes["device_ids_by_capability"],
            "device_summaries": [
                summarize_device(device) for device in normalized_devices
            ],
            "skipped_devices": device_indexes["skipped_devices"],
        }


def _merge_device_cache(
    devices: list[dict[str, Any]],
    cache_list: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Merge area cache snapshots into visible device payloads."""
    cache_by_id = {
        str(item["userDeviceId"]): item
        for item in cache_list
        if item.get("userDeviceId") is not None
    }
    if not cache_by_id:
        return devices

    merged: list[dict[str, Any]] = []
    for device in devices:
        device_id = device.get("userDeviceId")
        cache = cache_by_id.get(str(device_id)) if device_id is not None else None
        if cache is None:
            merged.append(device)
            continue
        merged.append(_merge_single_device_cache(device, cache))
    return merged


def _merge_single_device_cache(
    device: dict[str, Any],
    cache: dict[str, Any],
) -> dict[str, Any]:
    """Return a device payload with cache-list state merged into cache.extension."""
    merged = dict(device)
    device_cache = merged.get("cache")
    if not isinstance(device_cache, dict):
        device_cache = {}
    else:
        device_cache = dict(device_cache)

    extension = device_cache.get("extension")
    if not isinstance(extension, dict):
        extension = {}
    else:
        extension = dict(extension)

    for key, value in cache.items():
        if key in {"userDeviceId", "roomId"}:
            continue
        extension[key] = value

    if "isOnline" in cache:
        device_cache["isOnline"] = cache["isOnline"]
    if "updateTime" in cache:
        device_cache["updateTime"] = cache["updateTime"]

    device_cache["extension"] = extension
    merged["cache"] = device_cache
    return merged
