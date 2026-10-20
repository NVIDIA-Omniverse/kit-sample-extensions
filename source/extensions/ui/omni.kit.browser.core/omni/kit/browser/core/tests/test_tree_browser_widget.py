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
from omni.kit.browser.core import (
    AbstractBrowserModel,
    CategoryItem,
    CollectionItem,
    DetailItem,
    TreeBrowserWidget,
    TreeCategoryDelegate,
)
from omni.ui.tests.test_base import OmniUiTest

from .common import TreeBrowserModel

CURRENT_PATH = Path(__file__).parent
TEST_DATA_PATH = CURRENT_PATH.parent.parent.parent.parent.parent.joinpath("data").joinpath("tests")


class TestTreeCategoryDelegate(TreeCategoryDelegate):
    def _on_item_right_click(self, item: CategoryItem):
        self._right_click_item = item


class TestTreeBrowserWidget(OmniUiTest):
    # Before running each test
    async def setUp(self):
        await super().setUp()

        self._golden_img_dir = TEST_DATA_PATH.absolute().joinpath("golden_img").absolute()
        self._browser_model = TreeBrowserModel(show_all=True)
        self._window = await self.create_test_window(width=500, height=600, block_devices=False)
        self._delegate = TestTreeCategoryDelegate(hide_zero_count=True)
        with self._window.frame:
            self._browser_widget = TreeBrowserWidget(self._browser_model, category_delegate=self._delegate)

        self._browser_widget.collection_index = 0
        await omni.kit.app.get_app().next_update_async()

    # After running each test
    async def tearDown(self):
        # Rotations outlive the test otherwise: they never return on their own, and a test that
        # starts one for a loading row would leave it waking every frame for the rest of the run.
        self._delegate.destroy()
        self._window = None
        await super().tearDown()

    def __spin(self, item: CategoryItem):
        """Give a row what a loading one has: a rotation of its own."""

        async def forever():
            while True:
                await omni.kit.app.get_app().next_update_async()

        self._delegate._rotate_future[item] = asyncio.ensure_future(forever())

    def __live_rows(self):
        return self._browser_widget._live_category_items()

    async def test_the_live_rows_are_the_whole_tree(self):
        """
        What the widget hands a delegate when the tree is rebuilt.

        The top level is not the tree - a category has children, and they are rows too. Handing over
        the roots alone said every nested row had gone, and the delegate would stop the spinner of a
        sub folder that is on screen and still scanning.
        """
        model = self._browser_widget._category_view.model
        roots = list(model.get_item_children(None) or [])
        nested = [child for root in roots for child in (model.get_item_children(root) or [])]
        self.assertTrue(nested, "the fixture has no nested categories to test with")

        live = self.__live_rows()

        for row in roots + nested:
            self.assertIn(row, live, "a row on screen was reported as gone")

    async def test_pruning_keeps_the_rows_that_are_still_there(self):
        """The delegate's half of it: only what has gone stops."""
        live = self.__live_rows()
        staying = live[0]
        gone = CategoryItem("removed")
        self.__spin(staying)
        self.__spin(gone)

        self._delegate._prune_rows(live)
        await omni.kit.app.get_app().next_update_async()

        self.assertIn(staying, self._delegate._rotate_future, "a row on screen lost its spinner")
        self.assertNotIn(gone, self._delegate._rotate_future, "a row that left the tree kept spinning")

    # Clearing the collection - collection_index = -1, which is the other path that prunes - is not
    # covered here: it crashes this widget in the test app on its own, with no spinner and no
    # pruning in play. Reported rather than worked around, since it is not this change's doing.

    async def test_general(self):
        """Testing general look of TreeBrowserWidget"""

        # Wait for icon loaded
        await asyncio.sleep(5)

        # Expand first item
        collections = self._browser_model.get_item_children(None)
        category = self._browser_model.get_item_children(collections[0])[1]
        self._browser_widget._category_view.set_expanded(category, True, True)
        self._browser_model._item_changed(category)
        await omni.kit.app.get_app().next_update_async()

        await self.finalize_test(golden_img_dir=self._golden_img_dir, golden_img_name="tree_general.png")

    async def test_item_loading(self):
        collections = self._browser_model.get_item_children(None)
        category = self._browser_model.get_item_children(collections[0])[1]

        try:
            category.loading = True
            # self._browser_widget._category_view.set_expanded(category, True, True)
            self._browser_model._item_changed(category)
            await omni.kit.app.get_app().next_update_async()

            await self.capture_and_compare(golden_img_dir=self._golden_img_dir, golden_img_name="tree_loading.png")

            category.loading = False
            self._browser_model._item_changed(category)
            await omni.kit.app.get_app().next_update_async()
            await self.capture_and_compare(golden_img_dir=self._golden_img_dir, golden_img_name="tree_loading_done.png")
        finally:
            await self.finalize_test_no_image()

    async def test_right_click(self):
        collections = self._browser_model.get_item_children(None)
        category = self._browser_model.get_item_children(collections[0])[1]
        await ui_test.emulate_mouse_move_and_click(ui_test.Vec2(52, 43), right_click=True)
        self.assertEqual(self._delegate._right_click_item, category)
        await self.finalize_test_no_image()
