# SPDX-FileCopyrightText: Copyright (c) 2024-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.


from functools import partial

import carb.input
import omni.kit.clipboard as clipboard
import omni.ui as ui
import omni.usd
from pxr import Sdf

from ..style import *
from ..utils import show_tooltip
from .generic import GenericWidget


def is_path(text):
    """
    Return true if the given text is a prim path, based
    on a simple heuristic for now: if the string starts
    with a forward slash, it's considered a path.
    """
    return text and text[0] == "/"


class InfoItem(ui.AbstractItem):
    """Info table item"""

    def __init__(self, message):

        super().__init__()

        self._model = ui.SimpleStringModel(message)


class InfoModel(ui.AbstractItemModel):
    """Data Model for log/report info messages"""

    def __init__(self, entries):

        super().__init__()

        self._children = list()
        self.add_items(entries)

    def add_items(self, entries):
        """Populate the model"""

        for entry in entries:
            self._children.append(InfoItem(entry.message))

        # Notify of change
        self._item_changed(None)

    def get_item_children(self, item):
        """Return the children of an item."""

        # This is a table really, not a tree, so if we are not the root item
        # we have no children to return.
        if item is not None:
            return []

        return self._children

    def clear(self):
        """Clear any existing items"""
        self._children = list()
        self._item_changed(None)

    def get_item_value_model_count(self, item):
        """The number of columns"""
        return 1

    def get_item_value_model(self, item, column_id):
        """Return the value of an item for the specified column"""
        return item._model


class InfoDelegate(ui.AbstractItemDelegate):
    """Item Delegate to control style a little better"""

    def __init__(self, report_widget):

        super().__init__()
        self._report_widget = report_widget

    def build_widget(self, model, item, column_id, level, expanded):
        """Build the widget for a cell"""

        style = {"margin": 6}

        text = model.get_item_value_model(item, column_id).as_string

        if not text:
            return

        if is_path(text):
            style["TreeView.Item.Title"] = {"color": ui.color(140, 150, 150)}

        label = ui.Label(
            text,
            style_type_name_override="TreeView.Item.Title",
            style=style,
        )

        label.set_computed_content_size_changed_fn(partial(self._report_widget._item_content_size_changed, label))


class CoincidingWidget(GenericWidget):
    """
    Widget for displaying results of the FindCoincidingGeometry operation.  It displays INFO
    entries in a tree view with a single column and provides a workaround for a known issue
    where long text in a tree view gets cut off when scrolling horizontally.
    """

    def __init__(self, entries):

        # Get the INFO entries which, will be displayed separately.
        self._info_entries = list(filter(lambda e: e.level == "INFO", entries))

        # Filtered list of items to build the inherited GenericWidget GUI that will
        # display the non-INFO log entries.
        filtered_entries = list(filter(lambda e: e.level != "INFO", entries))

        super().__init__(filtered_entries)

        self._info_model = InfoModel(self._info_entries)
        self._info_delegate = InfoDelegate(self)

        self._menu = ui.Menu(menu_compatibility=False, style={"padding": 2})

        # Value of the last hovered path entry.
        self._hovered_path = None

        # Default path argument for the select and copy operations.
        self._default_path_arg = None

        self._selected_paths = []

        self._tree_view = None

    def build_widget(self):

        height = max(100, min(len(self._info_model.get_item_children(None)) * 31, 250))

        with ui.VStack(style={"margin": 0, "padding": 0}, height=ui.Percent(100)):
            # Build the inherited log view, if there are non INFO items to display.
            if self._data_model and self._data_model.get_item_children(None):
                super().build_widget(height=0)
                ui.Spacer(height=10)

            scroll = ui.ScrollingFrame(
                height=height,
                style_type_name_override="TreeView",
            )

            with scroll:
                self._tree_view = ui.TreeView(
                    self._info_model,
                    delegate=self._info_delegate,
                    root_visible=False,
                    header_visible=False,
                    style=TREE_VIEW_STYLE,
                )
                self._tree_view.set_selection_changed_fn(self._on_selection_changed)
                self._tree_view.set_hover_changed_fn(self._item_hovered)
                self._tree_view.set_mouse_pressed_fn(self._mouse_pressed)

    def _item_content_size_changed(self, item):
        """
        Adjusts the width of the tree view to accomodate the widest item.
        This is a workaround to known issues OM-60045 and OM-87810 where
        tree view items get cut off when scrolling.
        """
        width = ui.Length(item.computed_width)
        if width != self._tree_view.width:
            self._tree_view.width = width

    def _on_selection_changed(self, selection):

        # The selected paths
        self._selected_paths = []
        for item in selection:
            if not isinstance(item, InfoItem):
                continue
            text = item._model.get_value_as_string()
            if not (is_path(text) and Sdf.Path.IsValidPathString(text)):
                # Not a path
                continue
            self._selected_paths.append(text)

    def _mouse_pressed(self, posX, posY, button, modifier):

        if button == 1:
            self._menu.clear()
            if not self._hovered_path:
                return

            self._default_path_arg = self._hovered_path

            with self._menu:
                item = ui.MenuItem("Select Prim", menu_compatibility=False)
                item.set_triggered_fn(self._select_prims)
                ui.Separator(menu_compatibility=False)

                item = ui.MenuItem("Copy Path", menu_compatibility=False)
                item.set_triggered_fn(self._copy_paths)

            self._menu.show()

    def _item_hovered(self, item: ui.AbstractItem, hovered: bool):
        text = item._model.get_value_as_string()
        if not is_path(text):
            return
        if hovered:
            self._hovered_path = text
        elif self._hovered_path == text:
            self._hovered_path = None

    def _select_prims(self):
        if not (self._selected_paths or self._default_path_arg):
            return
        sel = omni.usd.get_context().get_selection()
        if self._selected_paths:
            sel.set_selected_prim_paths(self._selected_paths)
        else:
            sel.set_selected_prim_paths([self._default_path_arg])

    def _copy_paths(self):
        if not (self._selected_paths or self._default_path_arg):
            return
        if self._selected_paths:
            clipboard.copy(str(self._selected_paths))
        else:
            clipboard.copy(self._default_path_arg)
