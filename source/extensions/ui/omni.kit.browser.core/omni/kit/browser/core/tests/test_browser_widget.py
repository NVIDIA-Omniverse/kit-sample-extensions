# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
import asyncio
from pathlib import Path
from typing import List

import omni.kit.app
import omni.kit.ui_test as ui_test
from omni.kit.browser.core import BrowserWidget
from omni.ui.tests.test_base import OmniUiTest

from .common import SimpleBrowserModel

CURRENT_PATH = Path(__file__).parent
TEST_DATA_PATH = CURRENT_PATH.parent.parent.parent.parent.parent.joinpath("data").joinpath("tests")


class TestBrowserWidget(OmniUiTest):
    # Before running each test
    async def setUp(self):
        await super().setUp()

        self._golden_img_dir = TEST_DATA_PATH.absolute().joinpath("golden_img").absolute()
        self._browser_model = SimpleBrowserModel()

    # After running each test
    async def tearDown(self):
        self._browser_widget.destroy()
        await super().tearDown()

    async def test_general(self):
        """Testing general look of BrowserWidget"""
        window = await self.create_test_window(width=500, height=600)
        with window.frame:
            self._browser_widget = BrowserWidget(self._browser_model)

        await omni.kit.app.get_app().next_update_async()
        await self.finalize_test(golden_img_dir=self._golden_img_dir, golden_img_name="general.png")

    async def test_collection_changed(self):
        window = await self.create_test_window(width=500, height=600)
        with window.frame:
            self._browser_widget = BrowserWidget(self._browser_model)

        self.assertTrue(self._browser_widget.visible)
        self._browser_widget.visible = False
        self.assertFalse(self._browser_widget.visible)
        self._browser_widget.visible = True
        self.assertEqual(self._browser_widget.model, self._browser_model)
        self.assertEqual(self._browser_widget.collection_index, -1)
        self.assertIsNone(self._browser_widget.collection_selection)
        self._browser_widget.collection_index = 0
        # Wait for icon loaded
        await asyncio.sleep(5)
        self.assertIsNotNone(self._browser_widget.collection_selection)
        collection_items = self._browser_model.get_item_children(None)
        category_item = self._browser_model.get_item_children(collection_items[0])[0]
        self.assertEqual(self._browser_widget.category_selection, [category_item])
        self.assertEqual(self._browser_widget.detail_selection, [])

        await self.finalize_test(golden_img_dir=self._golden_img_dir, golden_img_name="collection_changed.png")

    async def test_refresh_collection(self):
        window = await self.create_test_window(width=500, height=600)
        with window.frame:
            self._browser_widget = BrowserWidget(self._browser_model)

        self._browser_widget.collection_index = 0
        await omni.kit.app.get_app().next_update_async()
        self._browser_model.category_count = 3
        self._browser_model._item_changed(self._browser_model.get_item_children(None)[0])

        await omni.kit.app.get_app().next_update_async()

        await self.finalize_test(golden_img_dir=self._golden_img_dir, golden_img_name="refresh_collection.png")

    async def test_select_category_always(self):
        window = await self.create_test_window(width=500, height=600)
        with window.frame:
            self._browser_widget = BrowserWidget(self._browser_model)

        self._browser_widget.collection_index = 0

        # Keep last category selection if changed selection to Empty
        await omni.kit.app.get_app().next_update_async()
        collection_items = self._browser_model.get_item_children(None)
        category_item = self._browser_model.get_item_children(collection_items[0])[1]
        self._browser_widget.category_selection = [category_item]
        await omni.kit.app.get_app().next_update_async()
        self._browser_widget.category_selection = []

        await omni.kit.app.get_app().next_update_async()
        self.assertEqual(self._browser_widget.category_selection, [category_item])

        await self.finalize_test_no_image()

    async def test_change_category_selection(self):
        def __on_category_selection_changed(category_item) -> None:
            self.__selected_category_item = category_item

        window = await self.create_test_window(width=500, height=600)
        with window.frame:
            self._browser_widget = BrowserWidget(
                self._browser_model,
                always_select_category=False,
                on_category_selection_changed_fn=__on_category_selection_changed,
                show_category_splitter=True,
            )

        self._browser_widget.collection_index = 0
        await omni.kit.app.get_app().next_update_async()
        collection_items = self._browser_model.get_item_children(None)
        category_item = self._browser_model.get_item_children(collection_items[0])[0]
        self._browser_widget.category_selection = [category_item]
        await omni.kit.app.get_app().next_update_async()
        self.assertEqual(self.__selected_category_item, category_item)
        self._browser_widget.category_selection = []

        await omni.kit.app.get_app().next_update_async()
        self.assertIsNone(self.__selected_category_item)

        await self.finalize_test(golden_img_dir=self._golden_img_dir, golden_img_name="change_category_selection.png")

    async def test_thumbnail_size(self):
        window = await self.create_test_window(width=500, height=600)
        with window.frame:
            self._browser_widget = BrowserWidget(self._browser_model)

        self._browser_widget.collection_index = 0

        def __on_thumbnail_size_changed(size: int) -> None:
            self.__thumbnail_size = size

        sub_id = self._browser_widget.add_thumbnail_size_changed_fn(__on_thumbnail_size_changed)
        await omni.kit.app.get_app().next_update_async()
        window_ref = ui_test.WindowRef(window, "")
        slider_ref = window_ref.find_all(f"**/IntSlider[*]")[0]
        slider_ref.widget.model.set_value(64)
        for _ in range(40):
            await omni.kit.app.get_app().next_update_async()

        self.assertEqual(self.__thumbnail_size, 64)
        self.assertEqual(self._browser_widget._detail_view.thumbnail_size, 64)
        self._browser_widget.remove_thumbnail_size_changed_fn(sub_id)
        await self.finalize_test(golden_img_dir=self._golden_img_dir, golden_img_name="thumbnail_size.png")

    async def test_navigation_off(self):
        window = await self.create_test_window(width=500, height=600)
        with window.frame:
            self._browser_widget = BrowserWidget(self._browser_model)
        self._browser_widget.show_widgets(collection=False, category=False)

        await omni.kit.app.get_app().next_update_async()
        await self.finalize_test(golden_img_dir=self._golden_img_dir, golden_img_name="navigation_off.png")

    async def test_filter(self):

        def __on_filter_changed(words) -> None:
            self.__filter_words = words

        window = await self.create_test_window(width=500, height=600)
        with window.frame:
            self._browser_widget = BrowserWidget(self._browser_model)
        sub_id = self._browser_widget.add_filter_changed_fn(__on_filter_changed)
        self._browser_widget.collection_index = 0
        filter_words = ["1", "0"]
        self._browser_widget.filter_details(filter_words)
        for _ in range(10):
            await omni.kit.app.get_app().next_update_async()
        self.assertEqual(self.__filter_words, filter_words)
        self._browser_widget.remove_filter_changed_fn(sub_id)

        await self.finalize_test(golden_img_dir=self._golden_img_dir, golden_img_name="filter.png")
