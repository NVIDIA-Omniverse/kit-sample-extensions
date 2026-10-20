"""Catalog tree delegate responsible for rendering and interaction in the catalog pane."""

from typing import Callable, Optional

import omni.ui as ui

# pylint: disable=no-member
from omni.kit.graph.editor.core.graph_editor_core_tree_delegate import ICON_PATH as _CORE_ICON_PATH
from omni.kit.graph.editor.core.graph_editor_core_tree_delegate import (
    GraphEditorCoreTreeDelegate,
)

from ....config.nodes import Nodes
from ....models.catalog.items.compound import CompoundItem
from ....models.catalog.items.shader import ShaderItem
from ....models.catalog.items.texture import TextureItem


class MaterialGraphCatalogDelegate(GraphEditorCoreTreeDelegate):
    """Catalog tree delegate with invalid texture styling."""

    def __init__(
        self,
        on_item_double_clicked: Optional[Callable[[ui.AbstractItem], None]] = None,
        on_group_accept_drop: Optional[Callable[[ui.AbstractItem, str], bool]] = None,
        on_group_drop: Optional[Callable[[ui.AbstractItem, ui.WidgetMouseDropEvent], None]] = None,
    ) -> None:
        """Initialize delegate callbacks for double-click and group drag/drop."""
        super().__init__()
        self._on_item_double_clicked = on_item_double_clicked
        self._on_group_accept_drop = on_group_accept_drop
        self._on_group_drop = on_group_drop
        self.right_clicked_item: Optional[ui.AbstractItem] = None

    _SECTION_BG = 0xFF2F2F2F

    def build_branch(self, model, item, column_id, level, expanded):
        """Override branch to match section background and spacing."""
        if model.can_item_have_children(item):
            with ui.ZStack():
                with ui.VStack():
                    ui.Spacer(height=3)
                    ui.Rectangle(height=self._section_height, style={"background_color": self._SECTION_BG})
                    ui.Spacer(height=3)
                with ui.VStack(width=0):
                    ui.Spacer(height=ui.Fraction(1.5))
                    thumbnail = "expanded" if expanded else "collapsed"
                    thumbnail = _CORE_ICON_PATH.joinpath(f"{thumbnail}.svg")
                    chevron = ui.ImageWithProvider(
                        f"{thumbnail}",
                        width=self._icon_size,
                        height=self._icon_size,
                        style_type_name_override="TreeView.Item.Title",
                    )
                    if self._on_expand:
                        chevron.set_mouse_pressed_fn(
                            lambda x, y, b, m, it=item, ex=expanded: (self._on_expand(it, not ex) if b == 0 else None)
                        )
                    ui.Spacer()

    def build_section_icon(self, model, item, column_id, level, expanded):
        """Override base spacer with increased left padding for section rows."""
        ui.Spacer(width=10, height=0)

    def _on_row_mouse_pressed(self, item: ui.AbstractItem, button: int) -> None:
        """Track the item under a right-click so the widget can show its context menu."""
        if button == 1:  # omni.ui uses button 1 for right mouse button.
            self.right_clicked_item = item
        else:
            self.right_clicked_item = None

    def build_section_widget(self, model, item, column_id, level, expanded):
        """Build a section row widget with optional group-drop handlers."""
        with ui.ZStack() as section_stack:
            ui.Rectangle(height=self._section_height, style={"background_color": self._SECTION_BG})
            with ui.HStack():
                self.build_section_icon(model, item, column_id, level, expanded)
                value_model = model.get_item_value_model(item, column_id)
                label = ui.Label(
                    value_model.as_string,
                    style_type_name_override="TreeView.Item.Title",
                    style={"TreeView.Item.Title": {"color": 0xFFD0D0D0}},
                    elided_text=True,
                )
                if self._on_item_double_clicked and (item.is_texture_group or item.is_compound_group):
                    label.set_mouse_double_clicked_fn(lambda *_: self._on_item_double_clicked(item))
                ui.Spacer(width=10)
        section_stack.set_mouse_pressed_fn(lambda x, y, b, m, it=item: self._on_row_mouse_pressed(it, b))
        if item.is_texture_group or item.is_compound_group:
            if self._on_group_accept_drop:
                section_stack.set_accept_drop_fn(lambda data, it=item: self._on_group_accept_drop(it, data))
            if self._on_group_drop:
                section_stack.set_drop_fn(lambda event, it=item: self._on_group_drop(it, event))

    def build_item_widget(
        self,
        model: ui.AbstractItemModel,
        item: ui.AbstractItem,
        column_id: int,
        level: int,
        expanded: bool,
    ) -> None:
        """Build a catalog item widget with invalid shading."""
        invalid = hasattr(item, "is_valid") and not item.is_valid
        with ui.ZStack() as item_stack:
            if invalid:
                ui.Rectangle(
                    height=self._item_size,
                    style={"background_color": Nodes.DROP_OVERLAY_REJECT_ABGR},
                    opaque_for_mouse_events=False,
                )

            style = {}
            if isinstance(item, ShaderItem) and item.icon:
                style = {"TreeView.Section.Icon": {"color": item.icon_color}}

            with ui.HStack(style=style):
                self.build_icon_with_tooltip(model, item, column_id, level, expanded)

                tooltip_model = model.get_item_value_model(item, 3)
                tooltip = ""
                if tooltip_model:
                    tooltip = tooltip_model.as_string
                tooltip_text = tooltip.strip()

                def _create_tooltip(text: str) -> None:
                    """Render tooltip label with width scaling for long text."""
                    if not text:
                        return
                    max_len = max([len(line) for line in text.split("\n")]) if text else 0
                    width = 350 if max_len > 175 else 0
                    ui.Label(text, word_wrap=True, width=width, style={"Label": {"color": 0xFF3B494B}})

                tooltip_kwargs = {"tooltip_fn": (lambda: _create_tooltip(tooltip_text))} if tooltip_text else {}
                with ui.VStack(spacing=5, height=self._item_size, **tooltip_kwargs):
                    ui.Spacer()
                    value_model = model.get_item_value_model(item, 0)
                    description_model = model.get_item_value_model(item, 1)
                    label = ui.Label(
                        value_model.as_string,
                        height=0,
                        style_type_name_override="TreeView.Item.Title",
                        style={"TreeView.Item.Title": {"color": 0xFFBBBBBB}},
                        elided_text=True,
                    )
                    if self._on_item_double_clicked and isinstance(item, (TextureItem, CompoundItem)):
                        label.set_mouse_double_clicked_fn(lambda *_: self._on_item_double_clicked(item))
                    if description_model and description_model.as_string:
                        description = description_model.as_string.partition("\n")[0]
                        ui.Label(
                            description,
                            height=0,
                            style_type_name_override="TreeView.Item.Description",
                            style={"TreeView.Item.Description": {"color": 0xFF808080}},
                            elided_text=True,
                        )
                    ui.Spacer()
        item_stack.set_mouse_pressed_fn(lambda x, y, b, m, it=item: self._on_row_mouse_pressed(it, b))
