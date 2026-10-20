"""Implement material graph extension logic for `plugins/impl/mdl/settings.py`."""

from typing import Iterable, List, Optional, Union

from pxr import Ar

from ....config.logging import logger
from ....settings.plugins import get_plugin_property, set_plugin_property

# pylint: disable=broad-exception-caught,no-member

MDL_PLUGIN_NAME = "mdl"
MDL_CATALOG_MODULES_KEY = "modules"
MDL_CATALOG_EXCLUDED_ANNOTATIONS_KEY = "catalogExcludedAnnotations"


def _is_valid_mdl_path(path: str) -> bool:
    """Return True if path is a non-empty string ending in .mdl."""
    if not isinstance(path, str) or not path:
        return False
    return path.lower().endswith(".mdl")


def _can_resolve_mdl_path(path: str) -> bool:
    """Return True if the MDL path can be resolved by the asset resolver."""
    try:
        resolved = Ar.GetResolver().Resolve(path)
    except (RuntimeError, ValueError, TypeError, AttributeError) as exc:
        logger.debug("MDL path resolve failed path=%s: %s", path, exc)
        resolved = ""
    return bool(resolved)


def _sanitize_mdl_modules(paths: Optional[Union[str, Iterable[str]]], *, log_invalid: bool = False) -> List[str]:
    """Filter and validate MDL module paths; return resolvable .mdl paths."""
    if paths is None:
        return []
    if isinstance(paths, str):
        values: Iterable[object] = [paths]
    elif isinstance(paths, Iterable):
        values = paths
    else:
        values = [paths]

    sanitized: List[str] = []
    for value in values:
        if not _is_valid_mdl_path(value):
            if log_invalid:
                logger.warning("invalid MDL module path: %s", value)
            continue
        if not _can_resolve_mdl_path(value):
            if log_invalid:
                logger.warning("MDL module path cannot be resolved: %s", value)
            continue
        if value not in sanitized:
            sanitized.append(value)
    return sanitized


def get_mdl_catalog_modules() -> List[str]:
    """Return the list of MDL catalog module paths from settings."""
    modules = get_plugin_property(MDL_PLUGIN_NAME, MDL_CATALOG_MODULES_KEY, [])
    sanitized = _sanitize_mdl_modules(modules, log_invalid=True)
    if sanitized != modules:
        set_plugin_property(MDL_PLUGIN_NAME, MDL_CATALOG_MODULES_KEY, sanitized)
    return sanitized


def set_mdl_catalog_modules(paths: Optional[Union[str, Iterable[str]]]) -> None:
    """Persist sanitized MDL catalog module paths to settings."""
    sanitized = _sanitize_mdl_modules(paths, log_invalid=True)
    set_plugin_property(MDL_PLUGIN_NAME, MDL_CATALOG_MODULES_KEY, sanitized)


def add_mdl_catalog_module(path: str) -> None:
    """Add an MDL module path to the catalog if valid and resolvable."""
    if not _is_valid_mdl_path(path):
        logger.warning("invalid MDL module path: %s", path)
        return
    if not _can_resolve_mdl_path(path):
        logger.warning("MDL module path cannot be resolved: %s", path)
        return
    module_asset_paths = get_mdl_catalog_modules()
    if path not in module_asset_paths:
        module_asset_paths.append(path)
        set_mdl_catalog_modules(module_asset_paths)


def remove_mdl_catalog_module(path: str) -> None:
    """Remove an MDL module path from the catalog settings."""
    if not _is_valid_mdl_path(path):
        logger.warning("invalid MDL module path: %s", path)
        return
    module_asset_paths = get_mdl_catalog_modules()
    if path in module_asset_paths:
        module_asset_paths.remove(path)
        set_mdl_catalog_modules(module_asset_paths)
