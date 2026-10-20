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

from omni.kit.browser.core import AbstractBrowserModel, CategoryItem, CollectionItem, DetailItem


class SimpleBrowserModel(AbstractBrowserModel):
    """The simple model. Custom implementation of the browser model."""

    def __init__(self, overview_name: Optional[str] = None):
        super().__init__(overview_name=overview_name)
        self.category_count = 5
        self.detail_count = 10
        self.execute_item = None

    def get_collection_items(self) -> List[CollectionItem]:
        return [CollectionItem("Remote", "omniverse"), CollectionItem("Local", "/Users")]

    def get_category_items(self, item: CollectionItem) -> List[CategoryItem]:
        category_items = []
        for i in range(self.category_count):
            name = f"{item.name}_{i+1}"
            category_items.append(CategoryItem(name, 10))
        return category_items

    def get_detail_items(self, item: CategoryItem) -> List[DetailItem]:
        detail_items = []
        for i in range(self.detail_count):
            name = f"{item.name}_{i+1}"
            url = f"/{item.name}/{name}"
            detail_items.append(DetailItem(name, url))
        return detail_items

    def execute(self, item: DetailItem) -> None:
        self.execute_item = item


class TreeBrowserModel(AbstractBrowserModel):
    """The simple model. Custom implementation of the browser model."""

    def __init__(self, overview_name: Optional[str] = None, show_all: bool = False):
        self._show_all = show_all
        super().__init__(overview_name=overview_name)

    def get_collection_items(self) -> List[CollectionItem]:
        return [CollectionItem("Remote", "omniverse"), CollectionItem("Local", "/Users")]

    def get_category_items(self, item: CollectionItem) -> List[CategoryItem]:
        category_items = []
        if self._show_all:
            category_items.append(CategoryItem("ALL", 0))
        for i in range(5):
            name = f"{item.name}_{i+1}"
            category_item = CategoryItem(name, 10)
            for j in range(5):
                name = f"{item.name}_{i+1}_{j+1}"
                category_item.children.append(CategoryItem(name, 1))
            empty_child = CategoryItem("Empty", 0)
            empty_child.children.append(CategoryItem("Empty", 0))
            category_item.children.append(empty_child)
            category_items.append(category_item)
        category_items.append(CategoryItem("Empty", 0))
        return category_items

    def get_detail_items(self, item: CategoryItem) -> List[DetailItem]:
        detail_items = []
        for i in range(10):
            name = f"{item.name}_{i+1}"
            url = f"/{item.name}/{name}"
            detail_items.append(DetailItem(name, url))
        return detail_items
