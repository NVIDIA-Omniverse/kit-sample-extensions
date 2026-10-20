# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

# NOTE:
#   omni.kit.test - std python's unittest module with additional wrapping to add suport for async/await tests
#   For most things refer to unittest docs: https://docs.python.org/3/library/unittest.html
from typing import List

import omni.kit.test

# Import extension python module we are testing with absolute import path, as if we are external user (other extension)
from omni.kit.browser.core import AbstractBrowserModel, CategoryItem, CollectionItem, DetailItem

from ..models import CollectionModelWrapper, SingleLevelWrapper


class SimpleBrowserModel(AbstractBrowserModel):
    """The simple model. Custom implementation of the browser model."""

    def __init__(self):
        super().__init__()
        self._collections = [CollectionItem("Remote", "omniverse"), CollectionItem("Local", "/Users")]
        self._categories = {}
        self._details = {}

        for collection_item in self._collections:
            for i in range(5):
                name = f"{collection_item.name}_{i+1}"
                self.append_catetory_item(collection_item, CategoryItem(name))

        for collection_item in self._categories:
            category_items = self._categories[collection_item]
            for category_item in category_items:
                for i in range(10):
                    name = f"{category_item.name}_{i+1}"
                    url = f"/{category_item.name}/{name}"
                    self.append_detail_item(category_item, DetailItem(name, url))

    def get_collection_items(self) -> List[CollectionItem]:
        return self._collections

    def get_category_items(self, item: CollectionItem) -> List[CategoryItem]:
        if item in self._categories:
            return self._categories[item]

    def get_detail_items(self, item: CategoryItem) -> List[DetailItem]:
        if item in self._details:
            return self._details[item]

    def append_catetory_item(self, collection_item: CollectionItem, catetory_item: CategoryItem) -> None:
        if collection_item not in self._categories:
            self._categories[collection_item] = []
        self._categories[collection_item].append(catetory_item)

    def append_detail_item(self, category_item: CategoryItem, detail_item: DetailItem) -> None:
        if category_item not in self._details:
            self._details[category_item] = []
        self._details[category_item].append(detail_item)
        category_item.count += 1


# Having a test class dervived from omni.kit.test.AsyncTestCase declared on the root of module will make it auto-discoverable by omni.kit.test
class TestBrowserModel(omni.kit.test.AsyncTestCase):
    # Before running each test
    async def setUp(self):
        self._browser_model = SimpleBrowserModel()

    # After running each test
    async def tearDown(self):
        self._browser_model = None

    # Actual test, notice it is "async" function, so "await" can be used if needed
    async def test_initialization_function(self):
        collection_model = CollectionModelWrapper(self._browser_model, None)

        # Index
        index_model = collection_model.get_item_value_model(None)
        self.assertEqual(index_model.as_int, -1)

        # Collection items
        collections = collection_model.get_item_children()
        self.assertEqual(len(collections), 2)
        self.assertEqual(collections[0].name, "Remote")
        self.assertEqual(collections[0].url, "omniverse")
        self.assertEqual(collections[1].name, "Local")
        self.assertEqual(collections[1].url, "/Users")

        # Empty wrapper
        category_model = SingleLevelWrapper()
        categories = category_model.get_item_children()
        self.assertEqual(len(categories), 0)

        detail_model = SingleLevelWrapper()

        # Category items
        for collection_item in collections:
            category_model.set_sources(self._browser_model, collection_item)
            categories = category_model.get_item_children()
            self.assertEqual(len(categories), 5)
            for i in range(5):
                expected_category_name = f"{collection_item.name}_{i+1}"
                self.assertEqual(categories[i].name, expected_category_name)
                self.assertEqual(categories[i].count, 10)
                detail_model.set_sources(self._browser_model, categories[i])
                details = detail_model.get_item_children()
                self.assertEqual(len(details), 10)
                for j in range(10):
                    expected_detail_name = f"{expected_category_name}_{j+1}"
                    self.assertEqual(details[j].name, expected_detail_name)
                    self.assertEqual(details[j].thumbnail, "")

    async def test_collection_function(self):
        collection_model = CollectionModelWrapper(self._browser_model, None)
        collections = collection_model.get_item_children()

        # Change index
        def on_selection_changed(item, golden):
            self.assertEqual(item, golden)

        sub_id = collection_model.add_selection_changed_fn(
            lambda item, golden=collections[0]: on_selection_changed(item, golden)
        )
        collection_model.current_index = 0
        collection_model.remove_selection_changed_fn(sub_id)

        sub_id = collection_model.add_selection_changed_fn(
            lambda item, golden=collections[1]: on_selection_changed(item, golden)
        )
        collection_model.current_index = 1
        collection_model.remove_selection_changed_fn(sub_id)

        sub_id = collection_model.add_selection_changed_fn(lambda item, golden=None: on_selection_changed(item, golden))
        collection_model.current_index = -1
        collection_model.remove_selection_changed_fn(sub_id)
