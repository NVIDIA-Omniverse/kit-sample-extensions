# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
import abc
from typing import Dict, List, Optional

import carb
from omni import ui

from .browser_item import BaseItem, CategoryItem, CollectionItem, DetailItem


class AbstractBrowserModel(ui.AbstractItemModel):
    """
    Abstract model for the browser. User need to reimplement following functions:
        get_collection_items
        get_category_items
        get_detail_items

    This model uses a simple cache to get collection/category/detail items.
    Reimplement get_item_children if user wants own cache.

    Args:
        overview_name (str): Create a summary category and show all other categories as children if defined. Default None.
        always_realod_detail_items (bool): If True, always reload detail items. Otherwise, load detail items from cache if not updated. Default False

    Overridden functions:
        void execute(self, item: DetailItem): Execute a file.
            Args:
                item: Detail item to be executed.
        bool remove_collection(self, item: CollectionItem): Remove a collection.
            Args:
                item: Collection item to be removed.

    """

    def __init__(self, overview_name: Optional[str] = None, always_realod_detail_items: bool = False):
        super().__init__()

        self.overview_name = overview_name
        self._always_realod_detail_items = always_realod_detail_items
        # Cache of children
        self.__children_cache: Dict[Optional[BaseItem], List[BaseItem]] = {}
        self.add_item_changed_fn(lambda model, item: self.__remove_from_cache(None, item))

        self.__children_sort_changed: Dict[BaseItem, bool] = {}

    def __remove_from_cache(self, _, item: Optional[BaseItem]) -> None:
        children = self.__children_cache.pop(item, [])
        for c in children:
            self.__remove_from_cache(None, c)

    def get_item_children(self, item: Optional[BaseItem] = None) -> List[ui.AbstractItem]:
        """Returns all the children items for the widget.

        Args:
            item (Optional[BaseItem]): Parent item. If None, returns collection item list; if CollectionItem, returns category item list; if CategoryItem, returns detail item list; otherwise, returns empty list.

        Returns:
            List[ui.AbstractItem]: List of child items.
        """
        # A simple caching of all the returned items
        # If the user wants to use own caching, he needs to reimplement this
        # method.
        if item is None:
            if None not in self.__children_cache:
                self.__children_cache[None] = self.get_collection_items()
            return self.__children_cache[None]

        elif isinstance(item, CollectionItem):
            if item not in self.__children_cache:
                category_items = self.get_category_items(item)
                if self.overview_name is not None:
                    # Summary mode enabled, create a summary CategoryItem as root and others as children
                    summary_category_item = CategoryItem(self.overview_name, 0)
                    summary_category_item.children = category_items
                    self.__children_cache[item] = [summary_category_item]
                else:
                    self.__children_cache[item] = category_items
            return self.__children_cache[item]

        elif isinstance(item, CategoryItem):
            if item not in self.__children_cache or self._always_realod_detail_items:
                self.__children_cache[item] = self.get_detail_items(item)
                self.__children_sort_changed[item] = False
            if item in self.__children_sort_changed and self.__children_sort_changed[item]:
                # Sort items
                sort_args = self.get_sort_args()
                if sort_args:
                    self.__children_cache[item].sort(**sort_args)
                self.__children_sort_changed[item] = False
            return self.__children_cache[item]

        return []

    def sort_changed(self) -> None:
        """
        Notify sort changed.
        """
        for item in self.__children_cache:
            self.__children_sort_changed[item] = True

    def get_item_value_model(self, item: Optional[BaseItem] = None, index: int = 0) -> Optional[ui.AbstractValueModel]:
        """Get the item name model.

        Args:
            item (Optional[BaseItem]): Item to query. If not None, returns its name model; otherwise, returns None.
            index (int): Ignored parameter.

        Returns:
            Optional[ui.AbstractValueModel]: The name model of the item or None if item is None.
        """
        if item is None:
            return None
        return item.name_model

    def get_item_value_model_count(self, item=None) -> int:
        """Returns the number of columns.

        Args:
            item (Optional[BaseItem]): Unused parameter.

        Returns:
            int: Count of value models, always 1.
        """
        return 1

    @abc.abstractmethod
    def get_collection_items(self) -> List[CollectionItem]:
        """Get list of collection items for collection combobox.

        Returns:
            List[CollectionItem]: List of collection items.
        """
        pass

    @abc.abstractmethod
    def get_category_items(self, item: CollectionItem) -> List[CategoryItem]:
        """Get list of category items for category view.

        Args:
            item (CollectionItem): Parent collection item for categories.

        Returns:
            List[CategoryItem]: List of category items.
        """
        pass

    @abc.abstractmethod
    def get_detail_items(self, item: CategoryItem) -> List[DetailItem]:
        """Get list of detail items for detail view.

        Args:
            item (CategoryItem): Parent category item for details.

        Returns:
            List[DetailItem]: List of detail items.
        """
        pass

    @abc.abstractmethod
    def get_sort_args(self) -> Optional[Dict]:
        """Get sort args to sort item list.

        Returns:
            Optional[Dict]: Sorting arguments in format {"key": key, "reverse": reverse}.
        """
        return None

    def execute(self, item: DetailItem) -> None:
        """Execute a detail item.

        Args:
            item (DetailItem): Detail item to be executed.
        """
        pass

    def remove_collection(self, item: CollectionItem) -> bool:
        """Remove a collection item.

        Args:
            item (CollectionItem): Collection item to be removed.

        Returns:
            bool: True if removal succeeded.
        """
        return True
