"""Texture registry metadata helpers for validation and timestamp-based cache checks."""

# pylint: disable=relative-beyond-top-level
from typing import Optional, Tuple

from .....config.logging import logger
from .....settings.catalog import Catalog
from .....utils.file_timestamp_cache import FileTimestampCache

_CACHE = FileTimestampCache()


def _normalized_extension(file_path: str) -> str:
    """Return lowercase extension (without dot) for a file path/URL."""
    if not file_path:
        return ""
    clean = file_path.split("?", 1)[0].split("#", 1)[0]
    suffix = clean.rsplit(".", 1)
    if len(suffix) < 2:
        return ""
    return suffix[-1].strip().lower()


def _is_supported_texture_format(file_path: str) -> bool:
    """Return True if file extension is allowed by settings."""
    extension = _normalized_extension(file_path)
    if not extension:
        return False
    supported = set(Catalog.get_supported_texture_formats())
    return extension in supported


def get_texture_info(file_path: str) -> Optional[Tuple[bool, int]]:
    """Return (valid, channel_count) for a texture file path."""
    if not file_path:
        return None
    if not _is_supported_texture_format(file_path):
        logger.debug("texture info skipped unsupported format: path=%s", file_path)
        return None
    cached = _CACHE.get(file_path)
    if cached is not None:
        return cached
    try:
        from ......_textureUtils import get_texture_info as _get_texture_info  # pylint: disable=no-name-in-module
    except (RuntimeError, ValueError, TypeError, AttributeError) as exc:  # pylint: disable=broad-exception-caught
        logger.warning("texture info import failed: path=%s error=%s", file_path, exc)
        return None
    try:
        info = _get_texture_info(file_path)
        if info is not None:
            _CACHE.set(file_path, info)
        return info
    except (RuntimeError, ValueError, TypeError, AttributeError) as exc:  # pylint: disable=broad-exception-caught
        logger.warning("texture info failed: path=%s error=%s", file_path, exc)
        return None


def create_texture_icon(file_path: str, output_path: str, size: int) -> bool:
    """Create an icon image for the texture file."""
    if not file_path or not output_path or size <= 0:
        return False
    if not _is_supported_texture_format(file_path):
        logger.debug("texture icon skipped unsupported format: path=%s", file_path)
        return False
    try:
        from ......_textureUtils import create_texture_icon as _create_texture_icon  # pylint: disable=no-name-in-module
    except (RuntimeError, ValueError, TypeError, AttributeError) as exc:  # pylint: disable=broad-exception-caught
        logger.warning(
            "texture icon import failed: path=%s output=%s error=%s",
            file_path,
            output_path,
            exc,
        )
        return False
    try:
        return bool(_create_texture_icon(file_path, output_path, int(size)))
    except (RuntimeError, ValueError, TypeError, AttributeError) as exc:  # pylint: disable=broad-exception-caught
        logger.warning(
            "texture icon failed: path=%s output=%s size=%s error=%s",
            file_path,
            output_path,
            size,
            exc,
        )
        return False
