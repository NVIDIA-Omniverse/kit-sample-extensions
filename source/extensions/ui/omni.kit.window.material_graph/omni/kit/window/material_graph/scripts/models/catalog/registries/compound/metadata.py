"""Compound registry metadata persistence and file-type utility helpers."""

import json
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

from .....config.logging import logger
from .....settings import utils

_GROUPS_FILENAME = "compound_groups.json"
_COMPOUND_EXTS = (".usd", ".usda", ".usdc")


def _normalize_path(path: str) -> str:
    """Execute normalize path behavior for material graph workflows."""

    return path.replace("\\", "/").rstrip("/").lower()


def _is_compound_file(path: str) -> bool:
    """Execute is compound file behavior for material graph workflows."""

    return isinstance(path, str) and path.lower().endswith(_COMPOUND_EXTS)


def _is_in_compound_paths(path: str, compound_paths: Sequence[str]) -> bool:
    """Execute is in compound paths behavior for material graph workflows."""

    normalized = _normalize_path(path)
    for root in compound_paths:
        root_norm = _normalize_path(root)
        if normalized.startswith(root_norm + "/") or normalized == root_norm:
            return True
    return False


def _get_groups_root() -> Optional[Path]:
    """Execute get groups root behavior for material graph workflows."""

    root = utils.COMPOUND_DEFAULT_PATH
    if not root:
        return None
    try:
        root_path = Path(root)
        root_path.mkdir(parents=True, exist_ok=True)
        return root_path
    except OSError as exc:
        logger.debug("failed to create compound groups root '%s': %s", root, exc)
        return None


def _load_group_metadata() -> Tuple[List[str], Dict[str, Dict[str, str]]]:
    """Execute load group metadata behavior for material graph workflows."""

    root = _get_groups_root()
    if not root:
        return [], {}
    path = root / _GROUPS_FILENAME
    if not path.exists():
        return [], {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        logger.debug("failed to load compound group metadata '%s': %s", path, exc)
        return [], {}
    groups = payload.get("groups", [])
    items = payload.get("items", {})
    if not isinstance(groups, list):
        groups = []
    if not isinstance(items, dict):
        items = {}
    clean_groups = [str(name) for name in groups if isinstance(name, str) and name.strip()]
    clean_items: Dict[str, Dict[str, str]] = {}
    for key, entry in items.items():
        if not isinstance(key, str) or not isinstance(entry, dict):
            continue
        group = entry.get("group") if isinstance(entry.get("group"), str) else ""
        name = entry.get("name") if isinstance(entry.get("name"), str) else ""
        clean_items[key] = {"group": group, "name": name}
    return clean_groups, clean_items


def _save_group_metadata(groups: List[str], items: Dict[str, Dict[str, str]]) -> bool:
    """Execute save group metadata behavior for material graph workflows."""

    root = _get_groups_root()
    if not root:
        return False
    path = root / _GROUPS_FILENAME
    payload = {"groups": list(groups), "items": items}
    try:
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    except OSError as exc:
        logger.warning("failed to save compound groups '%s': %s", path, exc)
        return False
    return True
