"""Texture catalog metadata helpers for icon roots, paths, and persisted manifests."""

import json
from pathlib import Path
from typing import List, Optional

import carb.settings
import carb.tokens

from .....settings.settings import Settings
from .....settings.utils import CATALOG_TEXTURES_PATH_DEFAULT


def _get_icons_root() -> Optional[str]:
    """Execute get icons root behavior for material graph workflows."""

    settings = carb.settings.get_settings()
    root = settings.get(Settings.CATALOG_TEXTURES_PATH)
    if not isinstance(root, str) or not root:
        root = CATALOG_TEXTURES_PATH_DEFAULT
    if isinstance(root, str) and "${" in root:
        tokens = carb.tokens.get_tokens_interface()
        root = tokens.resolve(root)
    return root


def _groups_path(root: Optional[str]) -> Optional[Path]:
    """Execute groups path behavior for material graph workflows."""

    if not root:
        return None
    return Path(root) / "texture_groups.json"


def _load_groups(root: Optional[str]) -> List[str]:
    """Execute load groups behavior for material graph workflows."""

    path = _groups_path(root)
    if not path or not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    if isinstance(data, list):
        return [str(item) for item in data if item]
    return []


def _save_groups(root: Optional[str], groups: List[str]) -> bool:
    """Execute save groups behavior for material graph workflows."""

    path = _groups_path(root)
    if not path:
        return False
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(groups, indent=2), encoding="utf-8")
    except OSError:
        # Keep this silent to match existing "best effort" metadata behavior.
        return False
    return True
