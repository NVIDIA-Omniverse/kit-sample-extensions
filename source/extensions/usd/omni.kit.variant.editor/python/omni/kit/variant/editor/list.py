# Copyright (c) 2023, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

import weakref

import carb
from omni import ui

from .ui_const import COLORS, DarkColors, LightColors
from .util import AbstractValueModelDelegate, get_ui_style


# Base list class for the other lists to inherit from
class ListItem(ui.AbstractItem):
    """Single item of list"""

    def __init__(self, values, delegate=None):
        super().__init__()

        self._children = []

        if delegate is None:
            self._delegate = AbstractValueModelDelegate()
        else:
            self._delegate = delegate

        self._models = []

        if type(values) != list:
            values = [values]
        for value in values:
            data, data_type = self._get_data(value)
            value_model = self._delegate.get_value_model(data, data_type)
            if value_model:
                self._models.append(value_model)

    def destroy(self):
        for child_item in self._children:
            child_item.destroy()

        self._children.clear()
        self._models.clear()

    @property
    def children(self):
        return self._children

    def add_child_item(self, child_item):
        self._children.append(child_item)

    def get_value_model(self, index=0):
        if index >= len(self._models) or index < 0:
            return None
        return self._models[index]

    def _get_data(self, value):
        if type(value) == str:
            datas = value.split("##")
            if len(datas) == 2:
                return datas
            else:
                return (value, "string")
        else:
            return (value, None)

    def __repr__(self):
        return f'"{self._models[0].as_string}"'


class ItemModel(ui.AbstractItemModel):
    """Represents item model"""

    def __init__(self, columns_count=1):
        self._columns_count = columns_count
        super().__init__()
        self._children = []

    @property
    def items(self):
        return self._children

    def insert_item(self, item, index=-1):
        """Insert item into list model"""
        if index < 0:
            self._children.append(item)
        else:
            self._children.insert(index, item)
        self._item_changed(None)

    def remove_item(self, item):
        index = self._children.index(item)
        self.remove_index(index)

    def remove_index(self, index):
        if index < 0 or index >= len(self._children):
            return

        del self._children[index]
        self._item_changed(None)

    def clear(self):
        """Clear all children"""
        self._children = []
        self._item_changed(None)

    def on_item_updated(self, item=None):
        self._item_changed(item)

    """Basic AbstractItemModel functions"""

    def get_item_children(self, item=None):
        """Returns all the children when the widget asks it."""
        if item is not None:
            return []

        return self._children

    def get_item_value_model_count(self, item=None):
        """The number of columns"""
        return self._columns_count

    def get_item_value_model(self, item=None, column_id=0):
        """Return value model for columns"""
        if item is None:
            return None
        return item.get_value_model(column_id)


class ListModel(ItemModel):
    """Represents lists"""

    def __init__(self, columns_count=1, enable_drag_drop=True):
        super().__init__(columns_count=columns_count)
        self._enable_drag_drop = enable_drag_drop

    """Enable drag and drop"""

    def get_drag_mime_data(self, item):
        """Returns Multipurpose Internet Mail Extensions (MIME) data for be able to drop this item somewhere"""
        # As we don't do Drag and Drop to the operating system, we return the string.
        return item.get_value_model(0).as_string

    def drop_accepted(self, target_item, source, drop_location=-1):
        """Reimplemented from AbstractItemModel. Called to highlight target when drag and drop."""
        if not self._enable_drag_drop:
            return False
        else:
            return not target_item and drop_location >= 0

    def drop(self, target_item, source, drop_location=-1):
        """Reimplemented from AbstractItemModel. Called when dropping something to the item."""
        try:
            source_id = self._children.index(source)
        except ValueError:
            # Not in the list. This is the source from another model.
            return

        if source_id == drop_location:
            # Nothing to do
            return

        self.remove_item(source)

        if drop_location > len(self._children):
            # Drop it to the end
            self.insert_item(source)
        else:
            if source_id < drop_location:
                # Becase when we removed source, the array became shorter
                drop_location = drop_location - 1

            self.insert_item(source, drop_location)

        self._item_changed(None)


# TODO - Move this style info out of here and into ui_const.py


class ListView:
    LIGHT_STYLE = {
        "TreeView": {
            "background_color": LightColors.Background,
            "secondary_color": COLORS.TRANSPARENT,
        },
        "TreeView.Frame": {
            "background_color": LightColors.Background,
            "secondary_color": LightColors.Text,
            "border_radius": 0,
        },
        "TreeView.Item": {"color": LightColors.Text, "margin": 1},
        "TreeView.Item:hovered": {"background_color": LightColors.BackgroundHovered},
        "TreeView.Item:selected": {"background_color": LightColors.BackgroundSelected},
    }
    DARK_STYLE = {
        "border_radius": 1,
        "margin": 0,
        "TreeView": {
            "background_color": DarkColors.Background,
            "secondary_color": COLORS.TRANSPARENT,
        },
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
        model=ListModel(columns_count=1),
        column_widths=[ui.Percent(10)],
        on_item_selected_fn=None,
        multi_selection=False,
        root_visible=False,
        header_visible=False,
        scrolling_frame=False,
        keep_expanded=True,
        on_mouse_pressed_fn=None,
        **kwargs,
    ):
        self._multi_selection = multi_selection
        self._on_item_selected_fn = on_item_selected_fn
        self._on_mouse_pressed_fn = on_mouse_pressed_fn

        frame_kwargs = {
            "style": kwargs.get("style", self.UI_STYLES[get_ui_style()]),
        }
        for arg in ["height"]:
            value = kwargs.pop(arg, None)
            if value is not None:
                frame_kwargs[arg] = value

        # Toggle whether the frame is a ui.Frame or ui.ScrollingFrame
        frame = ui.ScrollingFrame(**frame_kwargs) if scrolling_frame else ui.Frame(**frame_kwargs)
        with frame:
            self._tree_view = ui.TreeView(
                model,
                root_visible=root_visible,
                header_visible=header_visible,
                keep_expanded=keep_expanded,
                mouse_hovered_fn=lambda btn: self._on_hover_changed(btn),
                **kwargs,
            )
        self._tree_view.set_selection_changed_fn(self._on_selection_changed)
        self._tree_view.set_accept_drop_fn(self._on_accept_drop)
        self._tree_view.set_drop_fn(self._on_drop)
        if len(column_widths) > 0:
            self._tree_view.column_widths = column_widths

        self.model._tree_view = weakref.ref(self._tree_view)

    def destroy(self):
        self._on_item_selected_fn = None
        self._on_mouse_pressed_fn = None
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
            # Disable multi selection
            if selections and len(selections) > 1:
                selections = selections[-1:]
                self._tree_view.selection = selections

        for item in selections:
            if self._on_item_selected_fn:
                self._on_item_selected_fn(item)

    def _on_mouse_pressed(self, *args, **kwargs):
        pass

    def _on_accept_drop(self, item):
        pass

    def _on_drop(self, item):
        pass

    def _on_hover_changed(self, btn):
        pass
