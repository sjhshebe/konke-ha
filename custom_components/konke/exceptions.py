"""Exceptions for the Konke Smart integration."""

from __future__ import annotations


class KonkeApiError(Exception):
    """Base Konke API error."""


class KonkeAuthError(KonkeApiError):
    """Authentication failed or expired."""


class KonkeCannotConnect(KonkeApiError):
    """Unable to connect to Konke cloud."""


class KonkeUnsupportedDeviceError(KonkeApiError):
    """Device or capability is not supported by this integration."""


class KonkeCommandError(KonkeApiError):
    """A device command could not be built or executed."""
