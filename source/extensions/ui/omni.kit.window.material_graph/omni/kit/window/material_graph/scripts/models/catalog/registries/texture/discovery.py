"""Texture discovery helpers for reading texture definitions from local JSON catalogs."""

import json
from pathlib import Path
from typing import Iterator, Optional

from .....config.logging import logger
from ...items.texture import TextureItem


def _is_remote_url(path: str) -> bool:
    """Return True if path is a remote URL (omniverse, http, https)."""
    if not isinstance(path, str):
        return False
    return path.startswith(("omniverse://", "http://", "https://"))


def _iter_texture_jsons(root: str) -> Iterator[dict]:
    """Yield valid JSON payload dicts from *.json files under root."""
    if not root or _is_remote_url(root):
        return []
    try:
        root_path = Path(root)
        if not root_path.exists() or not root_path.is_dir():
            return []
        for entry in root_path.glob("*.json"):
            try:
                payload = json.loads(entry.read_text(encoding="utf-8"))
                if isinstance(payload, dict):
                    yield payload
            except (OSError, json.JSONDecodeError) as exc:
                logger.debug("texture json load failed path=%s: %s", entry, exc)
                continue
    except OSError as exc:
        logger.debug("texture root path failed root=%s: %s", root, exc)
        return []


def _default_name_from_path(path: str) -> str:
    """Extract a display name from a texture file path."""
    try:
        basename = Path(path).name
    except (RuntimeError, ValueError, TypeError, AttributeError) as exc:
        logger.debug("Path.name failed path=%s: %s", path, exc)
        basename = path.split("/")[-1]
    return basename or "Texture"


def _load_texture_item(root: str, payload: dict) -> Optional[TextureItem]:
    """Build a TextureItem from a JSON payload under the given root."""
    source_path = payload.get("source")
    if not isinstance(source_path, str) or not source_path:
        return None
    name = payload.get("name") or _default_name_from_path(source_path)
    icon_name = payload.get("icon") or ""
    group = payload.get("group") or ""
    icon_path = str(Path(root) / icon_name) if icon_name else ""
    if icon_path and not Path(icon_path).exists():
        icon_path = ""
    return TextureItem(name=name, source_path=source_path, icon_path=icon_path, valid=True, group=group)
