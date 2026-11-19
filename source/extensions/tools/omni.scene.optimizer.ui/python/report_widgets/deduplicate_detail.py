# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
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
import omni.usd
from omni.kit.widget.searchfield import SearchField
from pxr import UsdGeom

from ..style import SPLITTER_STYLE, TREE_VIEW_STYLE
from ..utils import get_icon, show_tooltip

# Regexes
GROUP_PATTERN = re.compile(r"^Duplicates \((\d+)\):$")
FUZZY_PATTERN = re.compile(r"^Running deduplicate, deep=(\d), fuzzy=(\d)$")
IGNORE_PATTERN = re.compile(r"^Ignoring (namespace|attribute) (.+)$")
FOUND_PATTERN = re.compile(r"^Found \d+ sets? of equal meshes$")


class DuplicateGroupTreeItem(ui.AbstractItem):
    """Item in the duplicate group tree"""

    def __init__(self, name, is_path=False):

        super().__init__()

        self.models = [ui.SimpleStringModel(name)]
        self.children = []
        self.is_path = is_path
        self.name = name
        self.filtered = False

    def get_children(self):
        return self.children

    def __str__(self):  # pragma: no cover
        return f"({self.models[0].as_string})"


class DuplicateGroupTreeModel(ui.AbstractItemModel):
    def __init__(self):
        super().__init__()
        self._children = []

    def clear(self):
        """Clear any existing items"""
        self._children = list()
        self._item_changed(None)

    def add_group(self, name):
        """Add a top level group"""

        child = DuplicateGroupTreeItem(name, is_path=False)
        self._children.append(child)

        return child

    def add_path(self, group, path):
        """Add a child path to a group"""
        child = DuplicateGroupTreeItem(path, is_path=True)
        group.children.append(child)

    def refresh(self):
        """Notify of change e.g. after add_item"""
        self._item_changed(None)

    def get_item_children(self, item):
        if item is None:
            return [child for child in self._children if not child.filtered]

        if not hasattr(item, "get_children"):  # pragma: no cover
            return []

        return [i for i in item.get_children() if not i.filtered]

    def get_item_value_model_count(self, item):
        return 1

    def get_item_value_model(self, item, column_id):
        return item.models[column_id]

    def filter(self, terms):
        """Filter the children based on the specified terms

        Iterates through the tree items, marking them filtered
        if they should be skipped. Finally calls refresh() which
        will trigger an update and only the matching items will
        be returned.

        If called with no "terms" then everything is displayed
        (i.e. reset the filter).
        """

        for group_item in self._children:

            # Default to skipping
            group_item.filtered = True if terms else False

            for path_item in group_item.children:
                path_item.filtered = False
                if terms:
                    include = any(f in path_item.name for f in terms)
                    path_item.filtered = not include

                    # If a child matches, then don't filter out the group
                    if include:
                        group_item.filtered = False

        self.refresh()


class DuplicateGroupTreeDelegate(ui.AbstractItemDelegate):
    """Tree delegate to define headers etc"""

    def __init__(self):
        super().__init__()

    def build_branch(self, model, item, column_id, level, expanded):
        """Build branch to open or close subtree"""

        with ui.HStack(width=10 * (level + 1), height=0):
            ui.Spacer()
            if model.can_item_have_children(item):
                icon = "minus.svg" if expanded else "plus.svg"
                ui.Spacer(width=6)
                ui.Image(get_icon(icon), width=10, height=10, style_type_name_override="TreeView.Item")

    def build_widget(self, model, item, column_id, level, expanded):
        """Create a widget per column per item"""
        value_model = model.get_item_value_model(item, column_id)
        label = value_model.as_string

        style = {"margin": 4}
        ui.Label(label, name=label, style=style, style_type_name_override="TreeView.Item")


class AttributeTableItem(ui.AbstractItem):
    """Item for attributes table"""

    def __init__(self, name, value, color, tooltip):

        super().__init__()

        self.name = name
        self.value = value
        self.color = color
        self.tooltip = tooltip

        self.models = [ui.SimpleStringModel(name), ui.SimpleStringModel(value)]


class AttributeTableModel(ui.AbstractItemModel):
    """Data Model for attributes table"""

    def __init__(self):

        super().__init__()

        self._children = list()

    def add_item(self, name, value, color, tooltip):
        item = AttributeTableItem(name, value, color, tooltip)
        self._children.append(item)
        return item

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

    def refresh(self):
        """Notify of change e.g. after add_item"""
        self._item_changed(None)

    def get_item_value_model_count(self, item):
        """The number of columns"""
        return 2

    def get_item_value_model(self, item, column_id):
        """Return the value of an item for the specified column"""
        return item.models[column_id]

    def get_column_width(self, column_id):
        """Get column widths"""

        if column_id == 0:
            return ui.Percent(30)
        else:
            return ui.Percent(70)


class AttributeTableDelegate(ui.AbstractItemDelegate):
    """Item Delegate to control style a little better

    Allows us to define the headers.
    """

    def __init__(self):
        super().__init__()

    def build_header(self, column_id):
        """Build the widget for a column header"""

        style = {"margin": 4, "padding": 0}

        if column_id == 0:
            ui.Label(
                "Attribute",
                style=style,
            )
        else:
            ui.Label(
                "Value",
                style=style,
            )

    def build_widget(self, model, item, column_id, level, expanded):
        """Build the widget for a cell"""

        style = {"margin": 4}

        if item.color is not None:
            style["color"] = item.color

        value = model.get_item_value_model(item, column_id).as_string

        icon = "check_solid.svg"
        if value == "incompatible":
            icon = "error.svg"

        with ui.HStack(spacing=2, height=0):

            if column_id == 1:
                ui.Spacer(width=2)
                with ui.ZStack(width=20):
                    with ui.VStack(style={"margin": 0, "padding": 0}, height=ui.Percent(100)):
                        ui.Spacer()
                        ui.Image(get_icon(icon), width=16, height=16)
                        ui.Spacer()

            ui.Label(
                value,
                style_type_name_override="TreeView.Item.Title",
                style=style,
                tooltip_fn=partial(show_tooltip, f"{item.tooltip}"),
            )


class DeduplicateDetailPanel:
    """Main Deduplicate detail panel"""

    def __init__(self, entries):
        """Initialize the panel"""

        self._entries = entries
        self._filter = set()
        self._selected_paths = set()

        # Operation args
        # Values here will be extracted from the report and represent the
        # arguments that the operation ran with.
        self._consider_deep = False
        self._fuzzy = False
        self._ignore_attributes = list()
        self._ignore_namespaces = list()

        # Initial scan of the entries, we're looking for one that contains
        # some of the settings the operation ran with. Unfortunately there
        # are various combinations of attributes that are considered when
        # deduplicating, and we need to account for those.
        for entry in self._entries:
            match = re.match(FUZZY_PATTERN, entry.message)

            if match:
                self._consider_deep = match.group(1) == "1"
                self._fuzzy = match.group(2) == "1"
                continue

            match = re.match(IGNORE_PATTERN, entry.message)
            if match:
                ignore_type = match.group(1)
                if ignore_type == "namespace":
                    self._ignore_namespaces.append(match.group(2))
                elif ignore_type == "attribute":
                    self._ignore_attributes.append(match.group(2))
                continue

            # We don't want to process every line, after this line
            # there is no more data we need so we can break.
            match = re.match(FOUND_PATTERN, entry.message)
            if match:
                break

        # Config
        width = min(ui.Workspace.get_main_window_width(), 800)
        height = min(ui.Workspace.get_main_window_height(), 600)
        window_flags = ui.WINDOW_FLAGS_NO_SCROLLBAR
        window_flags |= ui.WINDOW_FLAGS_MODAL

        self._window = ui.Window(
            "Deduplicate Geometry Details",
            dockPreference=ui.DockPreference.DISABLED,
            width=width,
            height=height,
            flags=window_flags,
        )

        # Set up models/delegates
        self._tree_view = None
        self._data_model = DuplicateGroupTreeModel()
        self._delegate = DuplicateGroupTreeDelegate()

        # Set up attributes table
        self._attributes_table_view = None
        self._attributes_model = AttributeTableModel()
        self._attributes_delegate = AttributeTableDelegate()

        # Populate data model
        self._init_tree_data()

        # Build the interface
        self._build_widgets()

    def _filter_by_text(self, terms):
        """Filter the tree view"""
        self._filter = terms

        self._data_model.filter(terms)

        # This doesn't always help, tree view really doesn't like to
        # expand.
        self._tree_view.set_expanded(None, True, True)

        # The selection changes when filtering, but the callback isn't
        # triggered from the tree view. We can mimic that by just
        # calling the callback manually with the current selection
        # (which is up to date)
        self._path_tree_selection_changed(self._tree_view.selection)

    def _init_tree_data(self):
        """Initialize the main path tree"""

        remaining = 0
        group = None

        stage = omni.usd.get_context().get_stage()

        self._data_model.clear()

        # Keep track of all the paths we deduplicated, so we can use them to
        # find all the ones we didn't.
        paths = set()

        # The entries consist of a "header" that specifies how many duplicates
        # are in the group, followed by the individual paths.
        # Look for the header, then use a counter so we know when we've seen
        # all of the paths. This is fine when there's a subsequent group, it's
        # mostly a sanity-check so that if additional output is ever added after
        # the last path we don't include that.
        for entry in self._entries:

            match = re.match(GROUP_PATTERN, entry.message)

            if match:
                remaining = int(match.group(1))
                group = None

            elif remaining:
                remaining -= 1

                if not group:
                    group_num = len(self._data_model._children) + 1
                    group = self._data_model.add_group(f"Duplicate Group {group_num}")

                # Deduplicate reports the original prim that was deduplicated.
                # However, in reference/instanceable reference modes, the prim is
                # changed to an xform and the geometry is moved to be a child.
                # Here we will check for that and include the geometry, as it's
                # the geometry attributes that were used to figure out whether
                # things were duplicates.
                prim_path = entry.message
                prim = stage.GetPrimAtPath(prim_path)

                if not prim.IsA(UsdGeom.PointBased):
                    child = prim.GetChild("Geometry")
                    if child:
                        prim_path = str(child.GetPrimPath())

                self._data_model.add_path(group, prim_path)
                paths.add(prim_path)

        # We also want to find any other point-based prim that was not
        # a duplicate, so we can inspect them to see why not.
        ungrouped = None
        for prim in stage.Traverse():
            if prim.IsA(UsdGeom.PointBased):
                path = str(prim.GetPrimPath())
                if path not in paths:
                    if not ungrouped:
                        ungrouped = self._data_model.add_group("Ungrouped")
                    self._data_model.add_path(ungrouped, path)

        # Trigger update
        self._data_model.refresh()

    def _select_prims(self):
        """Select prims in the stage"""

        # Select in the stage
        selection = omni.usd.get_context().get_selection()
        selection.set_selected_prim_paths(list(self._selected_paths), True)

    def _build_widgets(self):
        """Build the main widgets"""

        with self._window.frame:
            with ui.VStack(style={"margin": 0, "padding": 0}, height=ui.Percent(100)):
                with ui.HStack():

                    # Filter field
                    self._search = SearchField(
                        on_search_fn=lambda filters: self._filter_by_text(filters), show_tokens=False, separator=" "
                    )

                    ui.Spacer(width=6)

                    # Selection button
                    ui.Button(
                        "Select In Stage",
                        width=40,
                        height=20,
                        clicked_fn=lambda: self._select_prims(),
                        style={"padding": 6},
                        tooltip_fn=partial(show_tooltip, "Select any prims selected here in the stage"),
                    )

                ui.Spacer(height=4)

                # The main trees/tables
                with ui.ZStack(height=0):
                    self._build_path_tree()

                    half_height = int(self._window.height * 0.5)

                    with ui.Placer(offset_y=half_height, draggable=True, drag_axis=ui.Axis.Y):
                        ui.Rectangle(height=4, style=SPLITTER_STYLE, style_type_name_override="Splitter")

                self._build_attribute_table()

    def _build_attribute_table(self):
        """Build the attribute comparison table"""

        col_widths = [ui.Fraction(30), ui.Fraction(70)]

        # Wrap in a VStack with margin/padding disabled, so we can control via the
        # headers/cells separately.
        with ui.VStack(style={"margin": 0, "padding": 0}, height=ui.Fraction(40)):
            # Scrolling frame
            with ui.ScrollingFrame(
                height=ui.Percent(100),
                style_type_name_override="TreeView",
                horizontal_scrollbar_policy=ui.ScrollBarPolicy.SCROLLBAR_ALWAYS_OFF,
                vertical_scrollbar_policy=ui.ScrollBarPolicy.SCROLLBAR_AS_NEEDED,
            ):
                self._attributes_table_view = ui.TreeView(
                    self._attributes_model,
                    delegate=self._attributes_delegate,
                    root_visible=False,
                    header_visible=True,
                    columns_resizable=True,
                    column_widths=col_widths,
                    style=TREE_VIEW_STYLE,
                )

    def _build_path_tree(self):
        """Build the main duplicate groups tree"""

        with ui.VStack(style={"margin": 0, "padding": 0}, height=ui.Fraction(60)):
            # Scrolling frame with the main tree view
            with ui.ScrollingFrame(
                height=ui.Percent(100),
                style_type_name_override="TreeView",
                horizontal_scrollbar_policy=ui.ScrollBarPolicy.SCROLLBAR_AS_NEEDED,
                vertical_scrollbar_policy=ui.ScrollBarPolicy.SCROLLBAR_AS_NEEDED,
            ):

                self._tree_view = ui.TreeView(
                    self._data_model,
                    delegate=self._delegate,
                    root_visible=False,
                    style=TREE_VIEW_STYLE,
                )

                self._tree_view.column_widths = [ui.Fraction(100)]

                # Recursively expand all children.
                self._tree_view.set_expanded(None, True, True)

        self._tree_view.set_selection_changed_fn(self._path_tree_selection_changed)

    def _get_attribute_data(self, prims, attribute):
        """Get various display values for an attribute based on prims"""

        value = None
        first = True
        all_match = True
        is_array = False

        for prim in prims:

            attr = prim.GetAttribute(attribute)

            # The set is authored attributes on any prim, meaning it is authored
            # on at least one prim, and not this one
            if not attr:
                return "incompatible", ui.color(255, 0, 0), "Not all prims have this attribute authored"

            # Record this is array-typed, for altering what we display later.
            if attr.GetTypeName().isArray:
                is_array = True

            val = attr.Get()

            # First time, just record it and continue
            if first:
                value = val
                first = False
                continue

            # Subsequently, compare to the first value
            # Note: it's possible a prim doesn't have an attribute, hence using
            #       the "first" bool rather than just slicing the list.
            if val != value:
                all_match = False
                break

        # Mismatch in values
        if not all_match:
            return "incompatible", ui.color(255, 0, 0), "Value differs between prims"

        # At this point the attribute matches on all prims. Sort out a useful
        # tooltip and display value
        tooltip = ""

        if is_array:
            value = "[...]"
            tooltip = "Value contains array-based data that is consistent between prims"
        else:
            value = str(value)
            tooltip = "Value matches all prims"

        return value, None, tooltip

    def _get_ignore_attributes(self):
        """Get the list of attributes that should be ignored"""

        # Default ignore list.
        # Intended to mimic what deduplicate does internally.
        ignore_attributes = ["extent", "points", "normals", "primvars:normals", "primvars:normals:indices"]

        # Fuzzy mode doesn't require these to match, it can find duplicates
        # where they differ
        if self._fuzzy:
            ignore_attributes.append("faceVertexCounts")
            ignore_attributes.append("faceVertexIndices")

        # If not considering deep transforms and not in fuzzy mode, then the
        # points have to be an exact match
        if not self._consider_deep and not self._fuzzy:
            ignore_attributes.remove("points")

        # Append any custom attributes that were ignored when the operation ran
        for attribute in self._ignore_attributes:
            ignore_attributes.append(attribute)

        return ignore_attributes

    def _path_tree_selection_changed(self, selection):
        """Handle selection of the duplicate groups tree changing"""

        # Make unique, and store on self.
        selected_paths = set([item.name for item in selection if item.is_path])
        self._selected_paths = selected_paths

        # Reset the attributes model and then rebuild based on the
        # new selection
        self._attributes_model.clear()

        if not selected_paths:
            return

        prims = list()
        attributes = set()

        # Get ignore attributes
        ignore_attributes = self._get_ignore_attributes()

        stage = omni.usd.get_context().get_stage()

        # First, get each prim, and build a set of all authored attribute names
        # on any of them.
        for path in selected_paths:

            prim = stage.GetPrimAtPath(path)
            if not prim:
                continue

            prims.append(prim)

            for attr in prim.GetAuthoredAttributes():

                attr_name = attr.GetName()

                # Check if the attribute has a namespace we are ignoring
                if any(attr_name.startswith(n) for n in self._ignore_namespaces):
                    continue

                if attr_name in ignore_attributes:
                    continue

                if attr_name.startswith("xformOp"):
                    continue

                attributes.add(attr_name)

        # Now that we have the attributes we can add items to show
        # whether they are compatible or not between the prims, which
        # should provide an indication of why things couldn't be
        # deduplicated together.
        attributes = sorted(attributes)

        for attr in attributes:
            value, color, tooltip = self._get_attribute_data(prims, attr)
            self._attributes_model.add_item(attr, value, color, tooltip)

        self._attributes_model.refresh()
