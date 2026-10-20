"""Shared settings key utilities and token resolution helpers."""

from pathlib import Path
from typing import Callable, Iterable, List, Optional, Tuple, TypeVar, Union

import carb.settings
import carb.tokens
import omni.client
from omni.kit.window.preferences import PERSISTENT_SETTINGS_PREFIX

from ..config.logging import logger

# pylint: disable=broad-exception-caught,unpacking-non-sequence,no-member,global-statement

tokens = carb.tokens.get_tokens_interface()

SETTINGS_PATH = PERSISTENT_SETTINGS_PREFIX + "/app/properties/materialGraph"
TEST_SETTINGS_PATH = SETTINGS_PATH + "Test"


def get_settings_prefix() -> str:
    """Execute get settings prefix behavior for material graph workflows."""

    settings = carb.settings.get_settings()
    test_run = bool(settings.get("/app/isTestRun")) if settings else False
    return (TEST_SETTINGS_PATH if test_run else SETTINGS_PATH) + "/"


SETTINGS_PREFIX = get_settings_prefix()
FORCE_CONNECT = SETTINGS_PREFIX + "forceConnect"
COLOR_NOODLES = SETTINGS_PREFIX + "colorNoodles"
MDL_CATALOG_MODULES = SETTINGS_PREFIX + "plugins/mdl/modules"
SHOW_CATALOG = SETTINGS_PREFIX + "showCatalog"
CONFINE_NODEGRAPHS = SETTINGS_PREFIX + "confineNodeGraphs"
BACKDROP_DEFAULT_COLOR = SETTINGS_PREFIX + "backdropDefaultColor"
BACKDROP_DEFAULT_COLOR_DEFAULT = (0.84, 0.71, 0.29)
CONFINE_BACKDROPS = SETTINGS_PREFIX + "confineBackdrops"
PREVIEW_TEXTURE_INPUT = SETTINGS_PREFIX + "previewTextureInput"
PLUGIN_PROPERTIES_PREFIX = SETTINGS_PREFIX + "plugins/"
COMPOUND_PATHS = SETTINGS_PREFIX + "compoundPaths"
COMPOUND_PATHS_EXPLICIT_EMPTY = SETTINGS_PREFIX + "compoundPathsExplicitEmpty"
COMPOUND_DEFAULT_EXPORT_PATH = SETTINGS_PREFIX + "compoundDefaultExportPath"
COMPOUND_DEFAULT_PATH = tokens.resolve("${data}/nodegraphs")
CATALOG_TEXTURES_PATH = SETTINGS_PREFIX + "catalogTextures"
CATALOG_TEXTURES_PATH_DEFAULT = tokens.resolve("${data}/catalog_textures")
CATALOG_TEXTURE_ICON_SIZE = SETTINGS_PREFIX + "catalogTextureIconSize"
CATALOG_TEXTURE_ICON_SIZE_DEFAULT = 64
DROPPABLE_TEXTURE_FORMATS = SETTINGS_PREFIX + "droppableTextureFormats"
DROPPABLE_TEXTURE_FORMATS_DEFAULT = [
    "bmp",
    "dds",
    "exr",
    "gif",
    "hdr",
    "jpeg",
    "jpg",
    "tif",
    "png",
    "psd",
    "tga",
]
RENDER_CONTEXTS = PERSISTENT_SETTINGS_PREFIX + "/app/hydra/material/renderContexts"

_settings_sync_hook: Optional[Callable[[], None]] = None


def set_settings_sync_hook(hook: Optional[Callable[[], None]]) -> None:
    """Execute set settings sync hook behavior for material graph workflows."""

    global _settings_sync_hook
    _settings_sync_hook = hook


def refresh_settings_prefix() -> None:
    """Execute refresh settings prefix behavior for material graph workflows."""

    global SETTINGS_PREFIX
    global FORCE_CONNECT
    global COLOR_NOODLES
    global MDL_CATALOG_MODULES
    global SHOW_CATALOG
    global CONFINE_NODEGRAPHS
    global BACKDROP_DEFAULT_COLOR
    global CONFINE_BACKDROPS
    global PREVIEW_TEXTURE_INPUT
    global PLUGIN_PROPERTIES_PREFIX
    global COMPOUND_PATHS
    global COMPOUND_PATHS_EXPLICIT_EMPTY
    global COMPOUND_DEFAULT_EXPORT_PATH
    global CATALOG_TEXTURES_PATH
    global CATALOG_TEXTURE_ICON_SIZE
    global DROPPABLE_TEXTURE_FORMATS

    prefix = get_settings_prefix()
    if prefix == SETTINGS_PREFIX:
        return
    old_prefix = SETTINGS_PREFIX
    SETTINGS_PREFIX = prefix
    FORCE_CONNECT = SETTINGS_PREFIX + "forceConnect"
    COLOR_NOODLES = SETTINGS_PREFIX + "colorNoodles"
    MDL_CATALOG_MODULES = SETTINGS_PREFIX + "plugins/mdl/modules"
    SHOW_CATALOG = SETTINGS_PREFIX + "showCatalog"
    CONFINE_NODEGRAPHS = SETTINGS_PREFIX + "confineNodeGraphs"
    BACKDROP_DEFAULT_COLOR = SETTINGS_PREFIX + "backdropDefaultColor"
    CONFINE_BACKDROPS = SETTINGS_PREFIX + "confineBackdrops"
    PREVIEW_TEXTURE_INPUT = SETTINGS_PREFIX + "previewTextureInput"
    PLUGIN_PROPERTIES_PREFIX = SETTINGS_PREFIX + "plugins/"
    COMPOUND_PATHS = SETTINGS_PREFIX + "compoundPaths"
    COMPOUND_PATHS_EXPLICIT_EMPTY = SETTINGS_PREFIX + "compoundPathsExplicitEmpty"
    COMPOUND_DEFAULT_EXPORT_PATH = SETTINGS_PREFIX + "compoundDefaultExportPath"
    CATALOG_TEXTURES_PATH = SETTINGS_PREFIX + "catalogTextures"
    CATALOG_TEXTURE_ICON_SIZE = SETTINGS_PREFIX + "catalogTextureIconSize"
    DROPPABLE_TEXTURE_FORMATS = SETTINGS_PREFIX + "droppableTextureFormats"
    logger.info("settings prefix refreshed: %s -> %s", old_prefix, SETTINGS_PREFIX)
    if _settings_sync_hook:
        _settings_sync_hook()


def get_setting_keys() -> List[str]:
    """Execute get setting keys behavior for material graph workflows."""

    return [
        FORCE_CONNECT,
        COLOR_NOODLES,
        MDL_CATALOG_MODULES,
        SHOW_CATALOG,
        CONFINE_NODEGRAPHS,
        BACKDROP_DEFAULT_COLOR,
        CONFINE_BACKDROPS,
        PREVIEW_TEXTURE_INPUT,
        COMPOUND_PATHS,
        COMPOUND_PATHS_EXPLICIT_EMPTY,
        COMPOUND_DEFAULT_EXPORT_PATH,
        CATALOG_TEXTURES_PATH,
        CATALOG_TEXTURE_ICON_SIZE,
        DROPPABLE_TEXTURE_FORMATS,
        RENDER_CONTEXTS,
    ]


def _get_bool(key: str, default: bool) -> bool:
    """Execute get bool behavior for material graph workflows."""

    settings = carb.settings.get_settings()
    value = settings.get(key)
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    return bool(value)


T = TypeVar("T")


def _coerce_list(value: object) -> List[object]:
    """Execute coerce list behavior for material graph workflows."""

    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        return [value]
    return []


def _get_list(key: str) -> List[object]:
    """Execute get list behavior for material graph workflows."""

    settings = carb.settings.get_settings()
    value = settings.get(key)
    return _coerce_list(value)


def get_bool(key: str, default: bool) -> bool:
    """Execute get bool behavior for material graph workflows."""

    return _get_bool(key, default)


def get_list(key: str) -> List[object]:
    """Execute get list behavior for material graph workflows."""

    return _get_list(key)


def is_existing_path(path: str) -> bool:
    """Execute is existing path behavior for material graph workflows."""

    if not path:
        return False
    try:
        result, _entry = omni.client.stat(path)
        if result == omni.client.Result.OK:
            return True
    except (RuntimeError, ValueError, TypeError, AttributeError) as exc:
        logger.debug("omni.client.stat failed for '%s': %s", path, exc)
    try:
        return Path(path).exists()
    except (RuntimeError, ValueError, TypeError, AttributeError) as exc:
        logger.debug("local path existence check failed for '%s': %s", path, exc)
        return False


def _validate_item(
    validator: Callable[[T], Union[bool, Tuple[bool, Optional[str]]]], value: T
) -> Tuple[bool, Optional[str]]:
    """Execute validate item behavior for material graph workflows."""

    try:
        result = validator(value)
    except (RuntimeError, ValueError, TypeError, AttributeError) as exc:
        return False, f"{value} ({exc})"
    if isinstance(result, tuple):
        return result
    return bool(result), None


def _sanitize_list(
    values: Optional[Union[str, Iterable[T]]],
    validator: Callable[[T], Union[bool, Tuple[bool, Optional[str]]]],
    *,
    log_invalid: bool = False,
    warn_prefix: str = "invalid value",
) -> List[T]:
    """Execute sanitize list behavior for material graph workflows."""

    if values is None:
        return []
    if isinstance(values, str):
        values = [values]
    elif not isinstance(values, Iterable):
        values = [values]
    if not values:
        return []
    sanitized: List[T] = []
    for value in values:
        valid, reason = _validate_item(validator, value)
        if not valid:
            if log_invalid:
                suffix = f": {reason}" if reason else f": {value}"
                logger.warning("%s%s", warn_prefix, suffix)
            continue
        if value not in sanitized:
            sanitized.append(value)
    return sanitized


def normalize_texture_format(value: object) -> str:
    """Normalize a texture extension token (e.g. '.PNG' -> 'png')."""
    if not isinstance(value, str):
        return ""
    normalized = value.strip().lower()
    if normalized.startswith("."):
        normalized = normalized[1:]
    if not normalized:
        return ""
    if not normalized.isalnum():
        return ""
    return normalized


def sanitize_texture_formats(values: Optional[Union[str, Iterable[object]]]) -> List[str]:
    """Return a deduplicated list of valid normalized texture extensions."""

    def _is_valid_format(value: object) -> Tuple[bool, Optional[str]]:
        """Execute is valid format behavior for material graph workflows."""

        normalized = normalize_texture_format(value)
        if not normalized:
            return False, f"invalid texture format token: {value!r}"
        return True, None

    sanitized = _sanitize_list(
        values,
        _is_valid_format,
        log_invalid=True,
        warn_prefix="invalid texture format",
    )
    normalized_values = [normalize_texture_format(value) for value in sanitized]
    deduped: List[str] = []
    for value in normalized_values:
        if value and value not in deduped:
            deduped.append(value)
    return deduped
