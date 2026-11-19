# SPDX-FileCopyrightText: Copyright (c) 2023-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.


import asyncio
import random
import re
import weakref
from collections import defaultdict
from dataclasses import dataclass
from functools import partial
from typing import Dict, List, Set

import carb
import omni.kit
import omni.ui as ui

from ..style import SPLITTER_STYLE, TREE_VIEW_STYLE
from ..utils import get_icon, show_tooltip

CATEGORY_BUCKET = "BUCKET"
CATEGORY_BUCKET_HASHDESC = "BUCKET.HASHDESC"
CATEGORY_MERGE = "MERGE"

BUCKET_PATTERN = re.compile(r"Hashed\s([\w/]+)\s=\s(\d+)")
HASHDESC_HASH_PATTERN = re.compile(r"Hash:\s(\d+)")
HASHDESC_ATTR_PATTERN = re.compile(r"(?:Authored\s)?Attr:\s(.*?)=(.*)")
HASHDESC_SCHEMA_PATTERN = re.compile(r"Schema:\s(.*)")
HASHDESC_MATERIAL_PATTERN = re.compile(r"Bound Material:\s(.*)")
HASHDESC_PARENT_PATH_PATTERN = re.compile(r"Parent Path:\s(.*)")
HASHDESC_SPATIAL_CLUSTER_PATTERN = re.compile(r"Spatial Cluster:\s(.*)")

MERGE_OUTPUT_MESH = re.compile(r"Output Mesh:\s(.*?)\scontains\s(\d+)")

TREE_COLUMN_NAME = 0
TREE_COLUMN_TYPE = 1
TREE_COLUMN_HASH = 2

ATTR_COLUMN_PATH = 0

TYPE_MESH = "Mesh"
TYPE_XFORM = "Xform"

PROP_BOUND_MATERIAL = "Bound Material"
PROP_PARENT_PATH = "Parent Path"

# Color table code
COLOR_TABLE: List[ui.color] = []


def _build_color_table():
    # Get a consistent random number stream
    color_rand = random.Random(20130915)

    for i in range(1024):
        # generate random values for RGB channels between 0.6 and 1.0
        r = int(color_rand.uniform(0.6, 1.0) * 255)
        g = int(color_rand.uniform(0.6, 1.0) * 255)
        b = int(color_rand.uniform(0.6, 1.0) * 255)

        # add color to list
        COLOR_TABLE.append(ui.color(r, g, b))


def _get_color(hash_value: int) -> ui.color:
    if not COLOR_TABLE:
        _build_color_table()

    # use modulo to get a valid index for colors list
    index = hash_value % len(COLOR_TABLE)
    return COLOR_TABLE[index]


@dataclass
class HashProperty:
    name: str
    value: str


class TreeItem(ui.AbstractItem):
    """Item for input or output tree"""

    def __init__(self, name, type, hash, path, is_unmerged=False):

        super().__init__()

        self.models = [ui.SimpleStringModel(name), ui.SimpleStringModel(type), ui.SimpleStringModel(hash)]
        self.children = []
        self.path = path
        self.is_unmerged = is_unmerged

    def get_children(self):
        return self.children

    def get_icon(self):
        if self.models[TREE_COLUMN_TYPE].as_string == TYPE_XFORM:
            icon = "xform.svg"
        elif self.is_unmerged:
            icon = "unmerged_prim.svg"
        else:
            icon = "prim.svg"

        return get_icon(icon)

    def __str__(self):  # pragma: no cover
        return f"({self.models[TREE_COLUMN_NAME].as_string},  {self.models[TREE_COLUMN_TYPE].as_string}, {self.models[TREE_COLUMN_HASH].as_string})"


class TreeModel(ui.AbstractItemModel):
    def __init__(self):
        super().__init__()
        self._children = []
        self._items_by_hash = defaultdict(list)
        self._path_to_child = dict()

    def clear(self):
        """Clear any existing items"""
        self._children = list()
        self._path_to_child = dict()
        self._item_changed(None)

    def add_item(self, path, bucket_hash, is_unmerged=False):
        """Populate the model, remember to call refresh() afterwards"""

        # Split the path by / add Xform and Mesh TreeItem children

        parts = path[1:].split("/")  # Strip off starting /
        parent = None  # Start at World root
        current_part = len(parts) - 1
        current_path = ""
        for name in parts:
            current_path += f"/{name}"
            if current_part == 0:
                # performance improvement - avoid check for existing children for meshes.
                child = TreeItem(name, TYPE_MESH, bucket_hash, current_path, is_unmerged)
                self._items_by_hash[bucket_hash].append(child)
                if parent is None:
                    self._children.append(child)
                else:
                    parent.children.append(child)
            else:
                # Check if we already added this xform
                if current_path in self._path_to_child:
                    parent = self._path_to_child[current_path]
                else:
                    # If not, create it now
                    bucket = ""  # empty bucket for xforms
                    child = TreeItem(
                        name, TYPE_XFORM, bucket, current_path, False
                    )  # ignore unmerged for xforms (for now)

                    if parent is None:
                        self._children.append(child)

                    # Cache the path to child item.
                    # Note: caching this is _orders of magnitude_ faster than querying the
                    # children directly (which does a linear search using the __eq__ function)
                    self._path_to_child[current_path] = child
                    parent = child

            # decrement part counter
            current_part -= 1

    def refresh(self):
        """Notify of change e.g. after add_item"""
        self._item_changed(None)

    def get_item_children(self, item):
        if item is None:
            return self._children

        if not hasattr(item, "get_children"):  # pragma: no cover
            return []

        return item.get_children()

    def get_item_value_model_count(self, item):
        return 3

    def get_item_value_model(self, item, column_id):
        return item.models[column_id]

    def find_items_by_hash(self, hash_value):
        if hash_value in self._items_by_hash:
            return self._items_by_hash[hash_value]

        return []


class TreeDelegate(ui.AbstractItemDelegate):
    """Tree delegate to define headers etc"""

    def __init__(self):
        super().__init__()

    def build_branch(self, model, item, column_id, level, expanded):
        """Build branch to open or close subtree"""
        if column_id == 0:
            with ui.HStack(width=20 * (level + 1), height=0):
                ui.Spacer()
                if model.can_item_have_children(item):
                    icon = get_icon("minus.svg") if expanded else get_icon("plus.svg")
                    ui.Image(icon, width=10, height=10, style_type_name_override="TreeView.Item")
                    ui.Spacer(width=5)

    def build_widget(self, model, item, column_id, level, expanded):
        """Create a widget per column per item"""
        value_model = model.get_item_value_model(item, column_id)
        label = value_model.as_string

        hash_model = model.get_item_value_model(item, TREE_COLUMN_HASH)

        style = {"margin": 6}

        if hash_model.as_string:
            bucket = int(hash_model.as_string)
            style["color"] = _get_color(bucket)

        if column_id == 0:
            with ui.HStack(spacing=4, height=20):
                ui.Image(item.get_icon(), width=20, height=20, style_type_name_override="TreeView.Image")
                ui.Label(label, name=label, style=style, style_type_name_override="TreeView.Item")
        else:
            ui.Label(label, name=label, style=style, style_type_name_override="TreeView.Item")

    def build_header(self, column_id):
        """Build the widget for a column header"""

        style = {"margin": 6, "padding": 0}

        if column_id == TREE_COLUMN_NAME:
            ui.Label(
                "Name",
                tooltip_fn=partial(show_tooltip, "Name of the Prim"),
                style=style,
            )
        elif column_id == TREE_COLUMN_TYPE:
            ui.Label(
                "Type",
                tooltip_fn=partial(show_tooltip, "Type of the Prim"),
                style=style,
            )
        elif column_id == TREE_COLUMN_HASH:
            ui.Label(
                "Hash",
                tooltip_fn=partial(show_tooltip, "Merge bucket hash the Prim was placed in."),
                style=style,
            )


class AttributeTableItem(ui.AbstractItem):
    """Item for attributes table"""

    def __init__(self, prim_name, properties, all_properties, color: ui.color):

        super().__init__()

        self.color = color
        self.models = [ui.SimpleStringModel(prim_name)]
        for prop_name in all_properties:
            prop = next((p for p in properties if p.name == prop_name), "Undefined")
            if prop == "Undefined":
                self.models.append(ui.SimpleStringModel("Undefined"))
            else:
                self.models.append(ui.SimpleStringModel(prop.value))


class AttributeTableModel(ui.AbstractItemModel):
    """Data Model for attributes table"""

    def __init__(self, all_properties, mesh_hashes, hash_descriptions):

        super().__init__()

        self._children = list()
        self._all_properties = all_properties
        self.add_items(mesh_hashes, hash_descriptions)
        self._column_differs = {}  # cache which columns differ

    def add_items(self, mesh_hashes, hash_descriptions):
        """Populate the model"""

        for name, bucket in sorted(mesh_hashes.items()):
            self._children.append(
                AttributeTableItem(name, hash_descriptions[bucket], self._all_properties, _get_color(int(bucket)))
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
        return len(self._all_properties) + 1  # name + all the properties

    def get_item_value_model(self, item, column_id):
        """Return the value of an item for the specified column"""
        return item.models[column_id]

    def column_values_differ(self, column_id) -> bool:
        if not self._children:
            return False

        if column_id not in self._column_differs.keys():
            result = False  # assume all the same unless proven otherwise.
            prev_value = self.get_item_value_model(self._children[0], column_id).as_string
            for item in self._children[1:]:
                value = self.get_item_value_model(item, column_id).as_string
                if value != prev_value:
                    result = True
                    break

                prev_value = value
            # cache result for next time
            self._column_differs[column_id] = result

        return self._column_differs[column_id]

    def get_column_width(self, column_id):
        """Approximate column width by returning the larger of the heading or first value (if any)"""

        min_width = 10
        max_width = 25

        # Fix the path width (will be elided if very long)
        if column_id == ATTR_COLUMN_PATH:
            return 25

        heading_width = len(self._all_properties[column_id - 1])
        if not self._children:
            value_width = 0
        else:
            first_item = self._children[0]
            value_width = len(self.get_item_value_model(first_item, column_id).as_string)

        larger_width = max(heading_width, value_width)
        result = max(min_width, min(larger_width, max_width))

        return result


class AttributeTableFilterModel(ui.AbstractItemModel):
    """
    This model that takes the source model and filters out the items that are
    not selected in the input tree.
    """

    def __init__(self, source: AttributeTableModel, **kwargs):
        super().__init__()

        self.__source: ActivityModel = source
        self.__subscription = self.__source.subscribe_item_changed_fn(
            partial(AttributeTableFilterModel._source_changed, weakref.proxy(self))
        )

        self._selected_prims = []

    def _source_changed(self, model, item):
        self._item_changed(item)

    def set_selected_prims(self, selected_prims: Set[str]):
        self._selected_prims = selected_prims

        # notify change
        self._item_changed(None)

    def destroy(self):
        self.__source = None
        self.__subscription = None

    def get_item_children(self, item):
        """Returns all the children when the widget asks it."""
        if self.__source is None:
            return []

        children = self.__source.get_item_children(item)

        # If no selection then show all of them.
        if not self._selected_prims:
            return children

        # Return only children who have been selected.
        return list(filter(lambda p: p.models[ATTR_COLUMN_PATH].as_string in self._selected_prims, children))

    def get_item_value_model_count(self, item):
        """The number of columns"""
        return self.__source.get_item_value_model_count(item)

    def get_item_value_model(self, item, column_id):
        """Return value model."""
        return self.__source.get_item_value_model(item, column_id)

    def column_values_differ(self, column_id):
        return self.__source.column_values_differ(column_id)


class AttributeTableDelegate(ui.AbstractItemDelegate):
    """Item Delegate to control style a little better

    Allows us to define the headers.
    """

    def __init__(self, all_properties):

        super().__init__()
        self._all_properties = all_properties

    def build_header(self, column_id):
        """Build the widget for a column header"""

        style = {"margin": 6, "padding": 0}

        if column_id == ATTR_COLUMN_PATH:
            ui.Label(
                "Path",
                tooltip_fn=partial(show_tooltip, "Prim Path"),
                style=style,
            )
        else:
            name = self._all_properties[column_id - 1]
            ui.Label(
                name,
                tooltip_fn=partial(show_tooltip, f"{name}"),
                style=style,
            )

    def build_widget(self, model, item, column_id, level, expanded):
        """Build the widget for a cell"""

        style = {"margin": 6}
        if column_id == ATTR_COLUMN_PATH:
            style["color"] = item.color

        value = model.get_item_value_model(item, column_id).as_string
        tooltip = value
        if not value:
            value = "-"
            tooltip = "Undefined"
            style["color"] = ui.color(90, 90, 90)  # dark grey

        if column_id != ATTR_COLUMN_PATH and model.column_values_differ(column_id):
            style["color"] = ui.color(255, 140, 0)  # dark orange

        ui.Label(
            value,
            style_type_name_override="TreeView.Item.Title",
            style=style,
            tooltip_fn=partial(show_tooltip, f"{tooltip}"),
            elided_text=len(value) > 15,
        )


class MergeResultsPanel:
    def __init__(self, entries):
        width = min(ui.Workspace.get_main_window_width(), 1800)
        height = min(ui.Workspace.get_main_window_height(), 800)
        window_flags = ui.WINDOW_FLAGS_NO_SCROLLBAR
        window_flags |= ui.WINDOW_FLAGS_MODAL
        self._window = ui.Window(
            "Merge Results",
            dockPreference=ui.DockPreference.DISABLED,
            width=width,
            height=height,
            flags=window_flags,
        )

        self._mesh_hashes = {}  # hash by input mesh
        self._hash_descriptions = {}  # hash property list by hash
        self._all_properties = []  # unique and sorted set of property names
        self._output_to_input_map = {}  # list of input meshes by output mesh
        self._merged_hash_set = set()  # which buckets were merged.

        # parse the logs and populate the data structures
        self._parse_logs(entries)

        # init input and output trees and their models
        self._input_tree_view = None
        self._input_data_model = TreeModel()
        self._input_delegate = TreeDelegate()

        self._output_tree_view = None
        self._output_data_model = TreeModel()
        self._output_delegate = TreeDelegate()

        self._init_tree_models()

        # init attribute table and model
        self._attributes_table_view = None

        self._attributes_data_model = AttributeTableModel(
            self._all_properties, self._mesh_hashes, self._hash_descriptions
        )
        self._attributes_filter_model = AttributeTableFilterModel(self._attributes_data_model)

        self._attributes_delegate = AttributeTableDelegate(self._all_properties)

        # Finally, build the widgets
        self._build_widgets()

    def _init_tree_models(self):
        # init input mesh model
        for mesh, bucket in sorted(self._mesh_hashes.items()):
            is_unmerged = bucket not in self._merged_hash_set
            self._input_data_model.add_item(mesh, bucket, is_unmerged)
        self._input_data_model.refresh()

        # init output mesh model
        for mesh in sorted(self._output_to_input_map.keys()):
            # Get bucket hash of first input (any would do)
            first_input = self._output_to_input_map[mesh][0]
            self._output_data_model.add_item(mesh, self._mesh_hashes[first_input])
        self._output_data_model.refresh()

    def _parse_logs(self, entries):
        current_output_mesh = None
        remaining_input_meshes = 0
        input_meshes = []
        property_set = set()

        for entry in entries:

            if entry.category == CATEGORY_BUCKET:
                # Use re.match() to search for the pattern in the string
                match = re.match(BUCKET_PATTERN, entry.message)

                # If the pattern was found, extract the matching groups
                if match:
                    mesh_path = match.group(1)
                    hash_value = match.group(2)
                    self._mesh_hashes[mesh_path] = hash_value
                elif entry.message.startswith("Calculated"):
                    continue
                else:
                    carb.log_warn(f"MergeResultsPanel: Couldn't parse {CATEGORY_BUCKET} entry: '{entry.message}'")
                    continue

            elif entry.category == CATEGORY_BUCKET_HASHDESC:
                lines = entry.message.splitlines()

                hash_value = None
                properties = []

                # parse hash from first line
                hash_match = re.match(HASHDESC_HASH_PATTERN, lines[0])
                if hash_match:
                    hash_value = hash_match.group(1)
                else:
                    carb.log_warn(f"Could not parse hash value from {CATEGORY_BUCKET_HASHDESC} entry: '{lines[0]}'")
                    continue

                for line in lines[1:]:
                    if line.startswith("Attr:") or line.startswith("Authored Attr:"):
                        attr_match = re.match(HASHDESC_ATTR_PATTERN, line)
                        if attr_match:
                            key = attr_match.group(1)
                            val = attr_match.group(2)
                            properties.append(HashProperty(key, val))
                        else:
                            carb.log_warn(f"Couldn't parse HashDesc Attribute entry: '{line}'")
                            continue

                    elif line.startswith("Schema:"):
                        schema_match = re.match(HASHDESC_SCHEMA_PATTERN, line)
                        if schema_match:
                            schema = schema_match.group(1)
                            properties.append(HashProperty("Schema", schema))
                        else:
                            properties.append(HashProperty("Schema", ""))

                    elif line.startswith("Bound Material:"):
                        mat_match = re.match(HASHDESC_MATERIAL_PATTERN, line)
                        if mat_match:
                            material = mat_match.group(1)
                            properties.append(HashProperty(PROP_BOUND_MATERIAL, material))
                        else:
                            properties.append(HashProperty(PROP_BOUND_MATERIAL, ""))

                    elif line.startswith("Spatial Cluster:"):
                        path_match = re.match(HASHDESC_SPATIAL_CLUSTER_PATTERN, line)
                        if path_match:
                            parent_path = path_match.group(1)
                            properties.append(HashProperty("Spatial Cluster", parent_path))
                        else:
                            properties.append(HashProperty("Spatial Cluster", ""))

                    elif line.startswith("Parent Path:"):
                        path_match = re.match(HASHDESC_PARENT_PATH_PATTERN, line)
                        if path_match:
                            parent_path = path_match.group(1)
                            properties.append(HashProperty(PROP_PARENT_PATH, parent_path))
                        else:
                            carb.log_warn(f"MergeResultsPanel: Couldn't parse HashDesc Parent Path entry: '{line}'")
                    elif line == "":
                        continue
                    else:
                        carb.log_warn(f"MergeResultsPanel: Couldn't parse {CATEGORY_BUCKET_HASHDESC} entry: '{line}'")

                    # populate the hash descriptions map
                    self._hash_descriptions[hash_value] = properties

                    # capture unique set of property names
                    for prop in properties:
                        if prop.name != PROP_BOUND_MATERIAL and prop.name != PROP_PARENT_PATH:
                            property_set.add(prop.name)

            elif entry.category == CATEGORY_MERGE:
                # The merge logs first report the Output Mesh and how many input meshes it contains:
                # Example:  INFO, MERGE, Output Mesh: /merged contains 2
                out_match = re.match(MERGE_OUTPUT_MESH, entry.message)
                if out_match and out_match.group(1):
                    current_output_mesh = out_match.group(1)
                    remaining_input_meshes = int(out_match.group(2))
                    input_meshes = []

                elif current_output_mesh and remaining_input_meshes > 0:
                    # Following messages are just paths to the input meshes
                    # Example: INFO, MERGE, /World/Cube_02
                    input_meshes.append(entry.message)
                    remaining_input_meshes -= 1

                # Now we've grabbed all the input meshes we'll add them to the map.
                if current_output_mesh and remaining_input_meshes == 0:
                    self._output_to_input_map[current_output_mesh] = input_meshes
                    # Store which buckets were actually merged (using first mesh only)
                    self._merged_hash_set.add(self._mesh_hashes[input_meshes[0]])
                    current_output_mesh = None

        # Finally sort the unique properties in to a list, ensuring we add Bound Material and Parent Path at the end.
        self._all_properties = sorted(property_set)
        self._all_properties.append(PROP_BOUND_MATERIAL)
        self._all_properties.append(PROP_PARENT_PATH)

    def _build_widgets(self):
        half_height = int(self._window.height * 0.5)

        with self._window.frame:
            with ui.VStack(style={"margin": 0, "padding": 0}, height=ui.Percent(100)):
                with ui.ZStack(height=0):
                    self._build_tree_views()

                    with ui.Placer(offset_y=half_height, draggable=True, drag_axis=ui.Axis.Y):
                        ui.Rectangle(height=4, style=SPLITTER_STYLE, style_type_name_override="Splitter")

                self._build_attributes_table()

    def _build_tree_views(self):
        half_width = int(self._window.width * 0.5)

        with ui.HStack(style={"margin": 0, "padding": 0}):
            with ui.ZStack(width=0):
                self._build_input_tree()

                with ui.Placer(offset_x=half_width, draggable=True, drag_axis=ui.Axis.X):
                    ui.Rectangle(width=4, style=SPLITTER_STYLE, style_type_name_override="Splitter")

            self._build_output_tree()

        # setup sync selection between the two trees after both have been constructed.
        self._input_tree_view.set_mouse_released_fn(
            lambda x, y, b, c, cv=self._input_tree_view, ov=self._output_tree_view: self.on_tree_clicked(cv, ov)
        )
        self._output_tree_view.set_mouse_released_fn(
            lambda x, y, b, c, cv=self._output_tree_view, ov=self._input_tree_view: self.on_tree_clicked(cv, ov)
        )

        # setup selection changed callback for input tree (only) to filter the attribute table.
        self._input_tree_view.set_selection_changed_fn(self._on_input_tree_selection_changed)

    def _build_input_tree(self):
        # TODO: add filtering
        # Wrap in a VStack with margin/padding disabled, so we can control via the
        # headers/cells separately.
        with ui.VStack(style={"margin": 0, "padding": 0}):
            # Scrolling frame with the main tree view
            with ui.ScrollingFrame(
                height=ui.Percent(100),
                style_type_name_override="TreeView",
                horizontal_scrollbar_policy=ui.ScrollBarPolicy.SCROLLBAR_ALWAYS_OFF,
                vertical_scrollbar_policy=ui.ScrollBarPolicy.SCROLLBAR_AS_NEEDED,
            ):
                self._input_tree_view = ui.TreeView(
                    self._input_data_model,
                    delegate=self._input_delegate,
                    root_visible=False,
                    header_visible=True,
                    columns_resizable=True,
                    style=TREE_VIEW_STYLE,
                )

                self._input_tree_view.column_widths = [ui.Fraction(60), ui.Fraction(15), ui.Fraction(25)]

                # Recursively expand all children.
                self._input_tree_view.set_expanded(None, True, True)
            ui.Spacer(width=2)

    def _build_output_tree(self):
        # TODO: add filtering
        # Wrap in a VStack with margin/padding disabled, so we can control via the
        # headers/cells separately.
        with ui.VStack(style={"margin": 0, "padding": 0}):
            # Scrolling frame with the main tree view
            with ui.ScrollingFrame(
                height=ui.Percent(100),
                style_type_name_override="TreeView",
                horizontal_scrollbar_policy=ui.ScrollBarPolicy.SCROLLBAR_ALWAYS_OFF,
                vertical_scrollbar_policy=ui.ScrollBarPolicy.SCROLLBAR_AS_NEEDED,
            ):
                self._output_tree_view = ui.TreeView(
                    self._output_data_model,
                    delegate=self._output_delegate,
                    root_visible=False,
                    header_visible=True,
                    columns_resizable=True,
                    style=TREE_VIEW_STYLE,
                )

                self._output_tree_view.column_widths = [ui.Fraction(60), ui.Fraction(15), ui.Fraction(25)]

                # Recursively expand all children.
                self._output_tree_view.set_expanded(None, True, True)
            ui.Spacer(width=2)

    def _build_attributes_table(self):

        # Setup column widths
        col_widths = []  # Name
        for i in range(self._attributes_data_model.get_item_value_model_count(None)):
            cw = self._attributes_data_model.get_column_width(i)
            col_widths.append(ui.Fraction(cw))

        # Wrap in a VStack with margin/padding disabled, so we can control via the
        # headers/cells separately.
        with ui.VStack(style={"margin": 0, "padding": 0}):
            # Scrolling frame with the main tree view
            with ui.ScrollingFrame(
                height=ui.Percent(100),
                style_type_name_override="TreeView",
                horizontal_scrollbar_policy=ui.ScrollBarPolicy.SCROLLBAR_ALWAYS_OFF,
                vertical_scrollbar_policy=ui.ScrollBarPolicy.SCROLLBAR_AS_NEEDED,
            ):
                self._attributes_table_view = ui.TreeView(
                    self._attributes_filter_model,
                    delegate=self._attributes_delegate,
                    root_visible=False,
                    header_visible=True,
                    columns_resizable=True,
                    column_widths=col_widths,
                    style=TREE_VIEW_STYLE,
                )

    def on_tree_clicked(self, clicked_view, other_view):
        async def get_selection():
            await omni.kit.app.get_app().next_update_async()
            if clicked_view.selection:

                other_items = []
                for item in clicked_view.selection:
                    hash_model = clicked_view.model.get_item_value_model(item, TREE_COLUMN_HASH)
                    bucket = hash_model.as_string
                    # lookup bucket hash in output
                    other_items += other_view.model.find_items_by_hash(bucket)

                other_view.selection = list(other_items)

        asyncio.ensure_future(get_selection())

    def _on_input_tree_selection_changed(self, selection):
        # Build a list of the names
        selected_paths = set([item.path for item in selection])
        # Set the selection filter.
        self._attributes_filter_model.set_selected_prims(selected_paths)
