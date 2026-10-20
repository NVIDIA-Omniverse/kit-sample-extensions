# Copyright (c) 2018-2021, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#
from types import MethodType
from typing import Any

import omni.ui as ui


class QuickSearchItem(ui.AbstractItem):
    """Single item of the model"""

    def __init__(self, name: str):
        super().__init__()
        self.name_model = ui.SimpleStringModel(name)

    def __repr__(self):
        return f'QuickSearchItem<"{self.name_model.as_string}">'


class QuickSearchModel(ui.AbstractItemModel):
    """
    The model wrapper. We need it to recreate the model and keep the wrapped
    source unchanged. And to override some methods of the source model, like
    the name of the root.
    """

    def __init__(self, name: str, route_model: ui.AbstractItemModel):
        super().__init__()
        # We also needs to be notified if the child model changes
        old_item_changed = route_model._item_changed

        def _item_changed(model, item):
            self._item_changed(item)
            old_item_changed(item)

        route_model._item_changed = MethodType(_item_changed, route_model)
        self._route_model = route_model
        self.__root = QuickSearchItem(name)

    def destroy(self):
        self._route_model = None
        self.__root = None

    def get_item_children(self, item: Any):
        """Returns all the children when the widget asks it."""
        return self._route_model.get_item_children(item)

    def get_item_value_model_count(self, item):
        """The number of columns"""
        return 1

    def get_item_value_model(self, item: Any, column_id: int):
        """
        Return value model.
        It's the object that tracks the specific value.
        """
        if item is None:
            return self.__root.name_model

        return self._route_model.get_item_value_model(item, column_id)

    def get_drag_mime_data(self, item):
        """Called for DnD"""
        return self._route_model.get_drag_mime_data(item)

    def execute(self, item: Any):
        """Try if the source model has the execute method and call it"""
        execute_op = getattr(self._route_model, "execute", None)
        if callable(execute_op):
            execute_op(item)

    def complete(self, current_value: str, item: Any) -> str:
        """the complete methods will either call the complete command on the model or it do nothing
        returning the current value
        """
        complete_op = getattr(self._route_model, "complete", None)
        if callable(complete_op):
            return complete_op(current_value, item)
        else:
            return current_value


class QuickSearchFlatModel(QuickSearchModel):
    """
    The model wrapper for the filtered flat list. It iterates the source
    model, filters children and pretends it's the same model but with all the
    children parented to the root.
    """

    def __init__(self, name: str, route_model: ui.AbstractItemModel, flat: bool = True):
        super().__init__(name, route_model)
        self.__filter: str = ""
        self.__flat = flat

    def __get_item_children_recursive(self, item):
        """Get all the children from all the levels"""
        children = []
        for child in super().get_item_children(item):
            recursion = self.__get_item_children_recursive(child)
            if not recursion:
                # Leaf
                children.append(child)
            else:
                # Sub-children
                children += recursion
        return children

    def get_item_children(self, item):
        if self.__flat:
            return self.get_item_children_flatten(item)

        return super().get_item_children(item)

    def get_item_children_flatten(self, item):
        """Flattens the hirarchy and returns the children."""
        if item is not None:
            return []

        # Flat list of all the children
        items = self.__get_item_children_recursive(None)

        filter_by_text_op = getattr(self._route_model, "filter_by_text", None)
        if not callable(filter_by_text_op):
            # The source model doesn't have any filter, we filter it here
            filter_lower = self.__filter.lower()
            items = [item for item in items if filter_lower in self.get_item_value_model(item, 0).as_string.lower()]
        # else: pass # If the model has filter_by_text, it can filter the items

        return items

    def filter_by_text(self, filter_text: str):
        """Specify the filter string that is used to reduce the model"""
        if filter_text == self.__filter:
            return

        # If the model has filter_by_text, execute it.
        filter_by_text_op = getattr(self._route_model, "filter_by_text", None)
        if callable(filter_by_text_op):
            filter_by_text_op(filter_text)

        self.__filter = filter_text
        self._item_changed(None)
