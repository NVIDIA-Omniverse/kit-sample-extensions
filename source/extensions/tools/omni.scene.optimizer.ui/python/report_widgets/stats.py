# SPDX-FileCopyrightText: Copyright (c) 2023-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.


import json
from functools import partial

import omni.ui as ui

from ..style import *
from ..utils import show_tooltip


class StatsItem(ui.AbstractItem):
    """Simple table entry item for a statistics row"""

    def __init__(self, primType, count, inactive, invisible):

        super().__init__()

        self.models = [
            ui.SimpleStringModel(primType),
            ui.SimpleStringModel(count),
            ui.SimpleStringModel(inactive),
            ui.SimpleStringModel(invisible),
        ]


class StatsModel(ui.AbstractItemModel):
    """Data Model for the statistics table"""

    def __init__(self, entries):

        super().__init__()

        self._children = list()
        self.add_items(entries)

    def add_items(self, entries):
        """Populate the model"""

        for entry in entries:
            line = entry.message
            if line.startswith("PAYLOAD:"):
                # trim the "payload: " prefix
                payload = line[8:]

                analysis = json.loads(payload)
                stats = analysis["analysis"]

                # Add each prim type
                for primType in stats["types"]:
                    info = stats["types"][primType]

                    name = primType

                    if info["extra"]:
                        name += " (" + info["extra"] + ")"

                    invis = str(info["invisible"])

                    # Not imageable
                    if primType in ["Material", "Shader"]:
                        invis = "--"

                    self._children.append(StatsItem(name, str(info["count"]), str(info["inactive"]), invis))

                # Add totals
                self._children.append(
                    StatsItem("Total", str(stats["prims"]), str(stats["inactive"]), str(stats["invisible"]))
                )

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
        return 4

    def get_item_value_model(self, item, column_id):
        """Return the value of an item for the specified column"""
        return item.models[column_id]


class StatsDelegate(ui.AbstractItemDelegate):
    """Item Delegate to control style a little better

    Allows us to define the headers.
    """

    def build_header(self, column_id):
        """Build the widget for a column header"""

        margin = 6
        padding = 0

        if column_id == 0:
            ui.Label(
                "Prim Type",
                tooltip_fn=partial(show_tooltip, "The type of prim"),
                style={"margin": margin, "padding": padding},
            )
        elif column_id == 1:
            ui.Label(
                "Count",
                tooltip_fn=partial(show_tooltip, "The number of prims found in the stage"),
                style={"margin": margin, "padding": padding},
            )
        elif column_id == 2:
            ui.Label(
                "Inactive",
                tooltip_fn=partial(show_tooltip, "The number of this type of prim that are inactive"),
                style={"margin": margin, "padding": padding},
            )
        elif column_id == 3:
            ui.Label(
                "Invisible",
                tooltip_fn=partial(show_tooltip, "The number of this type of prim that are invisible"),
                style={"margin": margin, "padding": padding},
            )

    def build_widget(self, model, item, column_id, level, expanded):
        """Build the widget for a cell"""

        ui.Label(
            model.get_item_value_model(item, column_id).as_string,
            style_type_name_override="TreeView.Item.Title",
            style={"margin": 6},
        )


class StatsWidget:
    """Custom widget to display Stats information in the Scene Optimizer
    report.
    """

    def __init__(self, entries):
        self._data_model = StatsModel(entries)
        self._delegate = StatsDelegate()

    def build_widget(self):
        # Wrap in a VStack with margin/padding disabled, so we can control via the
        # headers/cells separately.
        with ui.VStack(style={"margin": 0, "padding": 0}):
            # Scrolling frame with the main tree view
            with ui.ScrollingFrame(height=250, style_type_name_override="TreeView"):
                tv = ui.TreeView(
                    self._data_model,
                    delegate=self._delegate,
                    root_visible=False,
                    header_visible=True,
                    style=TREE_VIEW_STYLE,
                )
