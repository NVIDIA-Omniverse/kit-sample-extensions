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
from typing import List, Tuple

import carb.input
import omni.kit.app
import omni.kit.test
import omni.kit.ui_test as ui_test
from carb.input import KEYBOARD_MODIFIER_FLAG_SHIFT
from omni.kit.browser.core import CategoryItem, DetailDelegate, DetailItem
from omni.kit.browser.core.models import DetailItem
from omni.ui.tests.test_base import OmniUiTest

from ..models import SingleLevelWrapper
from ..widgets.style import UI_STYLES
from ..widgets.thumbnail_view import ThumbnailView
from .common import SimpleBrowserModel

CURRENT_PATH = Path(__file__).parent
TEST_DATA_PATH = CURRENT_PATH.parent.parent.parent.parent.parent.joinpath("data").joinpath("tests")


class TestDelegate(DetailDelegate):
    def on_drag(self, item: DetailItem) -> str:
        return item.name


class TestThumbnailView(OmniUiTest):
    # Before running each test
    async def setUp(self):
        await super().setUp()

        self._golden_img_dir = TEST_DATA_PATH.absolute().joinpath("golden_img").absolute()
        self._browser_model = SimpleBrowserModel()
        self._detail_model = SingleLevelWrapper()
        colleciton_items = self._browser_model.get_item_children(None)
        category_items = self._browser_model.get_item_children(colleciton_items[0])
        self._detail_model.set_sources(self._browser_model, category_items[0])

        self._window = await self.create_test_window(width=500, height=600, block_devices=False)
        self._window.frame.set_style(UI_STYLES)
        self._delegate = TestDelegate(model=self._browser_model)
        with self._window.frame:
            self._view = ThumbnailView(self._detail_model, delegate=self._delegate)

        for _ in range(20):
            await omni.kit.app.get_app().next_update_async()

    # After running each test
    async def tearDown(self):
        self._view.destroy()
        await super().tearDown()

    async def test_general(self):
        """Testing general look of ThumbnailView"""
        # Wait for icons loaded
        await asyncio.sleep(5)

        self.assertEqual(self._view.model, self._detail_model)
        self.assertEqual(self._view.selection, [])

        await self.finalize_test(golden_img_dir=self._golden_img_dir, golden_img_name="thumbnailview_general.png")

    async def test_padding(self):
        self.assertEqual(self._view.thumbnail_padding_width, 1)
        self.assertEqual(self._view.thumbnail_padding_height, 1)

        self._view.thumbnail_padding_width = 10
        self._view.thumbnail_padding_height = 20

        for _ in range(10):
            await omni.kit.app.get_app().next_update_async()
        await self.finalize_test(golden_img_dir=self._golden_img_dir, golden_img_name="thumbnailview_padding.png")

    async def test_selection(self):
        detail_items = self._detail_model.get_item_children()
        pos = self.__get_item_position(detail_items[0])
        await ui_test.emulate_mouse_move_and_click(pos)
        self.assertEqual(self._view.selection, [detail_items[0]])

        # CTRL + CLICK to additional selection
        await ui_test.input.emulate_keyboard(
            carb.input.KeyboardEventType.KEY_PRESS,
            carb.input.KeyboardInput.LEFT_CONTROL,
            carb.input.KEYBOARD_MODIFIER_FLAG_CONTROL,
        )
        await omni.kit.app.get_app().next_update_async()
        pos = self.__get_item_position(detail_items[3])
        await ui_test.emulate_mouse_move_and_click(pos)
        self.assertEqual(self._view.selection, [detail_items[0], detail_items[3]])

        # CTRL + CLICK again to remove additional selection
        await ui_test.emulate_mouse_move_and_click(pos)
        self.assertEqual(self._view.selection, [detail_items[0]])
        await ui_test.input.emulate_keyboard(
            carb.input.KeyboardEventType.KEY_RELEASE,
            carb.input.KeyboardInput.LEFT_CONTROL,
            carb.input.KEYBOARD_MODIFIER_FLAG_CONTROL,
        )

        # SHIFT + CLICK to multi selection
        await ui_test.input.emulate_keyboard(
            carb.input.KeyboardEventType.KEY_PRESS,
            carb.input.KeyboardInput.LEFT_SHIFT,
            carb.input.KEYBOARD_MODIFIER_FLAG_SHIFT,
        )
        await omni.kit.app.get_app().next_update_async()
        pos = self.__get_item_position(detail_items[4])
        await ui_test.emulate_mouse_move_and_click(pos)
        self.assertEqual(
            self._view.selection, [detail_items[4], detail_items[3], detail_items[2], detail_items[1], detail_items[0]]
        )
        await ui_test.input.emulate_keyboard(
            carb.input.KeyboardEventType.KEY_RELEASE,
            carb.input.KeyboardInput.LEFT_SHIFT,
            carb.input.KEYBOARD_MODIFIER_FLAG_SHIFT,
        )

        # Right click on another item to change selection
        pos = self.__get_item_position(detail_items[5])
        await ui_test.emulate_mouse_move_and_click(pos, right_click=True)
        self.assertEqual(self._view.selection, [detail_items[5]])

        # Clear selection
        self._view.selection = []
        self.assertEqual(self._view.selection, [])

        await self.finalize_test_no_image()

    async def test_on_drag(self):

        def __on_selection_changed(selections: List[DetailItem]):
            self.__selections = selections

        self._view.set_selection_changed_fn(__on_selection_changed)
        detail_items = self._detail_model.get_item_children()

        self._view.selection = [detail_items[0], detail_items[3]]
        self.assertEqual(self.__selections, self._view.selection)

        # Drag item in selection
        drag_url = self._view.on_drag(detail_items[0])
        self.assertEqual(drag_url, "\n".join([item.name for item in self._view.selection]))

        # Drag item out of selection
        drag_url = self._view.on_drag(detail_items[1])
        self.assertEqual(drag_url, detail_items[1].name)

        self._view.set_selection_changed_fn(None)

        await self.finalize_test_no_image()

    async def test_item_execute(self):
        detail_items = self._detail_model.get_item_children()
        double_click_item = detail_items[2]
        pos = self.__get_item_position(double_click_item)
        await ui_test.emulate_mouse_move_and_click(pos, double=True)
        self.assertEqual(self._browser_model.execute_item, double_click_item)
        await self.finalize_test_no_image()

    async def test_item_changed(self):
        detail_items = self._detail_model.get_item_children()
        item = detail_items[2]
        item.name_model.set_value("NEW TEXT")
        self._delegate.item_changed(self._browser_model, item)
        for _ in range(10):
            await omni.kit.app.get_app().next_update_async()
        await self.finalize_test(golden_img_dir=self._golden_img_dir, golden_img_name="thumbnailview_item_changed.png")

    async def test_shift_selecting_across_a_tile_that_is_not_built_yet(self):
        """
        A range selection may span a tile that has not been created.

        Tiles are built a few milliseconds at a time, so between frames an item can be in the model
        and on nobody's screen. The range walk used to index the frame table directly and raised
        KeyError on such an item, losing the whole selection - the two neighbouring helpers already
        tolerated it, which is why nothing else showed the fault.
        """
        items = self._detail_model.get_item_children()
        pending = items[2]
        # The state a budgeted build leaves behind between frames.
        self._view._delegates.pop(pending)

        self._view.selection = [items[0]]
        self._view._on_click(KEYBOARD_MODIFIER_FLAG_SHIFT, items[4])

        self.assertIn(pending, self._view.selection, "an unbuilt tile was dropped from the range")
        self.assertEqual(len(self._view.selection), 5, "the range did not cover every item in it")

    async def test_clearing_the_view_leaves_it_able_to_rebuild(self):
        """
        `clear()` is public, and has to leave the accounting agreeing with the screen.

        The incremental build skips a notification whose children it has already built. Clearing
        the widgets without clearing that record means the next notification - the same items,
        which is what a redisplay looks like - is read as "already shown", and the view stays
        empty for as long as the contents do not change.
        """
        items = self._detail_model.get_item_children()
        self.assertTrue(self._view._delegates, "nothing was built to begin with")

        self._view.clear()
        self._view._model_item_changed(None, None)
        for _ in range(20):
            await omni.kit.app.get_app().next_update_async()

        self.assertEqual(
            sorted(id(i) for i in self._view._delegates),
            sorted(id(i) for i in items),
            "the tiles were never built again after clear()",
        )
        await self.finalize_test_no_image()

    def __get_item_position(self, item: DetailItem) -> ui_test.Vec2:
        frame = self._view._delegates[item]
        return ui_test.Vec2(
            frame.screen_position_x + frame.computed_content_width / 2,
            frame.screen_position_y + frame.computed_content_height / 2,
        )
