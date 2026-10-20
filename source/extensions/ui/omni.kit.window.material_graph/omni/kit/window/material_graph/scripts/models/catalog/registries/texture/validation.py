"""Texture validation helpers for filtering candidate assets into catalog entries."""

import hashlib
from pathlib import Path
from typing import List, Optional

from .....settings.catalog import Catalog
from .....settings.utils import is_existing_path
from ...items.texture import TextureItem
from .info import create_texture_icon


def _texture_id(path: str) -> str:
    """Return a stable hash identifier for a texture path."""
    return hashlib.sha1(path.encode("utf-8")).hexdigest()


def _icon_path_for_source(root: Optional[str], source_path: str) -> str:
    """Return the icon file path for a texture source under the given root."""
    if not root or not source_path:
        return ""
    return str(Path(root) / f"{_texture_id(source_path)}.png")


def _validate_items(items: List[TextureItem], root: Optional[str]) -> List[dict]:
    """Validate texture items and ensure icons exist; return per-item results."""
    results: List[dict] = []
    for item in items:
        valid = is_existing_path(item.source_path)
        icon_path = _icon_path_for_source(root, item.source_path)
        icon_exists = bool(icon_path and Path(icon_path).exists())
        if not icon_exists and valid:
            created = create_texture_icon(item.source_path, icon_path, Catalog.get_texture_icon_size())
            icon_exists = created and Path(icon_path).exists()
        results.append({"item": item, "valid": valid, "icon_path": icon_path if icon_exists else ""})
    return results
