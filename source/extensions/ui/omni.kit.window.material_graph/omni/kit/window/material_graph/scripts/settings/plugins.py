"""Implement material graph extension logic for `settings/plugins.py`."""

from typing import Any, Dict, Iterable, Optional, TypeVar

import carb.settings

from ..config.logging import logger
from . import utils

# pylint: disable=protected-access


def _is_valid_plugin_key(plugin_name: str, key: str) -> bool:
    """Execute is valid plugin key behavior for material graph workflows."""

    if not isinstance(plugin_name, str) or not plugin_name.strip():
        return False
    if not isinstance(key, str) or not key.strip():
        return False
    if "/" in plugin_name or "/" in key:
        return False
    return True


T = TypeVar("T")
_PLUGIN_PROPERTY_SCHEMAS: Dict[str, Dict[str, Dict[str, Any]]] = {}


def set_plugin_property_schema(plugin_name: str, properties: Iterable[Any]) -> None:
    """Execute set plugin property schema behavior for material graph workflows."""

    if not isinstance(plugin_name, str) or not plugin_name.strip():
        return
    schema: Dict[str, Dict[str, Any]] = {}
    for prop in properties:
        key = prop.key
        if not isinstance(key, str) or not key:
            continue
        schema[key] = {
            "type": prop.type,
            "default": prop.default,
            "allowed_values": prop.allowed_values,
        }
    if schema:
        _PLUGIN_PROPERTY_SCHEMAS[plugin_name] = schema


def clear_plugin_property_schema(plugin_name: str) -> None:
    """Drop plugin property schema for a plugin during shutdown."""
    if not isinstance(plugin_name, str) or not plugin_name.strip():
        return
    _PLUGIN_PROPERTY_SCHEMAS.pop(plugin_name, None)


def _validate_string_type(plugin_name: str, key: str, value: Any, normalized: str) -> bool:
    """Validate schema entries declared with string type names."""
    if normalized in ("bool", "boolean") and not isinstance(value, bool):
        logger.warning(
            "rejected plugin property %s.%s: expected bool, got %s",
            plugin_name,
            key,
            type(value).__name__,
        )
        return False
    if normalized in ("string", "str") and not isinstance(value, str):
        logger.warning(
            "rejected plugin property %s.%s: expected string, got %s",
            plugin_name,
            key,
            type(value).__name__,
        )
        return False
    if normalized in ("string_list", "list"):
        if not isinstance(value, (list, tuple)) or any(not isinstance(item, str) for item in value):
            logger.warning("rejected plugin property %s.%s: expected list[str]", plugin_name, key)
            return False
    return True


def _validate_python_type(plugin_name: str, key: str, value: Any, prop_type: type) -> bool:
    """Validate schema entries declared with concrete Python types."""
    if prop_type is list and not isinstance(value, list):
        logger.warning("rejected plugin property %s.%s: expected list", plugin_name, key)
        return False
    if prop_type is not list and not isinstance(value, prop_type):
        logger.warning(
            "rejected plugin property %s.%s: expected %s, got %s",
            plugin_name,
            key,
            prop_type.__name__,
            type(value).__name__,
        )
        return False
    return True


def _validate_allowed_values(plugin_name: str, key: str, value: Any, allowed_values: Any) -> bool:
    """Validate value membership against allowed-values schema."""
    if allowed_values is None:
        return True
    if isinstance(value, (list, tuple)):
        invalid = [item for item in value if item not in allowed_values]
        if invalid:
            logger.warning("rejected plugin property %s.%s: unsupported values %s", plugin_name, key, invalid)
            return False
        return True
    if value not in allowed_values:
        logger.warning("rejected plugin property %s.%s: unsupported value %s", plugin_name, key, value)
        return False
    return True


def _validate_plugin_property_value(plugin_name: str, key: str, value: Any) -> bool:
    """Execute validate plugin property value behavior for material graph workflows."""

    schema = _PLUGIN_PROPERTY_SCHEMAS.get(plugin_name, {})
    if not schema or key not in schema:
        return True
    prop_schema = schema[key]
    prop_type = prop_schema.get("type")
    allowed_values = prop_schema.get("allowed_values")

    if isinstance(prop_type, str):
        if not _validate_string_type(plugin_name, key, value, prop_type.lower()):
            return False
    elif isinstance(prop_type, type):
        if not _validate_python_type(plugin_name, key, value, prop_type):
            return False

    return _validate_allowed_values(plugin_name, key, value, allowed_values)


def get_plugin_property_key(plugin_name: str, key: str) -> Optional[str]:
    """Execute get plugin property key behavior for material graph workflows."""

    if not _is_valid_plugin_key(plugin_name, key):
        logger.warning("invalid plugin property key: %s/%s", plugin_name, key)
        return None
    return f"{utils.PLUGIN_PROPERTIES_PREFIX}{plugin_name}/{key}"


def get_plugin_property(plugin_name: str, key: str, default: Optional[T] = None) -> Optional[T]:
    """Execute get plugin property behavior for material graph workflows."""

    if not _is_valid_plugin_key(plugin_name, key):
        logger.warning("invalid plugin property key: %s/%s", plugin_name, key)
        return default
    settings = carb.settings.get_settings()
    settings_key = get_plugin_property_key(plugin_name, key)
    if not settings_key:
        return default
    value = settings.get(settings_key)
    if value is None:
        return default
    if not _validate_plugin_property_value(plugin_name, key, value):
        return default
    return value


def set_plugin_property(plugin_name: str, key: str, value: T) -> None:
    """Execute set plugin property behavior for material graph workflows."""

    if not _is_valid_plugin_key(plugin_name, key):
        logger.warning("invalid plugin property key: %s/%s", plugin_name, key)
        return
    if not _validate_plugin_property_value(plugin_name, key, value):
        return
    settings_key = get_plugin_property_key(plugin_name, key)
    if not settings_key:
        return
    settings = carb.settings.get_settings()
    settings.set(settings_key, value)
