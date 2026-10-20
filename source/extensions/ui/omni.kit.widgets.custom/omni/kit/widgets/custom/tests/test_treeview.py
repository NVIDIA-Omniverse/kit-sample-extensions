# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
from ..model import SimpleListItem
from ..treeview import SimpleListView
from .utils import GOLDEN_IMG_DIR, TestWidgetsCustomBase, wait_frames


class TestTreeView(TestWidgetsCustomBase):
    def _insert_list_items(self, num):
        for i in range(num):
            self._tree_view.insert(SimpleListItem(f"Item {i}"))

    # Before running each test
    async def setUp(self):
        await super().setUp()
        self._golden_img_dir = GOLDEN_IMG_DIR

        self._hide_main_menu_bar()
        self._tree_view = None

    # After running each test
    async def tearDown(self):
        if self._tree_view:
            self._tree_view.clear()
            self._tree_view = None

        await super().tearDown()

    async def test_simple_tree_view(self):
        window = await self.create_test_window()

        with window.frame:
            self._tree_view = SimpleListView()

        self._insert_list_items(10)
        self.assertEqual(len(self._tree_view.items), 10)
        self.assertEqual(len(self._tree_view.model.items), 10)

        await wait_frames(3)
        await self.finalize_test(golden_img_dir=self._golden_img_dir, golden_img_name="treeview_simple.png")

    async def test_change_selection(self):
        window = await self.create_test_window()

        selection_history = []

        def record_selection(item):
            selection_history.append(f"{item}")

        with window.frame:
            self._tree_view = SimpleListView(on_item_selected_fn=record_selection)

        self._insert_list_items(6)
        self._tree_view.selection = [1]
        self.assertEqual(len(selection_history), 1)
        self._tree_view.selection = [3]
        # when multi-selection is diabled, selection will take the last one of the list, and select will be triggered twice on the last item
        self._tree_view.selection = [0, 2, 5]
        self.assertEqual(selection_history, ['"Item 1"', '"Item 3"', '"Item 5"', '"Item 5"'])

        await wait_frames(3)
        await self.finalize_test(golden_img_dir=self._golden_img_dir, golden_img_name="treeview_selection.png")

    async def test_multi_selection(self):
        window = await self.create_test_window()

        with window.frame:
            self._tree_view = SimpleListView(multi_selection=True)

        self._insert_list_items(6)
        self._tree_view.selection = [1, 3, 5]
        self.assertEqual(len(self._tree_view.selection_items), 3)
        await wait_frames(3)
        await self.finalize_test(golden_img_dir=self._golden_img_dir, golden_img_name="treeview_multi_selection.png")

    async def test_delete_selected_items(self):
        window = await self.create_test_window()

        with window.frame:
            self._tree_view = SimpleListView(multi_selection=True)

        self._insert_list_items(10)
        self.assertEqual(self._tree_view.selection, [])

        self._tree_view.selection = [2, 4, 6]
        self._tree_view.remove_selected()
        self.assertEqual(self._tree_view.selection, [])

        self.assertEqual(len(self._tree_view.items), 7)
        await wait_frames(3)
        await self.finalize_test(golden_img_dir=self._golden_img_dir, golden_img_name="treeview_delete_selection.png")
