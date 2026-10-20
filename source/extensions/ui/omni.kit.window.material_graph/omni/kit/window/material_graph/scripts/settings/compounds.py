"""Implement material graph extension logic for `settings/compounds.py`."""

from pathlib import Path
from typing import Iterable, List, Optional, Union

import carb
import carb.settings
import carb.tokens

from ..config.logging import logger
from . import utils

# pylint: disable=protected-access


def _resolve_token(path: str) -> str:
    """Execute resolve token behavior for material graph workflows."""

    token = carb.tokens.get_tokens_interface()
    if not path:
        return ""
    resolved = token.resolve(path)
    if not resolved:
        logger.warning("token resolution failed for compound path: %s", path)
    return resolved


def _sanitize_compound_paths(paths: Optional[Union[str, Iterable[str]]], *, log_invalid: bool = False) -> List[str]:
    """Execute sanitize compound paths behavior for material graph workflows."""

    if paths is None:
        return []
    if isinstance(paths, str):
        values: Iterable[str] = [paths]
    elif isinstance(paths, Iterable):
        values = paths
    else:
        values = [paths]

    sanitized: List[str] = []
    for value in values:
        if not isinstance(value, str) or not value:
            if log_invalid:
                logger.warning("invalid compound path (%s): %s", utils.COMPOUND_PATHS, value)
            continue
        resolved = _resolve_token(value)
        if not resolved or not utils.is_existing_path(resolved):
            if log_invalid:
                logger.warning("compound path does not exist (%s): %s", utils.COMPOUND_PATHS, value)
            continue
        if resolved not in sanitized:
            sanitized.append(resolved)
    return sanitized


def _get_raw_compound_paths() -> List[str]:
    """Execute get raw compound paths behavior for material graph workflows."""

    settings = carb.settings.get_settings()
    raw = settings.get(utils.COMPOUND_PATHS)
    if raw is None:
        # Carbonite reads an empty string array back as ``None``.  Preserve the
        # separate authored-empty marker so this state is not confused with an
        # uninitialized setting.
        if settings.get_as_bool(utils.COMPOUND_PATHS_EXPLICIT_EMPTY):
            return []
        raw = [utils.COMPOUND_DEFAULT_PATH]
    return raw if isinstance(raw, list) else [raw]


def ensure_compound_paths_initialized() -> None:
    """Execute ensure compound paths initialized behavior for material graph workflows."""

    settings = carb.settings.get_settings()
    raw = settings.get(utils.COMPOUND_PATHS)
    if raw is not None or settings.get_as_bool(utils.COMPOUND_PATHS_EXPLICIT_EMPTY):
        return
    resolved_default = _resolve_token(utils.COMPOUND_DEFAULT_PATH)
    if resolved_default:
        if "://" not in resolved_default:
            try:
                Path(resolved_default).mkdir(parents=True, exist_ok=True)
            except OSError as exc:
                logger.warning("failed to create compound default path: %s (%s)", resolved_default, exc)
        settings.set_string_array(utils.COMPOUND_PATHS, [resolved_default])
        settings.set_bool(utils.COMPOUND_PATHS_EXPLICIT_EMPTY, False)
        return
    settings.set_string_array(utils.COMPOUND_PATHS, [utils.COMPOUND_DEFAULT_PATH])
    settings.set_bool(utils.COMPOUND_PATHS_EXPLICIT_EMPTY, False)


def get_compound_paths() -> List[str]:
    """Execute get compound paths behavior for material graph workflows."""

    return _sanitize_compound_paths(_get_raw_compound_paths())


def set_compound_paths(paths: Optional[Union[str, Iterable[str]]]) -> None:
    """Execute set compound paths behavior for material graph workflows."""

    sanitized = _sanitize_compound_paths(paths, log_invalid=True)
    settings = carb.settings.get_settings()
    settings.set(utils.COMPOUND_PATHS, sanitized)
    settings.set_bool(utils.COMPOUND_PATHS_EXPLICIT_EMPTY, not sanitized)


def add_compound_path(path: str) -> None:
    """Execute add compound path behavior for material graph workflows."""

    current = _get_raw_compound_paths()
    if path not in current:
        current.append(path)
    set_compound_paths(current)


def remove_compound_path(path: str) -> None:
    """Execute remove compound path behavior for material graph workflows."""

    current = _get_raw_compound_paths()
    if path in current:
        current.remove(path)
    set_compound_paths(current)


def clear_compound_paths() -> None:
    """Execute clear compound paths behavior for material graph workflows."""

    set_compound_paths([])
