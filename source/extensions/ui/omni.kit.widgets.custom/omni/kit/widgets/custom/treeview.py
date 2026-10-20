# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
import carb
from omni import ui

from .constant import COLORS, DarkColors, FontSize, LightColors, MouseKey
from .model import SimpleListModel
from .style import get_ui_style


class SimpleListView:
    LIGHT_STYLE = {
        "TreeView": {"background_color": LightColors.Background, "secondary_color": COLORS.TRANSPARENT},
        "TreeView.Frame": {
            "background_color": LightColors.Background,
            "secondary_color": LightColors.Text,
            "border_radius": 0,
        },
        "TreeView.Item": {"color": LightColors.Text, "margin": 4},
        "TreeView.Item:hovered": {"background_color": LightColors.BackgroundHovered},
        "TreeView.Item:selected": {"background_color": LightColors.BackgroundSelected},
    }
    DARK_STYLE = {
        "TreeView": {"background_color": DarkColors.Background, "secondary_color": COLORS.TRANSPARENT},
        "TreeView.Frame": {
            "background_color": DarkColors.Background,
            "secondary_color": DarkColors.Text,
            "border_radius": 0,
        },
        "TreeView.Item": {"color": DarkColors.Text, "margin": 4},
        "TreeView.Item:hovered": {"background_color": LightColors.BackgroundHovered},
        "TreeView.Item:selected": {"background_color": DarkColors.BackgroundSelected},
    }
    UI_STYLES = {"NvidiaLight": LIGHT_STYLE, "NvidiaDark": DARK_STYLE}

    def __init__(
        self,
        model=SimpleListModel(columns_count=1),
        column_widths=[],
        on_item_selected_fn=None,
        multi_selection=False,
        root_visible=False,
        header_visible=False,
        **kwargs,
    ):
        self._multi_selection = multi_selection
        self._on_item_selected_fn = on_item_selected_fn

        frame_kwargs = {
            "vertical_scrollbar_policy": kwargs.pop(
                "vertical_scrollbar_policy", ui.ScrollBarPolicy.SCROLLBAR_ALWAYS_OFF
            ),
            "horizontal_scrollbar_policy": kwargs.pop(
                "horizontal_scrollbar_policy", ui.ScrollBarPolicy.SCROLLBAR_ALWAYS_OFF
            ),
            "style": kwargs.get("style", self.UI_STYLES[get_ui_style()]),
        }
        for arg in ["height"]:
            value = kwargs.pop(arg, None)
            if value is not None:
                frame_kwargs[arg] = value

        with ui.ScrollingFrame(style_type_name_override="TreeView.Frame", **frame_kwargs):
            self._tree_view = ui.TreeView(model, root_visible=root_visible, header_visible=header_visible, **kwargs)
        self._tree_view.set_selection_changed_fn(self._on_selection_changed)
        if len(column_widths) > 0:
            self._tree_view.column_widths = column_widths

    def destroy(self):
        self._tree_view.model = None
        self._tree_view = None

    @property
    def treeview(self):
        return self._tree_view

    @property
    def model(self):
        return self._tree_view.model

    @model.setter
    def model(self, value):
        self.update_data(value)

    @property
    def items(self):
        return self._tree_view.model.get_item_children(None)

    @property
    def selection(self):
        selections = self._tree_view.selection
        if len(selections) == 0:
            return []
        else:
            items = self.items
            indexes = []
            for item in selections:
                indexes.append(items.index(item))
            return indexes

    @selection.setter
    def selection(self, indexes):
        if len(indexes) == 0:
            self._tree_view.clear_selection()
        else:
            items = self.items
            selections = []
            for index in indexes:
                if index >= len(items) or index < 0:
                    carb.log_error("[Listview] selection out of range!")
                else:
                    selections.append(items[index])
            self._tree_view.selection = selections

    @property
    def selection_items(self):
        return self._tree_view.selection

    def update_data(self, model):
        if model is not None:
            self._tree_view.model = model
            self.selection = []

    def insert(self, item, index=-1):
        self._tree_view.model.insert_item(item, index=index)

    def clear(self):
        self._tree_view.model.clear()

    def remove_selected(self):
        selected = self.selection
        if len(selected) > 0:
            # FIXME: added in a reverse index deletion so deleting a previous item won't affect item indices,
            # but may need a more elegant solution (or maybe to be safe, need to remove by value here)
            for index in reversed(sorted(selected)):
                self._tree_view.model.remove_index(index)

    def _on_selection_changed(self, selections):
        if len(selections) == 0:
            return

        if not self._multi_selection:
            # Diable multi selection
            if selections and len(selections) > 1:
                selections = selections[-1:]
                self._tree_view.selection = selections

        for item in selections:
            if self._on_item_selected_fn:
                self._on_item_selected_fn(item)
