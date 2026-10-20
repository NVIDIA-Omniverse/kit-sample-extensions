"""Graph interaction controller for click/double-click and context-menu behaviors."""

from functools import partial
from typing import Any, Callable, Iterable, Optional

import omni.ui
from omni.kit.widget.graph import IsolationGraphModel
from pxr import Sdf, UsdShade, UsdUI

from ....api.context_menu import get_background_menu_items
from ....config.logging import log_exception, logger
from ....models.catalog.items.compound import CompoundItem
from ....models.catalog.items.shader import ShaderItem
from ....models.catalog.items.texture import TextureItem
from ...interaction.menu_utils import show_menu_at_cursor

# pylint: disable=no-member,broad-exception-caught


class InteractionController:
    """Handles graph interaction events and context menus."""

    def __init__(self, widget: object, node_creation_controller: object, catalog_model: object) -> None:
        """Initialize the interaction controller."""
        self._widget = widget
        self._node_creation = node_creation_controller
        self._right_click_menu = None
        self._catalog_model = catalog_model

    def on_left_mouse_button_double_clicked(self, items: object) -> None:
        """Handle double-click events on the graph."""
        try:
            if not items:
                return

            item_models, has_port_item, has_io_node = self._collect_double_click_item_state(items)
            if has_port_item or has_io_node or self._contains_property_path(items):
                return
            if self._is_backdrop_double_click(item_models) or len(item_models) != 1:
                return

            item, item_model = item_models[0]
            if self._is_nodegraph_model(item_model):
                if self._widget.is_mouse_over_node_header(item):
                    return
                self._widget.set_current_compound(item)
                return
            return
        except Exception as exc:  # pylint: disable=broad-exception-caught
            log_exception(
                logger,
                "interaction double-click failed",
                context_name=getattr(self._widget, "current_context", None),
                action="double_click",
                exc=exc,
            )

    def _collect_double_click_item_state(self, items: object) -> tuple[list[tuple[object, object]], bool, bool]:
        """Collect item models and IO/port markers for double-click handling."""
        model = self._widget.model if self._widget else None
        item_models = []
        has_port_item = False
        has_io_node = False
        for item in items:
            item_model = model.get_item_model(item) if model else None
            if item_model is None:
                has_io_node = has_io_node or self._is_input_output_item(item)
                continue
            item_models.append((item, item_model))
            has_port_item = has_port_item or self._is_port_item(item_model)
            has_io_node = has_io_node or self._is_input_output_node(item_model) or self._is_input_output_item(item)
        return item_models, has_port_item, has_io_node

    @staticmethod
    def _is_backdrop_double_click(item_models: list[tuple[object, object]]) -> bool:
        """Return True when first clicked model is a backdrop."""
        if not item_models:
            return False
        return getattr(item_models[0][1], "type", None) == UsdUI.Backdrop

    @staticmethod
    def _is_port_item(item_model: object) -> bool:
        """Return True if the model item represents a port."""
        if not item_model:
            return False
        item_fields = dir(item_model)
        if "usdshade_port" in item_fields or "placeholder" in item_fields or "port" in item_fields:
            return True
        # Isolation/proxy port items may not expose the usual attributes directly.
        path = item_model.path if "path" in item_fields else None
        if isinstance(path, Sdf.Path) and path.IsPrimPropertyPath():
            return True
        return False

    @staticmethod
    def _is_nodegraph_model(item_model: object) -> bool:
        """Return True if the model represents a nodegraph."""
        if not item_model:
            return False
        return getattr(item_model, "type", None) == UsdShade.NodeGraph

    @staticmethod
    def _is_input_output_node(item_model: object) -> bool:
        """Return True if the model item is an isolation input/output node."""
        if not item_model:
            return False
        # Do not treat real nodegraphs/materials as IO nodes just because
        # model types expose remove_input/remove_output helpers.
        item_type = getattr(item_model, "type", None)
        if item_type in (UsdShade.NodeGraph, UsdShade.Material):
            return False
        try:
            return isinstance(item_model, (IsolationGraphModel.InputNode, IsolationGraphModel.OutputNode))
        except TypeError as exc:
            logger.debug("is_input_output_node isinstance check failed: %s", exc)
        is_input_node_fn = item_model.is_input_node if "is_input_node" in dir(item_model) else None
        if callable(is_input_node_fn):
            try:
                if bool(is_input_node_fn()):
                    return True
            except (
                RuntimeError,
                ValueError,
                TypeError,
                AttributeError,
            ) as exc:  # pylint: disable=broad-exception-caught
                logger.debug("is_input_output_node is_input_node check failed: %s", exc)
        is_output_node_fn = item_model.is_output_node if "is_output_node" in dir(item_model) else None
        if callable(is_output_node_fn):
            try:
                if bool(is_output_node_fn()):
                    return True
            except (
                RuntimeError,
                ValueError,
                TypeError,
                AttributeError,
            ) as exc:  # pylint: disable=broad-exception-caught
                logger.debug("is_input_output_node is_output_node check failed: %s", exc)
        model_type = type(item_model)
        get_type_name = model_type.get_type_name if "get_type_name" in dir(model_type) else None
        if callable(get_type_name):
            try:
                return get_type_name() in ("InputNode", "OutputNode")
            except (
                RuntimeError,
                ValueError,
                TypeError,
                AttributeError,
            ) as exc:  # pylint: disable=broad-exception-caught
                logger.debug("is_input_output_node get_type_name check failed: %s", exc)
                return False
        return False

    @staticmethod
    def _is_input_output_item(item: object) -> bool:
        """Return True if the raw clicked item is an isolation IO node wrapper."""
        if item is None:
            return False
        item_type = type(item)
        get_type_name = item_type.get_type_name if "get_type_name" in dir(item_type) else None
        if callable(get_type_name):
            try:
                return get_type_name() in ("InputNode", "OutputNode")
            except (
                RuntimeError,
                ValueError,
                TypeError,
                AttributeError,
            ) as exc:  # pylint: disable=broad-exception-caught
                logger.debug("is_input_output_item get_type_name check failed: %s", exc)
                return False
        return False

    @staticmethod
    def _contains_property_path(items: object) -> bool:
        """Return True if any item is a prim property path."""
        for item in items or []:
            if isinstance(item, Sdf.Path) and item.IsPrimPropertyPath():
                return True
        return False

    def on_right_mouse_button_pressed(
        self, items: object, x: Optional[float] = None, y: Optional[float] = None
    ) -> None:
        """Handle right-click events and show context menus."""
        try:
            if self._right_click_menu:
                self._right_click_menu.hide()
            self._right_click_menu = omni.ui.Menu("Context menu")
            mouse_position = self._node_creation.get_hovered_position()
            with self._right_click_menu:
                node_groups, nodegraph_entries, texture_entries = self._partition_catalog_children(
                    self._catalog_model.children
                )

                sections = []
                if node_groups:
                    sections.append(("Nodes", node_groups, self._build_group_menus))
                if nodegraph_entries:
                    sections.append(("NodeGraphs", nodegraph_entries, self._build_nodegraph_menus))
                if texture_entries:
                    sections.append(("Textures", texture_entries, self._build_texture_menus))
                for label, entries, builder in sorted(sections, key=lambda s: self._sort_text(s[0])):
                    section_menu = omni.ui.Menu(label)
                    with section_menu:
                        builder(entries, mouse_position)

                background_items = get_background_menu_items()
                if background_items:
                    omni.ui.Separator()
                    for menu_item in sorted(background_items, key=lambda i: self._sort_text(getattr(i, "label", ""))):
                        omni.ui.MenuItem(
                            menu_item.label,
                            triggered_fn=partial(
                                self._safe_menu_callback,
                                menu_item.callback,
                                items,
                                mouse_position,
                                menu_label=menu_item.label,
                            ),
                        )

            show_menu_at_cursor(self._right_click_menu)
        except Exception as exc:  # pylint: disable=broad-exception-caught
            log_exception(
                logger,
                "interaction right-click failed",
                context_name=getattr(self._widget, "current_context", None),
                action="right_click",
                exc=exc,
            )

    def hide_context_menu(self) -> None:
        """Hide the graph background context menu if visible."""
        if not self._right_click_menu:
            return
        try:
            self._right_click_menu.hide()
        except (RuntimeError, ValueError, TypeError, AttributeError) as exc:  # pylint: disable=broad-exception-caught
            logger.warning(
                "graph context-menu hide failed context='%s': %s; forcing the visibility flag off",
                getattr(self._widget, "current_context", None) or "<none>",
                exc,
            )
        try:
            self._right_click_menu.visible = False
        except (RuntimeError, ValueError, TypeError, AttributeError) as exc:  # pylint: disable=broad-exception-caught
            logger.warning(
                "graph context-menu visibility reset failed context='%s': %s; the stale menu may remain visible",
                getattr(self._widget, "current_context", None) or "<none>",
                exc,
            )

    @staticmethod
    def _is_texture_entry(item: object) -> bool:
        """Return True for texture items and texture-group entries."""
        return isinstance(item, TextureItem) or ("is_texture_group" in dir(item) and bool(item.is_texture_group))

    @staticmethod
    def _is_nodegraph_entry(item: object) -> bool:
        """Return True for compound items and compound-group entries."""
        return isinstance(item, CompoundItem) or ("is_compound_group" in dir(item) and bool(item.is_compound_group))

    @staticmethod
    def _sort_text(value: Any) -> str:
        """Return normalized lowercase text used for alphabetical ordering."""
        return str(value or "").strip().casefold()

    @classmethod
    def _item_sort_key(cls, item: object) -> str:
        """Return stable alphabetical key for item-like objects."""
        return cls._sort_text(getattr(item, "name", getattr(item, "label", "")))

    @classmethod
    def _sorted_items(cls, items: Iterable[object]) -> list[object]:
        """Return alphabetically sorted item list."""
        return sorted(list(items or []), key=cls._item_sort_key)

    def _partition_catalog_children(self, items: Iterable[object]) -> tuple[list[object], list[object], list[object]]:
        """Split visible catalog children into node, nodegraph, and texture buckets."""
        node_groups = []
        nodegraph_entries = []
        texture_entries = []
        for item in items:
            if self._is_texture_entry(item):
                texture_entries.append(item)
            elif self._is_nodegraph_entry(item):
                nodegraph_entries.append(item)
            else:
                node_groups.append(item)
        return node_groups, nodegraph_entries, texture_entries

    def _build_group_menus(self, groups: Iterable[object], mouse_position: Optional[tuple[float, float]]) -> None:
        """Build nested node creation menu entries for standard node groups."""
        for group in self._sorted_items(groups):
            children = group.children if "children" in dir(group) else None
            if not children:
                omni.ui.MenuItem(
                    group.name,
                    triggered_fn=partial(self._node_creation.create_from_catalog, group, mouse_position),
                )
                continue
            group_menu = omni.ui.Menu(group.name)
            with group_menu:
                self._build_group_menu_children(children, mouse_position)

    def _build_group_menu_children(
        self, children: Iterable[object], mouse_position: Optional[tuple[float, float]]
    ) -> None:
        """Build children entries for a node-group submenu.

        Single-item submenus are flattened recursively: if a submenu at any
        depth contains only one item, that item is promoted into the parent.
        """
        tagged = []
        for child in children or []:
            parts = self._submenu_parts_for_child(child)
            tagged.append((child, parts))
        self._build_tagged_menu_entries(tagged, mouse_position)

    def _build_tagged_menu_entries(
        self,
        tagged: list[tuple[object, list[str]]],
        mouse_position: Optional[tuple[float, float]],
    ) -> None:
        """Recursively build menu entries, flattening single-item submenus."""
        buckets: dict[str, list[tuple[object, list[str]]]] = {}
        flat_items: list[object] = []
        for child, parts in tagged:
            if not parts:
                flat_items.append(child)
            else:
                buckets.setdefault(parts[0], []).append((child, parts[1:]))

        entries: list[tuple[str, object]] = []
        for item in flat_items:
            name = item.name if "name" in dir(item) else ""
            entries.append((self._sort_text(name), ("item", item)))
        for key, bucket in buckets.items():
            if len(bucket) == 1:
                child, _ = bucket[0]
                name = child.name if "name" in dir(child) else ""
                entries.append((self._sort_text(name), ("item", child)))
            else:
                entries.append((self._sort_text(key), ("submenu", key, bucket)))

        entries.sort(key=lambda e: e[0])

        for _, entry in entries:
            if entry[0] == "item":
                self._create_catalog_menu_item(entry[1], mouse_position)
            else:
                _, key, bucket = entry
                with omni.ui.Menu(key):
                    self._build_tagged_menu_entries(bucket, mouse_position)

    def _create_catalog_menu_item(self, child: object, mouse_position: Optional[tuple[float, float]]) -> None:
        """Create one menu item for a catalog child."""
        omni.ui.MenuItem(
            child.name,
            triggered_fn=partial(self._node_creation.create_from_catalog, child, mouse_position),
        )

    def _submenu_parts_for_child(self, child: object) -> list[str]:
        """Return normalized submenu parts for a child item."""
        submenu_parts = self._get_family_submenu_parts(child)
        if not isinstance(child, ShaderItem):
            return submenu_parts
        return self._trim_redundant_polymorphic_tail(child, submenu_parts)

    @staticmethod
    def _get_family_submenu_parts(child: object) -> list[str]:
        """Return family-derived submenu parts with legacy fallback."""
        family = child.family if "family" in dir(child) else ""
        family_parts = [part.strip() for part in str(family).split(":") if part and part.strip()]
        submenu_parts = family_parts[1:] if len(family_parts) > 1 else []
        if submenu_parts or not isinstance(child, ShaderItem):
            return submenu_parts
        legacy_submenu = ((child.sub_menu if "sub_menu" in dir(child) else "") or "").strip()
        return [legacy_submenu] if legacy_submenu else []

    @staticmethod
    def _trim_redundant_polymorphic_tail(child: ShaderItem, submenu_parts: list[str]) -> list[str]:
        """Trim duplicated node-name tail from polymorphic submenu paths."""
        if not submenu_parts:
            return submenu_parts
        extra = (child.extra_mime_data if "extra_mime_data" in dir(child) else {}) or {}
        if not (bool(extra.get("is_polymorphic")) or bool(extra.get("requires_variant_selection"))):
            return submenu_parts
        child_name = ((child.name if "name" in dir(child) else "") or "").strip().casefold()
        tail = (submenu_parts[-1] or "").strip().casefold()
        if child_name and tail == child_name:
            return submenu_parts[:-1]
        return submenu_parts

    def _build_texture_menus(self, entries: Iterable[object], mouse_position: Optional[tuple[float, float]]) -> None:
        """Build context-menu entries for texture groups and items."""
        for entry in self._sorted_items(entries):
            if isinstance(entry, TextureItem):
                omni.ui.MenuItem(
                    entry.name,
                    triggered_fn=partial(self._node_creation.create_from_catalog, entry, mouse_position),
                )
                continue
            children = entry.children if "children" in dir(entry) else None
            group_menu = omni.ui.Menu(entry.name)
            with group_menu:
                for child in self._sorted_items(children or []):
                    omni.ui.MenuItem(
                        child.name,
                        triggered_fn=partial(self._node_creation.create_from_catalog, child, mouse_position),
                    )

    def _build_nodegraph_menus(self, entries: Iterable[object], mouse_position: Optional[tuple[float, float]]) -> None:
        """Build context-menu entries for compound groups and nodegraphs."""
        for entry in self._sorted_items(entries):
            if isinstance(entry, CompoundItem):
                omni.ui.MenuItem(
                    entry.name,
                    triggered_fn=partial(self._node_creation.create_from_catalog, entry, mouse_position),
                )
                continue
            children = entry.children if "children" in dir(entry) else None
            group_menu = omni.ui.Menu(entry.name)
            with group_menu:
                for child in self._sorted_items(children or []):
                    omni.ui.MenuItem(
                        child.name,
                        triggered_fn=partial(self._node_creation.create_from_catalog, child, mouse_position),
                    )

    @staticmethod
    def _safe_menu_callback(callback: Callable[..., object], *args: object, **kwargs: object) -> None:
        """Invoke a callback safely with error reporting."""
        menu_label = kwargs.pop("menu_label", None)
        try:
            if not callable(callback):
                logger.warning("context menu callback is not callable label=%s", menu_label)
                return
            if len(args) >= 2 and not kwargs:
                callback(items=args[0], mouse_position=args[1])
            else:
                callback(*args, **kwargs)
        except Exception as exc:  # pylint: disable=broad-exception-caught
            log_exception(
                logger,
                "context menu callback failed",
                action=str(menu_label or "context_menu_callback"),
                exc=exc,
            )

    def destroy(self) -> None:
        """Release subscriptions, callbacks, and cached references owned by this controller."""
        self._right_click_menu = None
        self._catalog_model = None
        self._node_creation = None
        self._widget = None
