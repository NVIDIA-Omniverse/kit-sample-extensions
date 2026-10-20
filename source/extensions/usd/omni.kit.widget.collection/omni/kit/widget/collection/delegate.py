# Copyright (c) 2018-2020, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

import asyncio
import math
from pathlib import Path

import omni.ui as ui

from .context_menu import ContextMenu
from .icons import CollectionIcons

CURRENT_PATH = Path(__file__).parent
ICON_PATH = CURRENT_PATH.parent.parent.parent.parent.joinpath("icons")


class AwaitWithFrame:
    """
    A future-like object that runs the given future and makes sure it's
    always in the given frame's scope. It allows creating widgets
    asynchronously.
    """

    def __init__(self, frame: ui.Frame, future: asyncio.Future):
        self._frame = frame
        self._future = future

    def __await__(self):
        # create an iterator object from that iterable
        iter_obj = iter(self._future.__await__())

        # infinite loop
        while True:
            try:
                with self._frame:
                    yield next(iter_obj)
            except StopIteration:
                break

        self._frame = None
        self._future = None


class ContextMenuEvent:
    """The object compatible with ContextMenu"""

    def __init__(self, item, path_string, expanded=None):
        self.item = item
        self.type = 0
        self.payload = {"prim_path": path_string, "node_open": expanded}

    def __str__(self):
        return str(self.item)


class ContextMenuHandler:
    """The object that the ContextMenu calls to expand the item"""

    def context_menu_handler(self, cmd, prim_path):
        """Not supported yet"""
        pass


class CollectionDelegate(ui.AbstractItemDelegate):
    def __init__(self):
        super().__init__()
        self._context_menu = ContextMenu()
        self._context_menu._stage_win = ContextMenuHandler()
        self._highlighting_enabled = None
        # Text that is highlighted in flat mode
        self._highlighting_text = None

    def build_branch(self, model, item, column_id, level, expanded):
        """Create a branch widget that opens or closes subtree"""

        # Getting some crashes..
        # if type(item)==ui.AbstractItem:
        #     return

        with ui.HStack(width=20 * (level + 2), height=0):
            ui.Spacer()
            if model.can_item_have_children(item):
                # Draw the +/- icon
                image_name = "Minus" if expanded else "Plus"
                ui.Image(
                    CollectionIcons().get(image_name),
                    width=10,
                    height=10,
                    style_type_name_override="TreeView.Item",
                    identifier="Image_plus_minus_icon",
                )
                ui.Spacer(width=5)

    def on_mouse_pressed(self, button, item, expanded, widget=None):
        """
        this is triggered when you click on an item in the tree, but also from the ScrollingFrame
        when you click anywhere inside the frame..
        """

        """Called when the user press the mouse button on the item"""
        if button != 1:
            # It's for context menu only (right click)
            return

        # If there's initally no item, we're being called from the ScrollingFrame
        # Getting the item requires some gymnastics...
        if not item:
            selection = widget._tree_view.selection
            if selection:
                item = selection[0]

        if item:
            # Form the event
            path = item.path if item else None
            event = ContextMenuEvent(item, path, expanded)

            # Show the menu
            self._context_menu.on_mouse_event(event)

    def build_widget(self, model, item, column_id, level, expanded):
        """Create a widget per item"""

        # Getting some crashes..
        # if type(item)==ui.AbstractItem:
        #     return

        enabled = True
        value_model = model.get_item_value_model(item, 0)
        if not value_model:
            return
        else:
            text = value_model.get_value_as_string()
            with ui.HStack(enabled=enabled, spacing=4, height=20, identifier=f"HStack_{text}"):
                # If highlighting disabled completely, all the items should be light
                is_highlighted = not self._highlighting_enabled and not self._highlighting_text
                if not is_highlighted:
                    # If it's not disabled disabled completley
                    is_highlighted = item.filtered

                # Gray out the icon if the filter string is not in the text
                iconname = "object_icon" if is_highlighted else "object_icon_grey"

                node_type = item.get_node_type()

                icon_filenames = [self.get_type_icon(node_type)]

                with ui.ZStack(width=20, height=20):
                    for icon_filename in icon_filenames:
                        image = ui.Image(
                            icon_filename,
                            name=iconname,
                            style_type_name_override="TreeView.Image",
                            identifier=f"Image_{node_type}",
                        )
                        if not enabled:
                            image.set_tooltip("Instance Proxy")

                # Normal mode. We need to highlight the whole item if it meets search requirement
                selection_chain = [text]
                labelnames_chain = ["explicit_member" if (item.is_explicit_collection_item()) else "object_name"]

                # Extend the label names depending on the size of the selection chain. Example, if it was [a, b]
                # and selection_chain is [z,y,x,w], it will become [a, b, a, b].
                labelnames_chain *= int(math.ceil(len(selection_chain) / len(labelnames_chain)))

                # These 2 are used by the right click context menu functionality
                def on_end_edit(label, field):
                    label.visible = True
                    field.visible = False
                    self.end_edit_subscription = None

                def on_mouse_double_clicked(label, field):
                    label.visible = False
                    field.visible = True
                    self.end_edit_subscription = field.model.subscribe_end_edit_fn(lambda _: on_end_edit(label, field))

                stack = ui.HStack()
                with stack:
                    for current_text, current_name in zip(selection_chain, labelnames_chain):
                        if not current_text:
                            continue

                        label = ui.Label(
                            current_text,
                            width=0,
                            name=current_name,
                            style_type_name_override="TreeView.Item",
                            mouse_pressed_fn=lambda x, y, b, _: self.on_mouse_pressed(
                                b, item, expanded
                            ),  # context menu
                            identifier=f"Label_{current_text}",
                        )

    def build_header(self, column_id):
        style_type_name = "TreeView.Header"
        if column_id == 0:
            with ui.HStack():
                ui.Spacer(width=10)
                ui.Label("Name", name="columnname", style_type_name_override=style_type_name)

    def set_highlighting(self, enable: bool = None, text: str = None):
        """
        Specify if the widgets should consider highlighting.
        """
        if enable is not None:
            self._highlighting_enabled = enable

        if text is not None:
            self._highlighting_text = text.lower()

    def get_type_icon(self, node_type):
        """Convert USD Type to icon file name"""
        icons = CollectionIcons()
        if node_type in ["DistantLight", "SphereLight", "RectLight", "DiskLight", "CylinderLight", "DomeLight"]:
            return icons.get(node_type, "Light")
        if node_type == "":
            node_type = "Xform"
        return icons.get(node_type, "Prim")
