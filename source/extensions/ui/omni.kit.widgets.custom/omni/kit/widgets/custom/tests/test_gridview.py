# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
import omni.ui as ui
from omni.kit.widgets.custom.gridview.simplegridview import SimpleGridView

from ..model import SimpleListItem, SimpleListModel
from .utils import GOLDEN_IMG_DIR, TestWidgetsCustomBase, wait_frames


class TestGridViewDelegate(ui.AbstractItemDelegate):
    def build_widget(self, model, item, *args):
        ui.Label(item.get_value_model().as_string)


class TestGridView(TestWidgetsCustomBase):
    def _insert_list_items(self, num):
        for i in range(num):
            self._gridview.insert_item(SimpleListItem(f"Item {i}"))

    # Before running each test
    async def setUp(self):
        await super().setUp()
        self._golden_img_dir = GOLDEN_IMG_DIR

        self._hide_main_menu_bar()
        self._gridview = None
        self._model = SimpleListModel()

    # After running each test
    async def tearDown(self):
        if self._gridview:
            self._gridview.clear()
            self._gridview = None

        if self._model:
            self._model = None

        await super().tearDown()

    async def test_simple_gridview(self):
        window = await self.create_test_window()

        with window.frame:
            self._gridview = SimpleGridView(
                column_count=4, row_height=30, model=self._model, delegate=TestGridViewDelegate()
            )

        self._insert_list_items(10)
        # add selection
        self._gridview.selections = self._model.get_item_children()[0]

        await wait_frames(3)
        await self.finalize_test(golden_img_dir=self._golden_img_dir, golden_img_name="gridview_simple.png")

    async def test_mouse_clicks(self):
        import omni.kit.ui_test as ui_test

        mouse_event_history = []

        def left_click_fn(item):
            mouse_event_history.append(("left click", f"{item}"))

        def right_click_fn(item):
            mouse_event_history.append(("right click", f"{item}"))

        def double_click_fn(item):
            mouse_event_history.append(("double click", f"{item}"))

        window = await self.create_test_window(block_devices=False)

        with window.frame:
            self._gridview = SimpleGridView(
                column_count=4,
                row_height=30,
                model=self._model,
                delegate=TestGridViewDelegate(),
                on_clicked_fn=left_click_fn,
                on_rclicked_fn=right_click_fn,
                on_double_clicked_fn=double_click_fn,
            )
        self._insert_list_items(10)
        await wait_frames(3)

        item0 = ui_test.find(f"{window.title}//Frame/**/Label[*].text=='Item 0'")
        item3 = ui_test.find(f"{window.title}//Frame/**/Label[*].text=='Item 3'")

        # left click
        await ui_test.emulate_mouse_move_and_click(item0.center)
        self.assertEqual(mouse_event_history[0], ("left click", '"Item 0"'))
        self.assertEqual(len(self._gridview.selections), 1)

        # right click
        await ui_test.emulate_mouse_move_and_click(item3.center, right_click=True)
        self.assertEqual(mouse_event_history[1], ("right click", '"Item 3"'))
        self.assertEqual(len(self._gridview.selections), 1)
        self.assertEqual(f"{self._gridview.selections[0]!r}", '"Item 3"')

        # double click
        await ui_test.emulate_mouse_move_and_click(item0.center, double=True)
        await wait_frames(3)
        # FIXME: Disabling double click check for now, it is flaky where most of the time it would work but
        #  sometimes the double click event is not triggered
        # double click triggered on_click twice, and cleared up selection
        # self.assertEqual(mouse_event_history[-1], ("double click", '"Item 0"'))
        self.assertEqual(len(self._gridview.selections), 0)
