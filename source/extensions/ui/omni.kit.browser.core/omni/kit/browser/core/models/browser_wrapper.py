# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
from typing import List, Optional

from omni import ui

from .browser_item import CategoryItem, CollectionItem
from .browser_model import AbstractBrowserModel, BaseItem


class SingleLevelWrapper(ui.AbstractItemModel):
    """
    The model pretends a source model with one single level of children
    Args:
        source_model (Optional[AbstractBrowserModel]): source data model. None for empty wrapper.
        root_item (Optional[BaseItem]): using children item list of this item as data items, comes from source_model.
    """

    def __init__(self, source_model: Optional[AbstractBrowserModel] = None, root_item: Optional[BaseItem] = None):
        super().__init__()
        # It's not 100% sure but it's probably better to use weak pointers. It
        # depends on how often the uber model is recreated.
        self._source_model = source_model
        self._root_item = root_item

    def set_sources(self, source_model: Optional[AbstractBrowserModel] = None, root_item: Optional[BaseItem] = None):
        """
        Update data source and trigger item changed for binded widget
        Args:
            source_model (Optional[AbstractBrowserModel]): source data model. None for empty wrapper.
            root_item (Optional[BaseItem]): using children item list of this item as data items, comes from source_model.
        """
        if source_model != self._source_model or root_item != self._root_item:
            self._source_model = source_model
            self._root_item = root_item
            self._item_changed(None)

    def get_item_value_model(
        self, item: Optional[BaseItem] = None, column_id: int = 0
    ) -> Optional[ui.AbstractValueModel]:
        """
        Get the item name model.
        Args:
            item (Optional[BaseItem]): item to query. If not None, return its name model. Otherwise return None.
            column_id (int): ignored.
        """
        if self._source_model is None:
            return None
        else:
            return self._source_model.get_item_value_model(item, column_id)

    def get_item_children(self, item=None) -> List[ui.AbstractItem]:
        """
        Returns all the children when the widget asks it.
        Return empty list if source model not defined.
        """
        if self._source_model is None:
            return []
        elif item is not None:
            if isinstance(item, CategoryItem):
                return item.children
            else:
                return []

        return self._source_model.get_item_children(self._root_item)

    def get_item_value_model_count(self, item=None) -> int:
        """The number of columns"""
        return 1 if self._source_model is None else self._source_model.get_item_value_model_count(self._root_item)


class CollectionModelWrapper(SingleLevelWrapper):
    """
    The model that has int value in the root, so it's acceptable by combo box.
    Args:
        source_model (Optional[AbstractBrowserModel]): source data model. None for empty wrapper.
        root_item (Optional[BaseItem]): using children item list of this item as data items, comes from source_model.
    """

    def __init__(self, source_model, root_item):
        super().__init__(source_model, root_item)

        # The current index of the combo box
        self._current_index = ui.SimpleIntModel(-1)
        self._current_index.add_value_changed_fn(self._on_current_index_changed)
        # Callbacks when selected collection changed. Use this to refresh category list view.
        self._on_selection_changed_fns = []

    @property
    def current_index(self) -> int:
        return self._current_index.as_int

    @current_index.setter
    def current_index(self, value: int) -> None:
        if value != self.current_index:
            self._current_index.set_value(value)

    def get_item_value_model(self, item=None, column_id=0) -> ui.AbstractValueModel:
        if item is None:
            return self._current_index
        else:
            return super().get_item_value_model(item=item, column_id=column_id)

    def add_selection_changed_fn(self, on_selection_changed_fn: callable) -> int:
        """
        Add notification when current selected collection changed.
        Args:
            on_selection_changed_fn (func): Function called when current selected collection changed. Return notificaation
                id used for remove_selection_changed_fn. Function signature:
                int on_selection_changed_fn(collection_item: CollectionItem)
        """
        id = len(self._on_selection_changed_fns)
        self._on_selection_changed_fns.append(on_selection_changed_fn)
        return id

    def remove_selection_changed_fn(self, id: int) -> bool:
        """
        Remove notification on current selected collection changed.
        Args:
            id (int): Notification id returned from add_selection_changed_fn.
        """
        if id >= 0 and id < len(self._on_selection_changed_fns):
            self._on_selection_changed_fns[id] = None
            return True
        else:
            return False

    def _on_current_index_changed(self, model: ui.AbstractValueModel) -> None:
        collection_item = self._get_current_item()
        for fn in self._on_selection_changed_fns:
            if fn is not None:
                fn(collection_item)
        self._item_changed(None)

    def _get_current_item(self) -> CollectionItem:
        """Get Current selected collection item"""
        index = self._current_index.as_int
        if index >= 0:
            collections = self.get_item_children()
            if index < len(collections):
                return collections[index]
            else:
                return None
        else:
            return None


class ChildrenModelWrapper(SingleLevelWrapper):
    """
    This model represents a data model to get children of item.
    Note:
        Current only category item has children.
    """

    def get_item_children(self, item=None) -> List[ui.AbstractItem]:
        """
        Returns all the children when the widget asks it.
        Return empty list if source model not defined.
        """
        if self._source_model is None:
            return []
        elif item is None:
            if isinstance(self._root_item, CategoryItem):
                return self._root_item.children
        elif isinstance(item, CategoryItem):
            return item.children

        return []
