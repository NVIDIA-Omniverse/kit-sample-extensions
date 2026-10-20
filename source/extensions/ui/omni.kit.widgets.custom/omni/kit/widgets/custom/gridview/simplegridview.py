# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
import asyncio

import omni
from omni import ui

from ..constant import COLORS, MouseKey
from ..model import SimpleListModel
from ..style import get_ui_style
from .style import UI_STYLES


class SimpleGridView:
    def __init__(self, **kwargs):
        # Args
        self._model = kwargs.get("model", SimpleListModel())
        self._delegate = kwargs.get("delegate", ui.AbstractItemDelegate())
        self._on_clicked_fn = kwargs.get("on_clicked_fn", None)
        self._on_rclicked_fn = kwargs.get("on_rclicked_fn", None)
        self._on_double_clicked_fn = kwargs.get("on_double_clicked_fn", None)
        self._on_drag_fn = kwargs.get("on_drag_fn", None)
        self._padding_x = kwargs.get("padding_x", 1)
        self._padding_y = kwargs.get("padding_y", 1)

        frame_kwargs = {
            "vertical_scrollbar_policy": kwargs.pop(
                "vertical_scrollbar_policy", ui.ScrollBarPolicy.SCROLLBAR_ALWAYS_OFF
            ),
            "horizontal_scrollbar_policy": kwargs.pop(
                "horizontal_scrollbar_policy", ui.ScrollBarPolicy.SCROLLBAR_ALWAYS_OFF
            ),
            "style": kwargs.get("style", UI_STYLES[get_ui_style()]),
        }
        for arg in ["width", "height"]:
            value = kwargs.pop(arg, None)
            if value is not None:
                frame_kwargs[arg] = value

        grid_kwargs = {}
        for arg in ["column_width", "column_count", "row_height", "row_count"]:
            value = kwargs.pop(arg, None)
            if value is not None:
                grid_kwargs[arg] = value

        # Build UI
        with ui.ScrollingFrame(style_type_name_override="GridView.Frame", **frame_kwargs):
            self._panel = ui.ZStack()
            with self._panel:
                self._background = ui.Rectangle(style_type_name_override="GridView.Grid")
                with ui.HStack():
                    ui.Spacer(width=self._padding_x)
                    with ui.VStack():
                        ui.Spacer(height=self._padding_y)
                        self._grid = ui.VGrid(**grid_kwargs)
                        ui.Spacer(height=self._padding_y)
                    ui.Spacer(width=self._padding_x)

        self._selections = []
        self._cards = {}
        self.rebuild_grid()

    @property
    def model(self):
        return self._model

    @model.setter
    def model(self, value):
        self._model = value
        self.rebuild_grid()

    @property
    def selections(self):
        return self._selections

    @selections.setter
    def selections(self, items):
        self._clear_selections()
        if type(items) == list:
            for item in items:
                self._add_selectioon(item)
        else:
            self._add_selectioon(items)

    @property
    def column_width(self):
        return self._grid.column_width

    @column_width.setter
    def column_width(self, value):
        self._grid.column_width = value
        self.on_width_changed()

    @property
    def row_height(self):
        return self._grid.row_height

    @row_height.setter
    def row_height(self, value):
        self._grid.row_height = value

    def insert_item(self, item, index=-1):
        self._model.insert_item(item, index=index)
        self.rebuild_grid()

    def clear(self):
        self._model.clear()
        self.rebuild_grid()

    def _create_grid_card(self, item):
        self._cards[item] = ui.ZStack()
        with self._cards[item]:
            self._delegate.build_widget(self._model, item)
            ui.Rectangle(
                mouse_pressed_fn=lambda x, y, btn, flag, item=item: self._on_mouse_pressed(btn, item),
                mouse_double_clicked_fn=lambda x, y, btn, flag, item=item: self._on_mouse_double_clicked(btn, item),
                style={"background_color": COLORS.TRANSPARENT},
            )
        if self._on_drag_fn:
            self._cards[item].set_drag_fn(lambda item=item: self._on_drag_fn(item))

    def _on_mouse_pressed(self, btn, item):
        if btn == MouseKey.LEFT:
            self._on_clicked(item)
        elif btn == MouseKey.RIGHT:
            self._on_rclicked(item)

    def _on_mouse_double_clicked(self, btn, item):
        if btn == MouseKey.LEFT:
            if self._on_double_clicked_fn:
                self._on_double_clicked_fn(item)

    def _on_clicked(self, item):
        if item in self._selections:
            self._clear_selections()
        else:
            self._clear_selections()
            self._add_selectioon(item)

        if self._on_clicked_fn:
            self._on_clicked_fn(item)

    def _on_rclicked(self, item):
        if item not in self._selections:
            self._clear_selections()
            self._add_selectioon(item)

        if self._on_rclicked_fn:
            self._on_rclicked_fn(item)

    def _clear_selections(self):
        for item in self._selections:
            self._cards[item].selected = False
        self._selections.clear()

    def _add_selectioon(self, item):
        self._selections.append(item)
        self._cards[item].selected = True

    def rebuild_grid(self):
        self._panel.visible = False
        self._clear_selections()
        self._cards.clear()
        self._grid.clear()
        if self._model is None:
            return
        children = self._model.get_item_children()
        if children is None or len(children) == 0:
            return
        self._panel.visible = True
        with self._grid:
            for item in children:
                self._create_grid_card(item)
        self.on_width_changed()

    def on_width_changed(self):
        asyncio.ensure_future(self._reset_grid_background_width())

    async def _reset_grid_background_width(self):
        await omni.kit.app.get_app().next_update_async()
        self._background.width = ui.Pixel(self._grid.column_count * self._grid.column_width + 2 * self._padding_x)
