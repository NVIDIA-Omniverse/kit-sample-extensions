"""Implement material graph extension logic for `models/catalog/registries/texture/registry.py`."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Callable, List, Optional

import carb.settings
import omni.kit.app

from .....config.logging import logger
from .....settings.settings import Settings
from .....utils.lifecycle_registry import LifecycleRegistry
from ...items.group import GroupItem
from ...items.texture import TextureItem
from .discovery import _default_name_from_path, _is_remote_url, _iter_texture_jsons, _load_texture_item
from .metadata import _get_icons_root, _load_groups, _save_groups
from .validation import _texture_id, _validate_items

# pylint: disable=no-member,global-statement,broad-exception-caught


def _ensure_local_dir(path: str) -> bool:
    """Execute ensure local dir behavior for material graph workflows."""

    if _is_remote_url(path):
        return False
    try:
        Path(path).mkdir(parents=True, exist_ok=True)
        return True
    except OSError:
        return False


class TextureRegistry:
    """Registry of user-added texture catalog items."""

    def __init__(self) -> None:
        """Initialize instance state for this material graph component."""

        self._items: List[TextureItem] = []
        self._groups: List[str] = []
        self._reload_callback: Optional[Callable[[], None]] = None
        self._lifecycle = LifecycleRegistry()
        self._settings = carb.settings.get_settings()
        self._settings_sub = self._settings.subscribe_to_tree_change_events(
            Settings.CATALOG_TEXTURES_PATH, self._on_settings_changed
        )
        self._lifecycle.add_unsubscribe(self._settings_sub, "unsubscribe_to_tree_change_events")
        self._validation_generation = 0
        self.refresh()

    def destroy(self) -> None:
        """Execute destroy behavior for material graph workflows."""

        if self._lifecycle:
            self._lifecycle.cleanup()
            self._lifecycle = None
        self._settings = None
        self._settings_sub = None
        self._items = []
        self._reload_callback = None

    def set_reload_callback(self, callback: Optional[Callable[[], None]]) -> None:
        """Execute set reload callback behavior for material graph workflows."""

        self._reload_callback = callback

    def refresh(self) -> None:
        """Execute refresh behavior for material graph workflows."""

        root = _get_icons_root()
        logger.info("texture registry refresh start root=%s", root)
        groups = _load_groups(root)
        items: List[TextureItem] = []
        if root:
            for entry in _iter_texture_jsons(root):
                item = _load_texture_item(root, entry)
                if item:
                    items.append(item)
                    if item.group and item.group not in groups:
                        groups.append(item.group)
        self._items = items
        self._groups = groups
        self._schedule_validation()
        logger.info("texture registry refresh end items=%s groups=%s", len(self._items), len(self._groups))
        if self._reload_callback:
            self._reload_callback()

    def get_items(self) -> List[TextureItem]:
        """Execute get items behavior for material graph workflows."""

        return list(self._items)

    def get_groups(self) -> List[str]:
        """Execute get groups behavior for material graph workflows."""

        return list(self._groups)

    def get_item_by_source(self, source_path: str) -> Optional[TextureItem]:
        """Execute get item by source behavior for material graph workflows."""

        for item in self._items:
            if item.source_path == source_path:
                return item
        return None

    def get_group_items(self) -> List[GroupItem]:
        """Execute get group items behavior for material graph workflows."""

        groups: List[GroupItem] = []
        for name in self._groups:
            group = GroupItem(name)
            setattr(group, "is_texture_group", True)
            for item in self._items:
                if item.group == name:
                    group.add_child(item)
            groups.append(group)
        return groups

    def add_texture(self, source_path: str, name: Optional[str] = None) -> Optional[TextureItem]:
        """Execute add texture behavior for material graph workflows."""

        if not source_path:
            return None
        root = _get_icons_root()
        if not root:
            logger.warning(
                "texture registry could not add source '%s': icon root setting '%s' is empty",
                source_path,
                Settings.CATALOG_TEXTURES_PATH,
            )
            return None
        if not _ensure_local_dir(root):
            logger.warning("texture registry: invalid icon root '%s'", root)
            return None
        texture_id = _texture_id(source_path)
        icon_filename = f"{texture_id}.png"
        json_filename = f"{texture_id}.json"
        json_path = Path(root) / json_filename
        display_name = name or _default_name_from_path(source_path)
        payload = {"id": texture_id, "name": display_name, "source": source_path, "icon": icon_filename, "group": ""}
        try:
            json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        except OSError as exc:
            logger.warning("texture registry: failed to write '%s': %s", json_path, exc)
            return None
        item = _load_texture_item(root, payload)
        self._schedule_refresh()
        return item

    def has_texture(self, source_path: str) -> bool:
        """Execute has texture behavior for material graph workflows."""

        if not source_path:
            return False
        for item in self._items:
            if item.source_path == source_path:
                return True
        return False

    def remove_texture(self, item: TextureItem) -> None:
        """Execute remove texture behavior for material graph workflows."""

        if not item:
            return
        root = _get_icons_root()
        if not root:
            return
        self._remove_texture_files(item, root)
        self.refresh()

    def _remove_texture_files(self, item: TextureItem, root: str) -> None:
        """Remove persisted texture metadata and icon files without refreshing."""

        texture_id = _texture_id(item.source_path)
        json_path = Path(root) / f"{texture_id}.json"
        icon_path = Path(root) / f"{texture_id}.png"
        try:
            if json_path.exists():
                json_path.unlink()
        except OSError as exc:
            logger.warning("texture registry: failed to remove '%s': %s", json_path, exc)
        try:
            if icon_path.exists():
                icon_path.unlink()
        except OSError as exc:
            logger.warning("texture registry: failed to remove '%s': %s", icon_path, exc)

    def _write_texture_group(self, item: TextureItem, name: str, root: str) -> bool:
        """Write a texture item's group metadata without refreshing."""

        texture_id = _texture_id(item.source_path)
        json_path = Path(root) / f"{texture_id}.json"
        if not json_path.exists():
            return False
        try:
            payload = json.loads(json_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return False
        payload["group"] = name
        try:
            json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        except OSError as exc:
            logger.warning("texture registry: failed to update '%s': %s", json_path, exc)
            return False
        item.group = name
        return True

    def rename_texture(self, item: TextureItem, new_name: str) -> None:
        """Execute rename texture behavior for material graph workflows."""

        if not item or not new_name:
            return
        root = _get_icons_root()
        if not root:
            return
        texture_id = _texture_id(item.source_path)
        json_path = Path(root) / f"{texture_id}.json"
        if not json_path.exists():
            return
        try:
            payload = json.loads(json_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            payload = {}
        payload["name"] = new_name
        try:
            json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        except OSError as exc:
            logger.warning("texture registry: failed to rename '%s': %s", json_path, exc)
            return
        self.refresh()

    def create_group(self, name: str) -> None:
        """Execute create group behavior for material graph workflows."""

        name = (name or "").strip()
        if not name or name in self._groups:
            return
        self._groups.append(name)
        if not _save_groups(_get_icons_root(), self._groups):
            self.refresh()
            return
        self.refresh()

    def rename_group(self, old_name: str, new_name: str) -> None:
        """Execute rename group behavior for material graph workflows."""

        old_name = (old_name or "").strip()
        new_name = (new_name or "").strip()
        if not old_name or not new_name or old_name == new_name:
            return
        if old_name not in self._groups or new_name in self._groups:
            return
        root = _get_icons_root()
        if not root:
            return
        items_to_move = [item for item in list(self._items) if item.group == old_name]
        moved_items: List[TextureItem] = []
        for item in items_to_move:
            if not self._write_texture_group(item, new_name, root):
                logger.warning("texture registry: failed to rename group '%s' item '%s'", old_name, item.name)
                for moved_item in moved_items:
                    if not self._write_texture_group(moved_item, old_name, root):
                        logger.warning(
                            "texture registry: failed to roll back group rename '%s' item '%s'",
                            old_name,
                            moved_item.name,
                        )
                self.refresh()
                return
            moved_items.append(item)
        renamed_groups = [new_name if name == old_name else name for name in self._groups]
        self._groups = list(dict.fromkeys(renamed_groups))
        if not _save_groups(root, self._groups):
            logger.warning("texture registry: failed to save renamed group manifest '%s'", new_name)
            for item in moved_items:
                if not self._write_texture_group(item, old_name, root):
                    logger.warning(
                        "texture registry: failed to roll back group rename '%s' item '%s'",
                        old_name,
                        item.name,
                    )
            self.refresh()
            return
        self.refresh()

    def remove_group(self, name: str) -> None:
        """Execute remove group behavior for material graph workflows."""

        name = (name or "").strip()
        if not name or name not in self._groups:
            return
        new_groups = [group for group in self._groups if group != name]
        root = _get_icons_root()
        # Save the manifest before deleting files. If later removals fail,
        # refresh re-adds orphaned texture groups from remaining metadata.
        if not root or not _save_groups(root, new_groups):
            self.refresh()
            return
        to_remove = [item for item in self._items if item.group == name]
        for item in to_remove:
            self._remove_texture_files(item, root)
        self._items = [item for item in self._items if item not in to_remove]
        self._groups = new_groups
        self.refresh()

    def assign_group(self, item: TextureItem, name: str, auto_refresh: bool = True) -> bool:
        """Execute assign group behavior for material graph workflows."""

        name = (name or "").strip()
        root = _get_icons_root()
        if not root:
            return False
        if not self._write_texture_group(item, name, root):
            return False
        if name and name not in self._groups:
            self._groups.append(name)
            if not _save_groups(root, self._groups):
                if auto_refresh:
                    self.refresh()
                return False
        if auto_refresh:
            self.refresh()
        return True

    def _on_settings_changed(self, _tree_item: object, _changed_item: object, _event_type: object) -> None:
        """Execute on settings changed behavior for material graph workflows."""

        self.refresh()

    def _schedule_validation(self) -> None:
        """Execute schedule validation behavior for material graph workflows."""

        if not self._lifecycle:
            return
        self._validation_generation += 1
        generation = self._validation_generation
        items = list(self._items)
        root = _get_icons_root()

        async def _validate_async() -> None:
            """Asynchronously execute validate async behavior for material graph workflows."""

            results = await asyncio.to_thread(_validate_items, items, root)
            await omni.kit.app.get_app().next_update_async()
            if generation != self._validation_generation:
                return
            changed = False
            for result in results:
                item = result["item"]
                if not item:
                    continue
                if item.is_valid != result["valid"]:
                    item.set_valid(result["valid"])
                    changed = True
                icon_path = result.get("icon_path", "")
                if icon_path and item.icon_model.get_value_as_string() != icon_path:
                    item.icon_model.set_value(icon_path)
                    changed = True
            if changed and self._reload_callback:
                self._reload_callback()

        self._lifecycle.add_task(_validate_async())

    def _schedule_refresh(self) -> None:
        """Execute schedule refresh behavior for material graph workflows."""

        if not self._lifecycle:
            return

        async def _refresh_async() -> None:
            """Asynchronously execute refresh async behavior for material graph workflows."""

            await omni.kit.app.get_app().next_update_async()
            self.refresh()

        self._lifecycle.add_task(_refresh_async())


_TEXTURE_REGISTRY: Optional[TextureRegistry] = None


def get_texture_registry() -> TextureRegistry:
    """Execute get texture registry behavior for material graph workflows."""

    global _TEXTURE_REGISTRY
    if _TEXTURE_REGISTRY is None:
        _TEXTURE_REGISTRY = TextureRegistry()
    return _TEXTURE_REGISTRY


def destroy_texture_registry() -> None:
    """Destroy and reset the process-global texture registry."""
    global _TEXTURE_REGISTRY
    registry = _TEXTURE_REGISTRY
    _TEXTURE_REGISTRY = None
    if registry is not None:
        registry.destroy()
