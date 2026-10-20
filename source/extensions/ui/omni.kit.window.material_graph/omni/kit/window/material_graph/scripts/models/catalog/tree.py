"""Catalog tree model that aggregates shader, texture, and compound item groups."""

import asyncio
from enum import Enum
from typing import Any, List, Optional, Sequence, Tuple

import omni.ui
from omni.kit.widget.graph import IsolationGraphModel
from pxr import UsdShade, UsdUI

from ...config.logging import logger
from ...utils.lifecycle_registry import LifecycleRegistry
from .items import CompoundItem, DroppableItem, GroupItem, MiscellaneousItem, TextureItem
from .registries.compound import get_compound_registry
from .registries.texture import get_texture_registry


class CatalogTreeModel(omni.ui.AbstractItemModel):
    """Tree model that exposes catalog items to the UI."""

    class Column(Enum):
        """Represent column behavior for the material graph extension."""

        NAME = 0
        INFO = 1
        ICON = 2
        TOOLTIP = 3

    def __init__(self) -> None:
        """Initialize instance state for this material graph component."""

        super().__init__()
        self._children = []
        self._discovery_plugin = None
        self._filter_name_text = ""
        self._filter_group: Optional[str] = None
        self._current_context: Optional[str] = None
        self._lifecycle = LifecycleRegistry()
        self._reload_task = None
        self._debounce_seconds = 0.2
        self._catalog_signature = None
        self._last_discovery_failure = None
        self._last_reload_failure = None
        self._has_reload_callback = True
        self._reload_generation = 0
        self._compound_registry = get_compound_registry()
        self._compound_registry.set_reload_callback(self._on_compounds_reload)
        self._texture_registry = get_texture_registry()
        self._texture_registry.set_reload_callback(self._on_textures_reload)

    def destroy(self) -> None:
        """Execute destroy behavior for material graph workflows."""

        if self._discovery_plugin:
            self._discovery_plugin.set_reload_callback(None)
            self._discovery_plugin = None
        if self._compound_registry:
            self._compound_registry.set_reload_callback(None)
            self._compound_registry = None
        if self._texture_registry:
            self._texture_registry.set_reload_callback(None)
            self._texture_registry = None
        self._children = []
        self._catalog_signature = None
        self._last_discovery_failure = None
        self._last_reload_failure = None
        self._lifecycle.cleanup()
        self._reload_task = None

    @property
    def children(self) -> List[Any]:
        """Execute children behavior for material graph workflows."""

        return self._children

    def set_discovery_plugin(self, discovery_plugin: Optional[Any]) -> None:
        """Execute set discovery plugin behavior for material graph workflows."""

        if discovery_plugin is None:
            self.clear()
            return
        if (not self._discovery_plugin) or (discovery_plugin.name != self._discovery_plugin.name):
            self._discovery_plugin = discovery_plugin
            self._last_discovery_failure = None
            self._last_reload_failure = None
            try:
                self._discovery_plugin.set_reload_callback(self._on_reload_callback)
                self._has_reload_callback = True
            except AttributeError:
                logger.warning(
                    "discovery plugin: '%s' does not support reload callbacks",
                    discovery_plugin.name,
                )
                self._has_reload_callback = False
            self.clear()
        if not self._children:
            self._schedule_reload(immediate=True)
        self.filter_by_text(self._filter_name_text)

    def set_current_context(self, context_name: Optional[str]) -> None:
        """Execute set current context behavior for material graph workflows."""

        if self._current_context == context_name:
            return
        self._current_context = context_name
        self.filter_by_text(self._filter_name_text)

    @property
    def current_context(self) -> Optional[str]:
        """Return the active catalog visibility context."""
        return self._current_context

    def reload(self) -> None:
        """Execute reload behavior for material graph workflows."""

        self.clear()
        if self._discovery_plugin:
            self._schedule_reload()

    def refresh_compounds(self) -> None:
        """Execute refresh compounds behavior for material graph workflows."""

        if self._compound_registry:
            self._compound_registry.refresh()

    def _schedule_reload(self, immediate: bool = False) -> None:
        """Execute schedule reload behavior for material graph workflows."""

        if self._reload_task:
            self._reload_task.cancel()
            self._reload_task = None
        self._reload_generation += 1
        generation = self._reload_generation

        async def _reload_async() -> None:
            """Asynchronously execute reload async behavior for material graph workflows."""

            if not immediate:
                await asyncio.sleep(self._debounce_seconds)
            if generation != self._reload_generation:
                return
            try:
                if self._discovery_plugin:
                    self._discovery_plugin.reload()
                if not self._has_reload_callback:
                    self._on_plugin_reload()
            except (
                RuntimeError,
                ValueError,
                TypeError,
                AttributeError,
            ) as exc:  # pylint: disable=broad-exception-caught
                plugin_name = getattr(self._discovery_plugin, "name", type(self._discovery_plugin).__name__)
                failure = (plugin_name, self._current_context, type(exc).__name__, str(exc))
                if failure != self._last_reload_failure:
                    logger.warning(
                        "catalog reload failed for plugin '%s' context=%s: %s; catalog contents were cleared",
                        plugin_name,
                        self._current_context or "<none>",
                        exc,
                    )
                self._last_reload_failure = failure

        self._reload_task = self._lifecycle.add_task(_reload_async())

    def _on_reload_callback(self) -> None:
        """Execute on reload callback behavior for material graph workflows."""

        self._on_plugin_reload()

    def _on_compounds_reload(self) -> None:
        """Execute on compounds reload behavior for material graph workflows."""

        if self._discovery_plugin:
            self._on_plugin_reload()

    def _on_textures_reload(self) -> None:
        """Execute on textures reload behavior for material graph workflows."""

        if self._discovery_plugin:
            self._on_plugin_reload()
            self._item_changed(None)

    def _on_plugin_reload(self) -> None:
        """Execute on plugin reload behavior for material graph workflows."""

        if not self._discovery_plugin:
            return
        try:
            plugin_catalog_items = self._discovery_plugin.get_catalog_items()
        except (RuntimeError, ValueError, TypeError, AttributeError) as exc:  # pylint: disable=broad-exception-caught
            plugin_name = getattr(self._discovery_plugin, "name", type(self._discovery_plugin).__name__)
            failure = (plugin_name, self._current_context, type(exc).__name__, str(exc))
            if failure != self._last_discovery_failure:
                logger.warning(
                    "catalog discovery failed for plugin '%s' context=%s: %s; catalog contents were cleared",
                    plugin_name,
                    self._current_context or "<none>",
                    exc,
                )
            self._last_discovery_failure = failure
            self._children = []
            self._catalog_signature = None
            self._item_changed(None)
            return
        self._last_discovery_failure = None
        if not plugin_catalog_items:
            logger.info("catalog discovery returned no items")
            self._children = []
        else:
            self._children = plugin_catalog_items.copy()
        compound_groups = self._build_compound_groups()
        if compound_groups:
            self._children.extend(compound_groups)
        texture_groups = self._build_texture_groups()
        if texture_groups:
            self._children.extend(texture_groups)

        miscellaneous_group_item = GroupItem("Miscellaneous")
        miscellaneous_group_item.add_child(MiscellaneousItem(UsdUI.Tokens.Backdrop, "A UsdUI.Backdrop prim"))
        miscellaneous_group_item.add_child(MiscellaneousItem(UsdShade.Tokens.NodeGraph, "A UsdShade.NodeGraph prim"))
        miscellaneous_group_item.add_child(
            MiscellaneousItem(
                IsolationGraphModel.InputNode.get_type_name(),
                "Provides access to the inputs of the current container.",
            )
        )
        miscellaneous_group_item.add_child(
            MiscellaneousItem(
                IsolationGraphModel.OutputNode.get_type_name(),
                "Provides access to the outputs of the current container.",
            )
        )
        if self._children:
            self._children.append(miscellaneous_group_item)

        signature = self._compute_signature(self._children)
        if signature != self._catalog_signature:
            self._catalog_signature = signature
            self._item_changed(None)

    def clear(self) -> None:
        """Execute clear behavior for material graph workflows."""

        if not self._children:
            return
        self._children = []
        self._catalog_signature = None
        self._item_changed(None)

    def get_item_children(self, item: Optional[Any]) -> List[Any]:
        """Execute get item children behavior for material graph workflows."""
        if item is None:
            return self._get_root_filtered_children()
        if isinstance(item, GroupItem):
            return self._get_group_filtered_children(item)
        return []

    def _get_root_filtered_children(self) -> List[Any]:
        """Return top-level children filtered by active catalog group filter."""
        if self._filter_group == "textures":
            return [c for c in self._children if c.filtered and (c.is_texture_group or isinstance(c, TextureItem))]
        if self._filter_group == "nodegraphs":
            return [c for c in self._children if c.filtered and (c.is_compound_group or isinstance(c, CompoundItem))]
        if self._filter_group == "nodes":
            return [
                c
                for c in self._children
                if c.filtered
                and not (c.is_texture_group or c.is_compound_group or isinstance(c, (TextureItem, CompoundItem)))
            ]
        return [c for c in self._children if c.filtered]

    def _get_group_filtered_children(self, item: GroupItem) -> List[Any]:
        """Return filtered children for a specific group item."""
        if self._filter_group == "textures" and not item.is_texture_group:
            return []
        if self._filter_group == "nodegraphs" and not item.is_compound_group:
            return []
        return [c for c in item.children if c.filtered]

    def get_item_value_model_count(self, item: Any) -> int:
        """Execute get item value model count behavior for material graph workflows."""
        return 1

    def get_item_value_model(self, item: Any, column_id: int) -> Optional[Any]:
        """Execute get item value model behavior for material graph workflows."""

        if item is None:
            return None
        if column_id == self.Column.NAME.value:
            return item.name_model
        if column_id == self.Column.INFO.value:
            return item.info_model
        if column_id == self.Column.ICON.value:
            return item.icon_model
        if column_id == self.Column.TOOLTIP.value:
            return item.tooltip_model
        return None

    def get_drag_mime_data(self, item: Any) -> str:
        """Execute get drag mime data behavior for material graph workflows."""

        if isinstance(item, DroppableItem):
            item_data = item.get_drag_mime_data()
            if item_data:
                return item_data
        return ""

    def drop_accepted(self, target_item: Any, source: Any, drop_location: int = -1) -> bool:
        """Accept internal TreeView drags of textures/compounds onto groups or root."""
        if isinstance(source, TextureItem):
            if target_item is None:
                return True
            return isinstance(target_item, GroupItem) and target_item.is_texture_group
        if isinstance(source, CompoundItem):
            if target_item is None:
                return True
            return isinstance(target_item, GroupItem) and target_item.is_compound_group
        return False

    def drop(self, target_item: Any, source: Any, drop_location: int = -1) -> None:
        """Handle internal TreeView drops to move items between groups."""
        if isinstance(source, TextureItem):
            source_group = source.group if source.group is not None else ""
            group_name = target_item.name if isinstance(target_item, GroupItem) and target_item.is_texture_group else ""
            if source_group != group_name and self._texture_registry:
                try:
                    result = self._texture_registry.assign_group(source, group_name)
                except Exception as exc:  # pylint: disable=broad-exception-caught
                    logger.warning("failed to assign texture '%s' to group '%s': %s", source.name, group_name, exc)
                    return
                if not result:
                    logger.warning("failed to assign texture '%s' to group '%s'", source.name, group_name)
            return
        if isinstance(source, CompoundItem):
            source_group = source.group if source.group is not None else ""
            group_name = (
                target_item.name if isinstance(target_item, GroupItem) and target_item.is_compound_group else ""
            )
            if source_group != group_name and self._compound_registry:
                try:
                    result = self._compound_registry.assign_group(source, group_name)
                except Exception as exc:  # pylint: disable=broad-exception-caught
                    logger.warning("failed to assign compound '%s' to group '%s': %s", source.name, group_name, exc)
                    return
                if not result:
                    logger.warning("failed to assign compound '%s' to group '%s'", source.name, group_name)
            return

    def filter_by_text(self, filter_name_text: str) -> None:
        """Execute filter by text behavior for material graph workflows."""

        self._filter_name_text = filter_name_text
        changed = False
        for child in self._children:
            previous = self._filter_signature(child)
            child.prefilter(self._filter_name_text.lower(), self._current_context)
            if previous != self._filter_signature(child):
                changed = True
        if changed:
            self._item_changed(None)

    def _filter_signature(self, item: Any) -> Tuple[Any, ...]:
        """Return recursive visibility state so changes inside visible groups are observable."""
        children = item.children if isinstance(item, GroupItem) else []
        return (item.filtered, tuple(self._filter_signature(child) for child in children))

    def set_filter_group(self, name: Optional[str]) -> None:
        """Execute set filter group behavior for material graph workflows."""

        if name == self._filter_group:
            return
        self._filter_group = name
        self._item_changed(None)

    def _build_compound_groups(self) -> List[Any]:
        """Execute build compound groups behavior for material graph workflows."""

        if not self._compound_registry:
            return []
        groups = self._compound_registry.get_group_items()
        ungrouped = [item for item in self._compound_registry.get_items() if not item.group]
        return groups + ungrouped

    def _build_texture_groups(self) -> List[GroupItem]:
        """Execute build texture groups behavior for material graph workflows."""

        if not self._texture_registry:
            return []
        groups = self._texture_registry.get_group_items()
        ungrouped = [item for item in self._texture_registry.get_items() if not item.group]
        return groups + ungrouped

    def _compute_signature(self, items: Sequence[Any]) -> Tuple[Any, ...]:
        """Execute compute signature behavior for material graph workflows."""

        memo = {}
        return tuple(self._item_signature(item, memo) for item in items)

    def _item_signature(self, item: Any, memo: dict) -> Any:
        """Execute item signature behavior for material graph workflows."""

        cached = memo.get(id(item))
        if cached is not None:
            return cached
        icon = item.icon_model.get_value_as_string() if item.icon_model else item.data.icon
        entry = (
            type(item).__name__,
            item.name,
            item.info,
            item.tooltip,
            icon,
            item.identifier,
            item.context,
            item.family,
            item.group,
        )
        if isinstance(item, GroupItem):
            signature = (entry, tuple(self._item_signature(child, memo) for child in item.children))
        else:
            signature = entry
        memo[id(item)] = signature
        return signature
