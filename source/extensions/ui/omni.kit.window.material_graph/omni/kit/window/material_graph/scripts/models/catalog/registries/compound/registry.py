"""Compound registry state, watchers, and cache refresh lifecycle management."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional

import carb.settings
import omni.client
from carb.eventdispatcher import get_eventdispatcher
from omni.kit.helper.file_utils import FILE_SAVED_GLOBAL_EVENT

from .....config.logging import logger
from .....settings.settings import Settings
from .....utils.lifecycle_registry import LifecycleRegistry
from ...items.compound import CompoundItem
from ...items.group import GroupItem
from .discovery import _compound_key, _iter_compound_files, _load_compounds
from .metadata import _is_compound_file, _is_in_compound_paths, _load_group_metadata, _save_group_metadata

# pylint: disable=no-member,global-statement,unpacking-non-sequence,no-name-in-module


def _merge_group_names(groups: List[str], items: List[CompoundItem]) -> List[str]:
    """Execute merge group names behavior for material graph workflows."""

    merged = [name for name in groups if name]
    for item in items:
        if item.group and item.group not in merged:
            merged.append(item.group)
    return merged


class CompoundRegistry:
    """Registry of compound nodes discovered from USD files."""

    def __init__(self) -> None:
        """Initialize instance state for this material graph component."""

        self._items: List[CompoundItem] = []
        self._groups: List[str] = []
        self._metadata: Dict[str, Dict[str, str]] = {}
        self._reload_callback: Optional[Callable[[], None]] = None
        self._lifecycle = LifecycleRegistry()
        self._settings = carb.settings.get_settings()
        self._settings_sub = self._settings.subscribe_to_tree_change_events(
            Settings.COMPOUND_PATHS, self._on_settings_changed
        )
        self._lifecycle.add_unsubscribe(self._settings_sub, "unsubscribe_to_tree_change_events")
        self._file_event_sub = get_eventdispatcher().observe_event(
            event_name=FILE_SAVED_GLOBAL_EVENT, on_event=self._on_file_saved
        )
        self._lifecycle.add_unsubscribe(self._file_event_sub)
        self.refresh()

    def destroy(self) -> None:
        """Execute destroy behavior for material graph workflows."""

        if self._lifecycle:
            self._lifecycle.cleanup()
            self._lifecycle = None
        self._settings = None
        self._settings_sub = None
        self._file_event_sub = None
        self._items = []
        self._groups = []
        self._metadata = {}
        self._reload_callback = None

    def set_reload_callback(self, callback: Optional[Callable[[], None]]) -> None:
        """Execute set reload callback behavior for material graph workflows."""

        self._reload_callback = callback

    def refresh(self, paths: Optional[Iterable[str]] = None) -> None:
        """Execute refresh behavior for material graph workflows."""

        search_paths = list(paths) if paths is not None else Settings.get_compound_paths()
        logger.info("compound registry refresh start paths=%s", len(search_paths))
        groups, metadata = _load_group_metadata()
        items: List[CompoundItem] = []
        for path in search_paths:
            for compound_path in _iter_compound_files(path):
                items.extend(_load_compounds(compound_path, metadata))
        self._items = items
        self._metadata = metadata
        self._groups = _merge_group_names(groups, items)
        logger.info("compound registry refresh end items=%s groups=%s", len(self._items), len(self._groups))
        if self._reload_callback:
            self._reload_callback()

    def get_items(self) -> List[CompoundItem]:
        """Execute get items behavior for material graph workflows."""

        return list(self._items)

    def get_groups(self) -> List[str]:
        """Execute get groups behavior for material graph workflows."""

        return list(self._groups)

    def get_group_items(self) -> List[GroupItem]:
        """Execute get group items behavior for material graph workflows."""

        groups: List[GroupItem] = []
        for name in self._groups:
            group = GroupItem(name)
            setattr(group, "is_compound_group", True)
            for item in self._items:
                if item.group == name:
                    group.add_child(item)
            groups.append(group)
        return groups

    def get_item_by_identifier(self, source_asset: str, identifier: str) -> Optional[CompoundItem]:
        """Execute get item by identifier behavior for material graph workflows."""

        key = _compound_key(source_asset, identifier)
        for item in self._items:
            if _compound_key(item.source_asset, item.identifier) == key:
                return item
        return None

    def create_group(self, name: str) -> None:
        """Execute create group behavior for material graph workflows."""

        name = (name or "").strip()
        if not name or name in self._groups:
            return
        self._groups.append(name)
        self._save_metadata_and_refresh()

    def rename_group(self, old_name: str, new_name: str) -> None:
        """Execute rename group behavior for material graph workflows."""

        old_name = (old_name or "").strip()
        new_name = (new_name or "").strip()
        if not old_name or not new_name or old_name == new_name:
            return
        if old_name not in self._groups or new_name in self._groups:
            return
        self._groups = [new_name if name == old_name else name for name in self._groups]
        for entry in self._metadata.values():
            if entry.get("group") == old_name:
                entry["group"] = new_name
        self._save_metadata_and_refresh()

    def remove_group(self, name: str) -> None:
        """Execute remove group behavior for material graph workflows."""

        name = (name or "").strip()
        if not name or name not in self._groups:
            return
        self._groups = [group for group in self._groups if group != name]
        for entry in self._metadata.values():
            if entry.get("group") == name:
                entry["group"] = ""
        self._save_metadata_and_refresh()

    def assign_group(self, item: CompoundItem, group_name: str) -> bool:
        """Execute assign group behavior for material graph workflows."""

        if not item:
            return False
        group_name = (group_name or "").strip()
        key = _compound_key(item.source_asset, item.identifier)
        entry = self._metadata.setdefault(key, {})
        entry["group"] = group_name
        if group_name and group_name not in self._groups:
            self._groups.append(group_name)
        return self._save_metadata_and_refresh()

    def rename_compound(self, item: CompoundItem, new_name: str) -> None:
        """Execute rename compound behavior for material graph workflows."""

        if not item:
            return
        new_name = (new_name or "").strip()
        if not new_name:
            return
        key = _compound_key(item.source_asset, item.identifier)
        entry = self._metadata.setdefault(key, {})
        entry["name"] = new_name
        self._save_metadata_and_refresh()

    def remove_compound(self, item: CompoundItem) -> bool:
        """Execute remove compound behavior for material graph workflows."""

        if not item:
            return False
        source_asset = item.source_asset
        removed = False
        try:
            path_obj = Path(source_asset)
            if path_obj.exists():
                path_obj.unlink()
                removed = True
        except OSError as exc:
            logger.debug("local compound delete failed for '%s': %s", source_asset, exc)
            removed = False
        if not removed and isinstance(source_asset, str) and source_asset:
            result = omni.client.delete(source_asset)
            removed = result == omni.client.Result.OK
        if not removed:
            logger.warning("compound delete failed; preserving metadata for '%s'", source_asset)
            return False
        key = _compound_key(item.source_asset, item.identifier)
        self._metadata.pop(key, None)
        return self._save_metadata_and_refresh()

    def _save_metadata_and_refresh(self) -> bool:
        """Persist compound metadata and refresh from disk."""
        saved = _save_group_metadata(self._groups, self._metadata)
        self.refresh()
        return saved

    def _on_settings_changed(self, _tree_item: Any, _changed_item: Any, _event_type: Any) -> None:
        """Execute on settings changed behavior for material graph workflows."""

        self.refresh()

    def _on_file_saved(self, event: dict) -> None:
        """Execute on file saved behavior for material graph workflows."""

        try:
            url = event["url"]
        except (KeyError, RuntimeError, ValueError, TypeError, AttributeError) as exc:
            logger.debug("compound file-save event missing url: %s", exc)
            return
        if not url or not _is_compound_file(url):
            return
        if _is_in_compound_paths(url, Settings.get_compound_paths()):
            self.refresh()


_COMPOUND_REGISTRY: Optional[CompoundRegistry] = None


def get_compound_registry() -> CompoundRegistry:
    """Execute get compound registry behavior for material graph workflows."""

    global _COMPOUND_REGISTRY
    if _COMPOUND_REGISTRY is None:
        _COMPOUND_REGISTRY = CompoundRegistry()
    return _COMPOUND_REGISTRY


def destroy_compound_registry() -> None:
    """Destroy and reset the process-global compound registry."""
    global _COMPOUND_REGISTRY
    registry = _COMPOUND_REGISTRY
    _COMPOUND_REGISTRY = None
    if registry is not None:
        registry.destroy()
