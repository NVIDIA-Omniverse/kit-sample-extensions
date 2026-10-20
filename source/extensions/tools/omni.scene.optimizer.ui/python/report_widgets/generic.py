# SPDX-FileCopyrightText: Copyright (c) 2023-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.


import re
from functools import partial

import omni.ui as ui

from ..style import *
from ..utils import show_tooltip


class GenericItem(ui.AbstractItem):
    """Generic table item"""

    def __init__(self, level, category, message):

        super().__init__()

        self.models = [ui.SimpleStringModel(level), ui.SimpleStringModel(message), ui.SimpleStringModel(category)]


class GenericModel(ui.AbstractItemModel):
    """Data Model for generic log/report info"""

    def __init__(self, entries):

        super().__init__()

        self._children = list()
        self.add_items(entries)

    def add_items(self, entries):
        """Populate the model"""

        for entry in entries:
            self._children.append(GenericItem(entry.level, entry.category, entry.message))

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
        return 3

    def get_item_value_model(self, item, column_id):
        """Return the value of an item for the specified column"""
        return item.models[column_id]


class GenericDelegate(ui.AbstractItemDelegate):
    """Item Delegate to control style a little better

    Allows us to define the headers.
    """

    def __init__(self):

        super().__init__()

    def build_header(self, column_id):
        """Build the widget for a column header"""

        margin = 6
        padding = 0

        if column_id == 0:
            ui.Label(
                "Level",
                tooltip_fn=partial(show_tooltip, "The severity level of the message"),
                style={"margin": margin, "padding": padding},
            )
        elif column_id == 1:
            ui.Label(
                "Message",
                tooltip_fn=partial(show_tooltip, "The report entry"),
                style={"margin": margin, "padding": padding},
            )
        elif column_id == 2:
            ui.Label(
                "Category",
                tooltip_fn=partial(show_tooltip, "The message category"),
                style={"margin": margin, "padding": padding},
            )

    def build_widget(self, model, item, column_id, level, expanded):
        """Build the widget for a cell"""

        style = {"margin": 6}

        # Adjust the first column color based on the message severity
        if column_id == 0:
            color = ui.color(0)
            level = model.get_item_value_model(item, column_id).as_string
            if level == "ERROR":
                color = ui.color(197, 115, 106)
            elif level == "WARNING":
                color = ui.color(226, 204, 74)
            elif level == "INFO":
                color = ui.color(121, 186, 235)
            elif level == "DEBUG":
                color = ui.color(128, 128, 128)
            style["color"] = color

        ui.Label(
            model.get_item_value_model(item, column_id).as_string,
            style_type_name_override="TreeView.Item.Title",
            style=style,
        )


class GenericWidget:
    """Custom widget to display operation report entries for the Scene Optimizer,
    where they don't have a specific widget to handle their custom data.
    """

    def __init__(self, entries):
        self._data_model = GenericModel(entries)
        self._delegate = GenericDelegate()

    def build_widget(self, height=250):
        # Wrap in a VStack with margin/padding disabled, so we can control via the
        # headers/cells separately.
        if not height:
            height = max(55, min(len(self._data_model.get_item_children(None)) * 25, 250))

        with ui.VStack(style={"margin": 0, "padding": 0}):
            # Scrolling frame with the main tree view
            with ui.ScrollingFrame(height=height, style_type_name_override="TreeView"):

                tv = ui.TreeView(
                    self._data_model,
                    delegate=self._delegate,
                    root_visible=False,
                    header_visible=True,
                    columns_resizable=True,
                    resizeable_on_columns_resized=True,
                    style=TREE_VIEW_STYLE,
                )

                # By default, the middle (message) column will resize as the
                # window is resized. If columns are manually resized then they
                # get "locked" to the sizes you've chosen.
                tv.column_widths = [ui.Pixel(80), ui.Fraction(1), ui.Pixel(120)]

                # Minimum column widths so you can't fully hide the columns. UX
                # decision to make it less awkward for users. Note: a small min
                # is used, enough to not fully hide the columns. Using the original
                # widths as mins causes issues.
                tv.min_column_widths = [ui.Pixel(20), ui.Pixel(20), ui.Pixel(20)]
