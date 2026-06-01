"""Constants for the Konke Smart integration."""

from __future__ import annotations

from homeassistant.const import Platform

DOMAIN = "konke"

PLATFORMS: list[Platform] = [Platform.SCENE, Platform.CLIMATE]

AUTH_METHOD_TOKEN = "token"
AUTH_METHOD_PASSWORD = "password"

CONF_AUTH_METHOD = "auth_method"
CONF_ACCESS_TOKEN = "access_token"
CONF_REFRESH_TOKEN = "refresh_token"
CONF_TOKEN_EXPIRES_AT = "token_expires_at"
CONF_COUNTRY_CODE = "country_code"
CONF_REGION_ID = "region_id"
CONF_HOME_ID = "home_id"
CONF_HOME_NAME = "home_name"
CONF_USER_ID = "user_id"
CONF_VERSION_HEADER = "version_header"
CONF_SCAN_INTERVAL = "scan_interval"
CONF_CREATE_SCENE_ENTITIES = "create_scene_entities"
CONF_CREATE_OFFLINE_DEVICE_ENTITIES = "create_offline_device_entities"
CONF_DEBUG_RAW_COMMAND = "debug_raw_command"
CONF_ALLOW_PASSWORD_REAUTH = "allow_password_reauth"

SERVICE_EXECUTE_SCENE = "execute_scene"
SERVICE_REFRESH = "refresh"
SERVICE_RAW_COMMAND = "raw_command"
SERVICE_LIST_AIR_CONDITIONERS = "list_air_conditioners"
SERVICE_TURN_OFF_AIR_CONDITIONERS = "turn_off_air_conditioners"
ATTR_SCENE_ID = "scene_id"
ATTR_ENTRY_ID = "entry_id"
ATTR_USER_DEVICE_ID = "user_device_id"
ATTR_ACTION_NAME = "action_name"
ATTR_EXTENSION = "extension"
ATTR_EXTRA = "extra"
ATTR_DRY_RUN = "dry_run"
ATTR_INCLUDE_OFFLINE = "include_offline"
ATTR_ONLY_ON = "only_on"
ATTR_INCLUDE_ROOM_NAMES = "include_room_names"
ATTR_EXCLUDE_ROOM_NAMES = "exclude_room_names"
ATTR_INCLUDE_ROOM_IDS = "include_room_ids"
ATTR_EXCLUDE_ROOM_IDS = "exclude_room_ids"
