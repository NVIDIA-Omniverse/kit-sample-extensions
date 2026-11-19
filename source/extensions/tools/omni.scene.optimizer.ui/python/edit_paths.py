# SPDX-FileCopyrightText: Copyright (c) 2022-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.


from functools import partial

import omni.ui as ui
import omni.usd
from pxr import Sdf

from .style import *
from .utils import ImageAndTextButton, get_icon, show_tooltip


class PathItem(ui.AbstractItem):
    """Single item representing a path and prim type"""

    def __init__(self, path, _type):

        super().__init__()

        self.path_model = ui.SimpleStringModel(path)
        self.type_model = ui.SimpleStringModel(_type)

    def __repr__(self):  # pragma: no cover
        """Debug representation"""
        return f'"{self.path_model.as_string} {self.type_model.as_string}"'


class PathModel(ui.AbstractItemModel):
    """Data Model for the prim paths tree view"""

    def __init__(self, stage, paths):

        super().__init__()

        self._stage = stage
        self._children = list()
        self.add_items(paths)

    def add_items(self, paths):
        """Add the specified prim paths to the model, if they don't already exist"""

        # Grab a set of the existing paths for quick comparison
        existing = set([child.path_model.as_string for child in self._children])

        # Add each path if it's valid/not already included
        for path in paths:

            if not path:
                continue

            if path in existing:
                continue

            # Resolve type name
            _type = ""
            if Sdf.Path.IsValidPathString(path):
                prim = self._stage.GetPrimAtPath(path)
                if prim:
                    _type = prim.GetTypeName()
            elif "+" in path:
                _type = "Expression"

            self._children.append(PathItem(path, _type))

        # Notify of change
        self._item_changed(None)

    def clear(self):
        """Clear any existing items"""
        self._children = list()
        self._item_changed(None)

    def remove_items(self, items):
        """Remove the specified items from the model"""

        for item in items:
            try:
                self._children.remove(item)
            except:
                pass

        self._item_changed(None)

    def get_item_children(self, item):
        """Return the children of an item."""

        # This is a table really, not a tree, so if we are not the root item
        # we have no children to return.
        if item is not None:
            return []

        return self._children

    def get_item_value_model_count(self, item):
        """The number of columns"""
        return 3

    def get_item_value_model(self, item, column_id):
        """Return the value of an item for the specified column"""
        return item.type_model if column_id == 1 else item.path_model


class PathDelegate(ui.AbstractItemDelegate):
    """Item Delegate to control style a little better

    Allows us to define the headers.
    """

    def __init__(self, remove_fn):

        super().__init__()
        self._remove_fn = remove_fn

    def build_header(self, column_id):
        """Build the widget for a column header"""

        if column_id == 0:
            ui.Label(
                "Path/Expression",
                tooltip_fn=partial(show_tooltip, "A prim path or regular expression"),
                style={"margin": 6},
            )
        elif column_id == 1:
            ui.Label(
                "Type",
                tooltip_fn=partial(show_tooltip, "If found, the type of the prim"),
                style={"margin": 6},
            )

    def remove_item(self, model, path_item):
        """Remove a single item"""
        self._remove_fn(path_item)

    def build_widget(self, model, item, column_id, level, expanded):
        """Build the widget for a cell"""

        if column_id == 2:
            ui.Button(
                " ",
                width=20,
                image_url=get_icon("remove_item.svg"),
                image_width=20,
                image_height=20,
                clicked_fn=partial(self.remove_item, model, item),
                style={"background_color": 0x0},
            )
        else:
            ui.Label(
                model.get_item_value_model(item, column_id).as_string, style_type_name_override="TreeView.Item.Title"
            )


class EditPathsPanel:
    """Edit Prim Paths UI Panel"""

    def __init__(self, paths, accept_fn, stage=None):

        if stage is None:
            stage = omni.usd.get_context().get_stage()

        self.window = ui.Window("Edit Prim Paths", width=500, height=400)

        self._data_model = PathModel(stage, paths)
        self._delegate = PathDelegate(remove_fn=self._remove_path_item_fn)
        self._selection = list()
        self._accept_fn = accept_fn

        self.update_ui(paths)

    def add_paths(self, paths):
        """Add paths to the list"""
        self._data_model.add_items(paths)

    def remove_paths(self, paths):
        """Remove paths from the list"""
        # Get the items in the data model that have the same value as the supplied paths
        items = []
        for item in self._data_model._children:
            if item.path_model.as_string in paths:
                items.append(item)
        # Remove the items from the model
        self._data_model.remove_items(items)

    def clear_paths(self):
        """Remove all paths from the list"""
        self._data_model.clear()
        self._selection = list()

    def set_visibility_changed_fn(self, fn):
        """Set callback function for the windows visibility changing"""
        self.window.set_visibility_changed_fn(fn)

    def _remove_all_paths_fn(self, x, y, i, b):
        """Remove all paths from the tree"""
        self.clear_paths()

    def _remove_path_item_fn(self, path_item):
        """Remove a path item from the list.

        If multiple items are selected, then all will be removed.
        """

        items = [path_item]

        # If there is more than one item selected then we want to delete all the
        # items. Except for the case the user clicked delete on an item outside
        # of the selection, in which case we'll just delete that item instead.
        if len(self._selection) > 1 and path_item in self._selection:
            items = self._selection

        self._data_model.remove_items(items)

    def add_paths_from_selection(self, x, y, i, b):
        """Add any selected paths in the stage to the model"""

        selected_paths = omni.usd.get_context().get_selection().get_selected_prim_paths()
        if not selected_paths:
            return

        self.add_paths(selected_paths)

    def select_paths(self, x, y, i, b):
        """Get the current selection and add to the stage selection"""

        # Early out
        if len(self._selection) == 0:
            return

        # Get the existing selection. Add any selected paths in the tree view to
        # the main stage selection.
        selection = omni.usd.get_context().get_selection()

        paths = selection.get_selected_prim_paths()
        for path_item in self._selection:
            prim_path = path_item.path_model.as_string
            if Sdf.Path.IsValidPathString(prim_path) and prim_path not in paths:
                paths.append(prim_path)

        # Select in the stage
        selection.set_selected_prim_paths(paths, True)

    def selection_changed(self, selection):
        """Record the current selection, so we can use it if necessary"""
        self._selection = selection

    def accept(self):
        """Called when the user clicks Ok to accept the changes"""
        paths = list()
        for path_item in self._data_model._children:
            paths.append(path_item.path_model.as_string)

        # Notify
        self._accept_fn(paths)

        # Close window
        self.window.visible = False

    def reject(self):
        """Called when the user clicks Cancel to ignore the changes"""
        self.window.visible = False

    def drop_accept(self, data):
        """Returns whether or not to accept a potential drag/drop"""
        if Sdf.Path.IsValidPathString(data):
            return True

        return False

    def drop(self, event):
        """Accept a drop"""

        # Check the omni selection. If the selection contains the path string
        # provided as mime data, then we assume that the user is dragging one
        # or more paths - we only get passed the first, so instead, add the
        # whole selection.
        selected_paths = omni.usd.get_context().get_selection().get_selected_prim_paths()
        if event.mime_data in selected_paths:
            self.add_paths(selected_paths)
        else:
            # If not, then assume it's an individual path.
            self.add_paths([event.mime_data])

    def update_ui(self, paths):
        """Rebuild the main UI"""

        image_width = 20

        with self.window.frame:

            with ui.VStack(style=HEADER_STYLE):

                # Header Buttons
                with ui.HStack(height=30, style={"padding": 4, "margin": 2}):

                    ImageAndTextButton(
                        "Add",
                        image_path=get_icon("add.svg"),
                        width=100,
                        height=30,
                        image_width=14,
                        image_height=14,
                        mouse_pressed_fn=self.add_paths_from_selection,
                        tooltip="Add any prims that are selected in the stage",
                    )

                    ImageAndTextButton(
                        "Remove All",
                        image_path=get_icon("remove.svg"),
                        width=100,
                        height=30,
                        image_width=image_width,
                        image_height=30,
                        mouse_pressed_fn=self._remove_all_paths_fn,
                        tooltip="Remove everything from the list",
                    )

                    ui.Spacer()

                    ImageAndTextButton(
                        "Show In Stage",
                        image_path=get_icon("share.svg"),
                        width=100,
                        height=30,
                        image_width=image_width,
                        image_height=30,
                        mouse_pressed_fn=self.select_paths,
                        tooltip="Add any of the selected items in this list to the stage selection",
                    )

                # Scrolling frame with the main tree view
                with ui.ScrollingFrame(style_type_name_override="TreeView"):

                    tv = ui.TreeView(
                        self._data_model,
                        delegate=self._delegate,
                        root_visible=False,
                        header_visible=True,
                        selection_changed_fn=self.selection_changed,
                        style=TREE_VIEW_STYLE,
                    )

                    tv.column_widths = [ui.Fraction(75), ui.Fraction(20), ui.Fraction(5)]

                    # Enable drag/drop of prim paths from the outliner
                    tv.set_accept_drop_fn(self.drop_accept)
                    tv.set_drop_fn(self.drop)

                with ui.HStack(height=30):

                    ui.Spacer()

                    ui.Button(
                        "Ok",
                        width=100,
                        clicked_fn=self.accept,
                        tooltip_fn=partial(show_tooltip, "Accept the changes and close the window"),
                    )

                    ui.Button(
                        "Cancel",
                        width=100,
                        clicked_fn=self.reject,
                        tooltip_fn=partial(show_tooltip, "Discard changes and close the window"),
                    )
