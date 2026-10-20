# Copyright (c) 2018-2021, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#
__all__ = ["GraphEditorCoreTreeDelegate"]

from functools import partial
from pathlib import Path

import omni.ui as ui
from omni.ui import color as cl

CURRENT_PATH = Path(__file__).parent
ICON_PATH = CURRENT_PATH.parent.parent.parent.parent.parent.joinpath("icons")


class GraphEditorCoreTreeDelegate(ui.AbstractItemDelegate):
    """The delegate for TreeView of the MDL shader panel"""

    def __init__(self, flat=False):
        super().__init__()
        self._flat = flat
        self._filter_by_text = ""
        self._item_size = 50
        self._icon_size = 25
        self._section_height = 30
        self._on_expand = None

    def destroy(self):
        pass

    def set_on_expand_fn(self, fn):
        self._on_expand = fn

    def build_branch(self, model, item, column_id, level, expanded):
        """Create a branch widget that opens or closes subtree"""
        if model.can_item_have_children(item):
            with ui.ZStack():
                # Background Color
                with ui.VStack():
                    ui.Spacer(height=2)
                    # tried to use style_type_name_override="Rectangle", name="section_background", doesn't work
                    ui.Rectangle(height=self._section_height, style={"background_color": 0xFF343434})
                    ui.Spacer(height=2)

                with ui.VStack(width=0):
                    ui.Spacer(height=ui.Fraction(1.5))

                    thumbnail = "expanded" if expanded else "collapsed"
                    thumbnail = ICON_PATH.joinpath(f"{thumbnail}.svg")

                    ui.ImageWithProvider(
                        f"{thumbnail}",
                        width=self._icon_size,
                        height=self._icon_size,
                        style_type_name_override="TreeView.Item.Title",
                    )
                    ui.Spacer()

    def build_section_icon(self, model, item, column_id, level, expanded):
        """this function is used as the base class function to be override by inherited ones,
        so that we can add icon in front of the section item"""
        ui.Spacer(width=5, height=0)

    def build_section_widget(self, model, item, column_id, level, expanded):
        with ui.ZStack():
            # Background Color
            ui.Rectangle(height=self._section_height, style={"background_color": 0xFF343434})
            # Section Title
            with ui.HStack():
                self.build_section_icon(model, item, column_id, level, expanded)
                value_model = model.get_item_value_model(item, column_id)
                ui.Label(value_model.as_string, style_type_name_override="TreeView.Item.Title", elided_text=True)
                num_childreen = len(model.get_item_children(item))
                ui.Label(f"{num_childreen}", name="count", width=0)
                ui.Spacer(width=10)
            if self._on_expand:
                ui.Spacer(mouse_pressed_fn=lambda x, y, b, m: self._on_expand(item, not expanded))

    def build_icon_with_tooltip(self, model, item, column_id, level, expanded):
        def build_icon_tooltip(thumbnail: str):
            with ui.ZStack(width=0, height=0):
                ui.Rectangle()
                ui.Image(
                    f"{thumbnail}",
                    width=self._item_size * 2,
                    height=self._item_size * 2,
                    style_type_name_override="TreeView.Section.Icon",
                    name="Icon",
                )

        ui.Spacer(width=5)
        icon_model = model.get_item_value_model(item, 2)
        if icon_model:
            thumbnail = icon_model.as_string
            ui.Image(
                f"{thumbnail}",
                width=self._item_size - 10,
                alignment=ui.Alignment.CENTER,
                style_type_name_override="TreeView.Section.Icon",
                name="Icon",
                tooltip_fn=partial(build_icon_tooltip, thumbnail),
                style={
                    "Tooltip": {"background_color": cl(0, 0, 0, 0), "border_width": 0, "border_color": cl(0, 0, 0, 0)}
                },
            )
        ui.Spacer(width=5)

    def build_item_widget(self, model, item, column_id, level, expanded):
        """build the widget for the items"""
        with ui.HStack():
            self.build_icon_with_tooltip(model, item, column_id, level, expanded)

            tooltip_model = model.get_item_value_model(item, 3)
            tooltip = ""
            if tooltip_model:
                tooltip = tooltip_model.as_string
            if hasattr(item, "identifier"):
                tooltip += " " + item.identifier

            def _create_tooltip(text):
                """Create a tooltip in a fixed style, wrap the tooltip if the maximum line length is too long"""
                max_len = max([len(line) for line in text.split("\n")])
                width = 350 if max_len > 175 else 0
                ui.Label(text, word_wrap=True, width=width, style={"Label": {"color": 0xFF3B494B}})

            with ui.VStack(spacing=5, height=self._item_size, tooltip_fn=lambda: _create_tooltip(tooltip)):
                ui.Spacer()
                value_model = model.get_item_value_model(item, 0)
                description_model = model.get_item_value_model(item, 1)
                ui.Label(
                    value_model.as_string,
                    height=0,
                    style_type_name_override="TreeView.Item.Title",
                    elided_text=True,
                )
                if description_model and description_model.as_string:
                    description = description_model.as_string.partition("\n")[0]
                    ui.Label(
                        description, height=0, style_type_name_override="TreeView.Item.Description", elided_text=True
                    )
                ui.Spacer()

    def build_widget(self, model, item, column_id, level, expanded):
        if model.can_item_have_children(item):
            # Build the section_widget
            self.build_section_widget(model, item, column_id, level, expanded)
        else:
            self.build_item_widget(model, item, column_id, level, expanded)

    def filter_by_text(self, filter_name_text: str):
        """Saves the filtering text to use it when drawing the item"""
        self._filter_by_text = filter_name_text
