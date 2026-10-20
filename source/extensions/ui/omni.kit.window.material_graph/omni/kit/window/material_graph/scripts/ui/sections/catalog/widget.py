"""Catalog widget section for browsing and filtering node creation entries."""

import json
from typing import Callable, List, Optional

import carb.input
import omni.kit.app
import omni.ui as ui
from omni.kit.graph.editor.core.graph_editor_core_catalog import GraphEditorCoreCatalog
from omni.kit.widget.searchfield import SearchField
from omni.kit.window.popup_dialog import InputDialog, MessageDialog

from ....config.logging import logger
from ....models.catalog.items.compound import CompoundItem
from ....models.catalog.items.group import GroupItem
from ....models.catalog.items.texture import TextureItem
from ....models.catalog.registries.compound import get_compound_registry
from ....models.catalog.registries.texture import get_texture_registry
from ....utils.lifecycle_registry import LifecycleRegistry
from ...controllers.overlay.catalog_drop_overlay import CatalogDropOverlayController
from ...interaction.menu_utils import show_menu_at_cursor
from .constants import (
    CATALOG_ACTIVE_TAB_COLOR,
    CATALOG_INACTIVE_TAB_BG,
    CATALOG_INACTIVE_TAB_COLOR,
    CATALOG_TAB_NODEGRAPHS,
    CATALOG_TAB_NODES,
    CATALOG_TAB_TEXTURES,
)

# pylint: disable=no-member,protected-access,attribute-defined-outside-init


class MaterialGraphCatalog(GraphEditorCoreCatalog):
    """Catalog widget with drop overlay feedback."""

    def __init__(
        self,
        model: ui.AbstractItemModel,
        delegate: ui.AbstractItemDelegate = None,
        on_context_menu_fn: Optional[Callable[[List[ui.AbstractItem]], None]] = None,
        accept_drop_fn: Optional[Callable[[str], bool]] = None,
        drop_fn: Optional[Callable[[ui.WidgetMouseDropEvent], None]] = None,
        **kwargs,
    ) -> None:
        """Initialize catalog UI, tab state, and drag/drop proxy hooks."""
        self._accept_drop_proxy_fn = accept_drop_fn
        self._drop_proxy_fn = drop_fn
        self._drop_overlay_controller = CatalogDropOverlayController()
        self._active_tab = CATALOG_TAB_NODES
        self._rename_dialog = None
        self._delete_dialog = None
        self._item_context_menu = None
        self._last_clicked_group = None
        self._tabs_frame = None
        self._lifecycle = LifecycleRegistry()
        super().__init__(
            model=model,
            delegate=delegate,
            on_context_menu_fn=on_context_menu_fn,
            accept_drop_fn=self._on_accept_drop_proxy,
            drop_fn=self._on_drop_proxy,
            **kwargs,
        )
        frame = self._GraphEditorCoreCatalog__frame
        if frame:
            frame.set_mouse_hovered_fn(self._on_hovered)

    @staticmethod
    def _extract_drop_data(*args, **kwargs) -> tuple[Optional[str], Optional[ui.WidgetMouseDropEvent]]:
        """Return drop payload and event from varying callback signatures."""
        if args:
            first = args[0]
            if hasattr(first, "mime_data"):
                return first.mime_data, first
            if isinstance(first, str):
                return first, None
        source = kwargs.get("source")
        if isinstance(source, str):
            return source, None
        return None, None

    def _on_accept_drop_proxy(self, *args, **kwargs) -> bool:
        """Filter incoming drops and update overlay visibility state."""
        drop_data, _event = self._extract_drop_data(*args, **kwargs)
        if not isinstance(drop_data, str):
            if self._drop_overlay_controller:
                self._drop_overlay_controller.hide()
            return False
        payload = self._parse_payload(drop_data)
        if payload and payload.get("origin") == "catalog":
            if self._drop_overlay_controller:
                self._drop_overlay_controller.hide()
            return False
        else:
            result = bool(self._accept_drop_proxy_fn(drop_data)) if self._accept_drop_proxy_fn else False
        if self._drop_overlay_controller:
            self._drop_overlay_controller.show(result)
        return result

    def _on_drop_proxy(self, *args, **kwargs) -> None:
        """Forward accepted drops to graph handlers and hide overlay."""
        if self._drop_overlay_controller:
            self._drop_overlay_controller.hide()
        drop_data, event = self._extract_drop_data(*args, **kwargs)
        if self._drop_proxy_fn:
            if event is not None:
                self._drop_proxy_fn(event)
                return
            if isinstance(drop_data, str):
                synthetic = type("DropEvent", (), {"mime_data": drop_data, "x": None, "y": None})()
                self._drop_proxy_fn(synthetic)

    def _on_tree_accept_drop(self, *args, **kwargs) -> bool:
        """Tree-level drop acceptance for external drops (files, MDL modules)."""
        return self._on_accept_drop_proxy(*args, **kwargs)

    def _on_tree_drop(self, *args, **kwargs) -> None:
        """Tree-level drop handling for external drops."""
        self._on_drop_proxy(*args, **kwargs)

    def _on_build(self) -> None:
        """Build tabs, search field, tree view, and drop overlay widgets."""
        with ui.ZStack():
            with ui.HStack():
                with ui.VStack():
                    self._tabs_frame = ui.Frame(height=24)
                    with self._tabs_frame:
                        self._build_tabs()
                    self._GraphEditorCoreCatalog__search_field = SearchField(
                        show_tokens=False,
                        style=self._GraphEditorCoreCatalog__search_field_style,
                    )
                    self._scroll_frame = ui.ScrollingFrame(
                        horizontal_scrollbar_policy=ui.ScrollBarPolicy.SCROLLBAR_ALWAYS_OFF,
                        vertical_scrollbar_policy=ui.ScrollBarPolicy.SCROLLBAR_AS_NEEDED,
                        style_type_name_override="TreeView.ScrollingFrame",
                        style={
                            "TreeView.ScrollingFrame": {"background_color": 0xFF2D2D2D},
                            "TreeView": {"background_color": 0xFF2D2D2D, "color": 0xFFC0C0C0},
                            "TreeView.Item": {"background_color": 0x00000000},
                            "TreeView.Item:hovered": {"background_color": 0xFF3E3E3E},
                            "TreeView.Item:selected": {"background_color": 0xFF494949},
                        },
                    )
                    with self._scroll_frame:
                        self._tree_view = ui.TreeView(
                            self._GraphEditorCoreCatalog__model,
                            delegate=self._GraphEditorCoreCatalog__delegate,
                            root_visible=False,
                            header_visible=False,
                            mouse_pressed_fn=self._on_mouse_pressed_proxy,
                        )
                        self._tree_view.set_key_pressed_fn(self._on_key_pressed)
                        if self._accept_drop_proxy_fn:
                            self._tree_view.set_accept_drop_fn(self._on_tree_accept_drop)
                        if self._drop_proxy_fn:
                            self._tree_view.set_drop_fn(self._on_tree_drop)
                    self._catalog_filler = ui.Rectangle(style={"background_color": 0xFF2D2D2D})
                ui.Spacer(width=10)
            if self._drop_overlay_controller:
                self._drop_overlay_controller.build()
                self._wire_catalog_bg_overlay()

        field_model = self._GraphEditorCoreCatalog__search_field._search_field.model
        self._GraphEditorCoreCatalog__filter_subscription = field_model.subscribe_value_changed_fn(
            lambda m: self._GraphEditorCoreCatalog__filter_by_text(m.as_string)
        )
        self._apply_tab_filter()

        scroll_ref = self._scroll_frame
        overhead = 100
        _last_wh = [0]

        def _get_window_height():
            from ....extension import get_graph_window

            gw = get_graph_window()
            if gw:
                return gw.height
            window = ui.Workspace.get_window("Material Graph")
            return window.height if window else 0

        def _apply_scroll_height():
            try:
                wh = _get_window_height()
            except Exception:
                return
            if wh > overhead + 50 and wh != _last_wh[0]:
                _last_wh[0] = wh
                scroll_ref.height = ui.Pixel(wh - overhead)

        async def _initial_apply():
            for _ in range(10):
                await omni.kit.app.get_app().next_update_async()
            _apply_scroll_height()

        if self._lifecycle:
            self._lifecycle.add_task(_initial_apply())

        self._apply_scroll_height = _apply_scroll_height

        from ....extension import get_graph_window

        gw = get_graph_window()
        if gw:
            self._window_size_sub = gw.set_height_changed_fn(lambda h: _apply_scroll_height())
            self._window_size_sub_w = gw.set_width_changed_fn(lambda w: _apply_scroll_height())

    _PANEL_BG = 0xFF2D2D2D

    def _wire_catalog_bg_overlay(self) -> None:
        """Wire the drop overlay to change catalog backgrounds (matches graph overlay)."""
        scroll_ref = self._scroll_frame
        filler_ref = getattr(self, "_catalog_filler", None)
        saved_bg: list = [None]
        panel_bg = self._PANEL_BG

        def _set_bg(color: Optional[int]) -> None:
            if color is None:
                bg = saved_bg[0] if saved_bg[0] is not None else panel_bg
                saved_bg[0] = None
            else:
                if saved_bg[0] is None:
                    saved_bg[0] = panel_bg
                bg = color
            if scroll_ref:
                style = dict(scroll_ref.style) if scroll_ref.style else {}
                sf = dict(style.get("TreeView.ScrollingFrame", {}))
                tv = dict(style.get("TreeView", {}))
                sf["background_color"] = bg
                tv["background_color"] = bg
                style["TreeView.ScrollingFrame"] = sf
                style["TreeView"] = tv
                scroll_ref.style = style
            if filler_ref:
                filler_ref.style = {"background_color": bg}

        self._drop_overlay_controller.set_background_fn(_set_bg)

    @property
    def drop_overlay_controller(self) -> CatalogDropOverlayController:
        """Return the catalog drop overlay controller."""
        return self._drop_overlay_controller

    def _on_hovered(self, hovered: bool) -> None:
        """Hide drop overlay when pointer leaves the catalog frame."""
        if not hovered:
            if self._drop_overlay_controller:
                self._drop_overlay_controller.hide()

    def get_active_tab(self) -> str:
        """Return the active catalog tab."""
        return self._active_tab

    def should_block_delete_nodes(self) -> bool:
        """Return True when catalog should consume delete."""
        if self._active_tab not in (CATALOG_TAB_TEXTURES, CATALOG_TAB_NODEGRAPHS):
            return False
        if not self._tree_view:
            return False
        selection = list(self._tree_view.selection or [])
        if not selection:
            return False
        if self._active_tab == CATALOG_TAB_TEXTURES:
            return any(isinstance(item, (GroupItem, TextureItem)) for item in selection)
        return any(isinstance(item, (GroupItem, CompoundItem)) for item in selection)

    _TAB_ACTIVE_TEXT = 0xFFFFFFFF
    _TAB_INACTIVE_TEXT = 0xFFAAAAAA
    _TAB_HOVER_TEXT = 0xFFFFFFFF
    _TAB_ACCENT = CATALOG_ACTIVE_TAB_COLOR

    def _build_tabs(self) -> None:
        """Build catalog tabs for nodes, nodegraphs, and textures."""

        def set_tab(name: str) -> None:
            """Activate tab, update filters, and refresh tab visuals."""
            self._active_tab = name
            self._apply_tab_filter()
            self._refresh_tabs()

        with ui.HStack(height=24, spacing=0):
            for key, label in [
                (CATALOG_TAB_NODES, "Nodes"),
                (CATALOG_TAB_NODEGRAPHS, "NodeGraphs"),
                (CATALOG_TAB_TEXTURES, "Textures"),
            ]:
                is_active = self._active_tab == key
                with ui.VStack(width=0, height=0, spacing=0):
                    ui.Button(
                        label,
                        clicked_fn=lambda k=key: set_tab(k),
                        style={
                            "Button": {
                                "background_color": 0x00000000,
                                "border_radius": 0,
                                "border_width": 0,
                                "margin": 0,
                                "padding": 6,
                            },
                            "Button:hovered": {"background_color": 0x00000000},
                            "Button.Label": {
                                "color": self._TAB_ACTIVE_TEXT if is_active else self._TAB_INACTIVE_TEXT,
                                "font_size": 14,
                            },
                            "Button.Label:hovered": {
                                "color": self._TAB_ACTIVE_TEXT if is_active else self._TAB_HOVER_TEXT,
                            },
                        },
                        height=20,
                        width=0,
                    )
                    if is_active:
                        ui.Rectangle(height=2, style={"background_color": self._TAB_ACCENT})
                    else:
                        ui.Spacer(height=2)
            ui.Spacer()

    def _refresh_tabs(self) -> None:
        """Rebuild tab UI on next frame to reflect active tab state."""
        if not self._tabs_frame:
            return

        async def refresh_async() -> None:
            """Recreate tab controls after next frame to avoid stale UI refs."""
            await omni.kit.app.get_app().next_update_async()
            if not self._tabs_frame:
                return
            self._tabs_frame.clear()
            with self._tabs_frame:
                self._build_tabs()

        if self._lifecycle:
            self._lifecycle.add_task(refresh_async(), label="catalog tabs refresh")

    def _apply_tab_filter(self) -> None:
        """Apply model-side filtering to match current catalog tab."""
        model = self._GraphEditorCoreCatalog__model
        if self._active_tab == CATALOG_TAB_TEXTURES:
            model.set_filter_group(CATALOG_TAB_TEXTURES)
        elif self._active_tab == CATALOG_TAB_NODEGRAPHS:
            model.set_filter_group(CATALOG_TAB_NODEGRAPHS)
        else:
            model.set_filter_group(CATALOG_TAB_NODES)

    def handle_texture_drop(
        self,
        payload: dict,
        event: Optional[ui.WidgetMouseDropEvent] = None,
        target_group: Optional[GroupItem] = None,
    ) -> None:
        """Handle moving a texture item to a new group."""
        if self._active_tab != CATALOG_TAB_TEXTURES:
            return
        source = payload.get("source")
        if not source:
            return
        registry = get_texture_registry()
        item = registry.get_item_by_source(source)
        if not item:
            return
        if target_group is None:
            target_group = self._resolve_drop_group()
        group_name = target_group.name if target_group else ""
        if item.group == group_name:
            return
        if not registry.assign_group(item, group_name):
            logger.warning("failed to assign texture '%s' to group '%s'", item.name, group_name)

    def handle_compound_drop(
        self,
        payload: dict,
        event: Optional[ui.WidgetMouseDropEvent] = None,
        target_group: Optional[GroupItem] = None,
    ) -> None:
        """Handle moving a compound item to a new group."""
        if self._active_tab != CATALOG_TAB_NODEGRAPHS:
            return
        source_asset = payload.get("source_asset")
        identifier = payload.get("identifier")
        if not source_asset or not identifier:
            return
        registry = get_compound_registry()
        item = registry.get_item_by_identifier(source_asset, identifier)
        if not item:
            return
        if target_group is None:
            target_group = self._resolve_drop_group()
        group_name = target_group.name if target_group else ""
        if item.group == group_name:
            return
        if not registry.assign_group(item, group_name):
            logger.warning("failed to assign compound '%s' to group '%s'", item.name, group_name)

    def _parse_payload(self, data: str) -> Optional[dict]:
        """Parse drop payload JSON into a dictionary, if valid."""
        if not data:
            return None
        text = data.strip()
        # Plain path drops are expected for import workflows; only attempt JSON
        # parsing for payloads that look like JSON objects/arrays.
        if not text.startswith(("{", "[")):
            return None
        try:
            payload = json.loads(text)
            return payload if isinstance(payload, dict) else None
        except (RuntimeError, ValueError, TypeError, AttributeError) as exc:  # pylint: disable=broad-exception-caught
            logger.warning("catalog JSON drop payload parse failed (length=%s): %s", len(text), exc)
            return None

    def accept_group_drop(self, item: ui.AbstractItem, data: str) -> bool:
        """Return True when payload can be dropped onto the given group item."""
        if self._active_tab not in (CATALOG_TAB_TEXTURES, CATALOG_TAB_NODEGRAPHS):
            return False
        if isinstance(item, GroupItem) and item.is_texture_group:
            payload = self._parse_payload(data)
            return bool(payload and payload.get("type") == "Texture" and payload.get("source"))
        if isinstance(item, GroupItem) and item.is_compound_group:
            payload = self._parse_payload(data)
            return bool(payload and payload.get("type") == "ImportNodeGraph")
        return False

    def drop_on_group(self, item: ui.AbstractItem, event: ui.WidgetMouseDropEvent) -> None:
        """Route a group drop event to texture/compound move handlers."""
        if not isinstance(item, GroupItem):
            return
        payload = self._parse_payload(event.mime_data)
        if not payload:
            return
        if item.is_texture_group and payload.get("type") == "Texture":
            self.handle_texture_drop(payload, event, target_group=item)
            return
        if item.is_compound_group and payload.get("type") == "ImportNodeGraph":
            self.handle_compound_drop(payload, event, target_group=item)

    def _resolve_drop_group(self) -> Optional[GroupItem]:
        """Resolve the target group for a drop event.

        Group-row drops are handled directly by the delegate's per-row drop
        handlers.  When the tree-level handler fires the drop landed outside
        any group row, so we return None (ungroup / default).
        """
        return None

    def _on_mouse_pressed_proxy(self, x: float, y: float, button: int, modifier: int) -> None:
        """Proxy mouse press to track last clicked group and show item context menus."""
        if button == 1 and self._tree_view and self._active_tab in (CATALOG_TAB_TEXTURES, CATALOG_TAB_NODEGRAPHS):
            self._lifecycle.add_task(
                self._handle_deferred_right_click(x, y, button, modifier), label="deferred right-click"
            )
            return
        try:
            self._GraphEditorCoreCatalog__on_mouse_pressed(x, y, button, modifier)
        finally:
            if not self._tree_view:
                return
            self._update_last_clicked_group(list(self._tree_view.selection or []))

    async def _handle_deferred_right_click(self, x: float, y: float, button: int, modifier: int) -> None:
        """Deferred right-click handler that runs after delegate widget handlers have fired."""
        await omni.kit.app.get_app().next_update_async()
        delegate = self._GraphEditorCoreCatalog__delegate
        clicked_item = getattr(delegate, "right_clicked_item", None)
        if hasattr(delegate, "right_clicked_item"):
            delegate.right_clicked_item = None
        if clicked_item is not None and self._show_item_context_menu([clicked_item]):
            self._update_last_clicked_group([clicked_item])
            return
        try:
            self._GraphEditorCoreCatalog__on_mouse_pressed(x, y, button, modifier)
        finally:
            if self._tree_view:
                self._update_last_clicked_group(list(self._tree_view.selection or []))

    def _update_last_clicked_group(self, selection: List[ui.AbstractItem]) -> None:
        """Track the most recently clicked catalog group."""
        if selection:
            item = selection[0]
            if isinstance(item, GroupItem):
                self._last_clicked_group = item

    def _show_item_context_menu(self, selection: List[ui.AbstractItem]) -> bool:
        """Show a context menu for the selected catalog items. Returns True if shown."""
        if self._active_tab == CATALOG_TAB_TEXTURES:
            return self._show_texture_context_menu(selection)
        if self._active_tab == CATALOG_TAB_NODEGRAPHS:
            return self._show_nodegraph_context_menu(selection)
        return False

    def _show_texture_context_menu(self, selection: List[ui.AbstractItem]) -> bool:
        """Show context menu for texture items/groups."""
        groups = [i for i in selection if isinstance(i, GroupItem) and i.is_texture_group]
        textures = [i for i in selection if isinstance(i, TextureItem)]
        if not groups and not textures:
            return False
        self._item_context_menu = ui.Menu("Catalog Item")
        with self._item_context_menu:
            if groups:
                label = "Delete Group" if len(groups) == 1 else "Delete Groups"
                ui.MenuItem(label, triggered_fn=lambda g=groups: self._confirm_remove_groups(g))
            if textures:
                label = "Delete Texture" if len(textures) == 1 else "Delete Textures"
                ui.MenuItem(label, triggered_fn=lambda t=textures: self._confirm_remove_textures(t))
        show_menu_at_cursor(self._item_context_menu)
        return True

    def _show_nodegraph_context_menu(self, selection: List[ui.AbstractItem]) -> bool:
        """Show context menu for nodegraph items/groups."""
        groups = [i for i in selection if isinstance(i, GroupItem) and i.is_compound_group]
        compounds = [i for i in selection if isinstance(i, CompoundItem)]
        if not groups and not compounds:
            return False
        self._item_context_menu = ui.Menu("Catalog Item")
        with self._item_context_menu:
            if groups:
                label = "Delete Group" if len(groups) == 1 else "Delete Groups"
                ui.MenuItem(label, triggered_fn=lambda g=groups: self._confirm_remove_compound_groups(g))
            if compounds:
                label = "Delete Nodegraph" if len(compounds) == 1 else "Delete Nodegraphs"
                ui.MenuItem(label, triggered_fn=lambda c=compounds: self._confirm_remove_compounds(c))
        show_menu_at_cursor(self._item_context_menu)
        return True

    def _on_key_pressed(self, key: int, _modifier: int, pressed: bool) -> bool:
        """Handle delete/backspace actions for texture/compound catalog tabs."""
        if not self._should_handle_delete_key(key, pressed):
            return False
        selection = list(self._tree_view.selection or [])
        if not selection:
            return True
        if self._active_tab == CATALOG_TAB_TEXTURES:
            self._handle_texture_delete_selection(selection)
            return True
        if self._active_tab == CATALOG_TAB_NODEGRAPHS:
            self._handle_nodegraph_delete_selection(selection)
            return True
        return True

    def _should_handle_delete_key(self, key: int, pressed: bool) -> bool:
        """Return True when key event should trigger catalog deletion flow."""
        if not pressed or not self._tree_view:
            return False
        if key not in (int(carb.input.KeyboardInput.DEL), int(carb.input.KeyboardInput.BACKSPACE)):
            return False
        return self._active_tab in (CATALOG_TAB_TEXTURES, CATALOG_TAB_NODEGRAPHS)

    def _handle_texture_delete_selection(self, selection: List[ui.AbstractItem]) -> None:
        """Handle delete actions for texture tab selection."""
        groups = [item for item in selection if isinstance(item, GroupItem) and item.is_texture_group]
        textures = [item for item in selection if isinstance(item, TextureItem)]
        if groups:
            self._confirm_remove_groups(groups)
            return
        if textures:
            self._confirm_remove_textures(textures)

    def _handle_nodegraph_delete_selection(self, selection: List[ui.AbstractItem]) -> None:
        """Handle delete actions for nodegraph tab selection."""
        groups = [item for item in selection if isinstance(item, GroupItem) and item.is_compound_group]
        compounds = [item for item in selection if isinstance(item, CompoundItem)]
        if groups:
            self._confirm_remove_compound_groups(groups)
            return
        if compounds:
            self._confirm_remove_compounds(compounds)

    def _confirm_remove_textures(self, items: List[TextureItem]) -> None:
        """Ask for confirmation before deleting selected textures."""
        registry = get_texture_registry()

        def _apply(dialog: MessageDialog) -> None:
            """Apply texture deletion after user confirmation."""
            for item in items:
                registry.remove_texture(item)
            dialog.hide()

        title = "Remove Texture" if len(items) == 1 else "Remove Textures"
        message = "Remove selected texture?" if len(items) == 1 else "Remove selected textures?"
        self._delete_dialog = MessageDialog(
            title=title,
            message=message,
            ok_handler=_apply,
            ok_label="Remove",
        )
        self._delete_dialog.show()

    def _confirm_remove_groups(self, items: List[GroupItem]) -> None:
        """Ask for confirmation before deleting texture groups."""
        registry = get_texture_registry()

        def _apply(dialog: MessageDialog) -> None:
            """Apply group deletion after user confirmation."""
            for item in items:
                registry.remove_group(item.name)
            dialog.hide()

        title = "Remove Group" if len(items) == 1 else "Remove Groups"
        message = (
            "Remove selected group and its textures?"
            if len(items) == 1
            else "Remove selected groups and their textures?"
        )
        self._delete_dialog = MessageDialog(
            title=title,
            message=message,
            ok_handler=_apply,
            ok_label="Remove",
        )
        self._delete_dialog.show()

    def _confirm_remove_compounds(self, items: List[CompoundItem]) -> None:
        """Ask for confirmation before deleting selected compound entries."""
        registry = get_compound_registry()

        def _apply(dialog: MessageDialog) -> None:
            """Apply compound deletion after user confirmation."""
            for item in items:
                registry.remove_compound(item)
            dialog.hide()

        title = "Remove Nodegraph" if len(items) == 1 else "Remove Nodegraphs"
        message = "Remove selected nodegraph file?" if len(items) == 1 else "Remove selected nodegraph files?"
        self._delete_dialog = MessageDialog(
            title=title,
            message=message,
            ok_handler=_apply,
            ok_label="Remove",
        )
        self._delete_dialog.show()

    def _confirm_remove_compound_groups(self, items: List[GroupItem]) -> None:
        """Ask for confirmation before deleting compound groups."""
        registry = get_compound_registry()

        def _apply(dialog: MessageDialog) -> None:
            """Apply compound-group deletion after user confirmation."""
            for item in items:
                registry.remove_group(item.name)
            dialog.hide()

        title = "Remove Group" if len(items) == 1 else "Remove Groups"
        message = "Remove selected group?" if len(items) == 1 else "Remove selected groups?"
        self._delete_dialog = MessageDialog(
            title=title,
            message=message,
            ok_handler=_apply,
            ok_label="Remove",
        )
        self._delete_dialog.show()

    def handle_item_double_clicked(self, item: ui.AbstractItem) -> None:
        """Handle double click rename for textures/groups."""
        if self._active_tab not in (CATALOG_TAB_TEXTURES, CATALOG_TAB_NODEGRAPHS):
            return
        if self._active_tab == CATALOG_TAB_NODEGRAPHS:
            self._handle_nodegraph_double_click(item)
            return
        self._handle_texture_double_click(item)

    def _show_rename_dialog(self, title: str, default_value: str, apply_fn) -> None:
        """Show a rename dialog with consistent shape."""
        self._rename_dialog = InputDialog(
            title=title,
            width=300,
            message="New name:",
            default_value=default_value,
            ok_handler=apply_fn,
        )
        self._rename_dialog.show()

    def _handle_nodegraph_double_click(self, item: ui.AbstractItem) -> None:
        """Handle rename flow for nodegraph tab entries."""
        registry = get_compound_registry()
        if isinstance(item, CompoundItem):
            current = item.name_model.get_value_as_string()

            def _apply(dialog: InputDialog) -> None:
                """Apply a validated nodegraph name to the selected compound entry."""
                new_name = dialog.get_value()
                if isinstance(new_name, str) and new_name.strip():
                    registry.rename_compound(item, new_name.strip())
                dialog.hide()

            self._show_rename_dialog("Rename Nodegraph", current, _apply)
            return
        if isinstance(item, GroupItem) and item.is_compound_group:
            current = item.name

            def _apply(dialog: InputDialog) -> None:
                """Apply a validated name to the selected compound group."""
                new_name = dialog.get_value()
                if isinstance(new_name, str) and new_name.strip():
                    registry.rename_group(current, new_name.strip())
                dialog.hide()

            self._show_rename_dialog("Rename Group", current, _apply)

    def _handle_texture_double_click(self, item: ui.AbstractItem) -> None:
        """Handle rename flow for texture tab entries."""
        registry = get_texture_registry()
        if isinstance(item, TextureItem):
            current = item.name_model.get_value_as_string()

            def _apply(dialog: InputDialog) -> None:
                """Apply a validated texture name to the selected texture item."""
                new_name = dialog.get_value()
                if isinstance(new_name, str) and new_name.strip():
                    registry.rename_texture(item, new_name.strip())
                dialog.hide()

            self._show_rename_dialog("Rename Texture", current, _apply)
            return
        if isinstance(item, GroupItem) and item.is_texture_group:
            current = item.name

            def _apply(dialog: InputDialog) -> None:
                """Apply a validated name to the selected texture group."""
                new_name = dialog.get_value()
                if isinstance(new_name, str) and new_name.strip():
                    registry.rename_group(current, new_name.strip())
                dialog.hide()

            self._show_rename_dialog("Rename Group", current, _apply)

    def destroy(self) -> None:
        """Release catalog lifecycle resources, overlay controller, and pending async tasks."""
        self._catalog_filler = None
        self._item_context_menu = None
        if self._lifecycle:
            self._lifecycle.cleanup()
            self._lifecycle = None
        if self._drop_overlay_controller:
            self._drop_overlay_controller.destroy()
            self._drop_overlay_controller = None
