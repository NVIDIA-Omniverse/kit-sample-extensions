## Copyright (c) 2021, NVIDIA CORPORATION.  All rights reserved.
##
## NVIDIA CORPORATION and its licensors retain all intellectual property
## and proprietary rights in and to this software, related documentation
## and any modifications thereto.  Any use, reproduction, disclosure or
## distribution of this software and related documentation without an express
## license agreement from NVIDIA CORPORATION is strictly prohibited.
##
import random
from pathlib import Path
from typing import Optional
from unittest.mock import patch

import carb
import omni.appwindow
import omni.kit
import omni.kit.ui_test as ui_test
import omni.ui as ui
from carb.input import DeviceType, KeyboardInput
from omni.ui.tests.test_base import OmniUiTest

from ..quicksearch_delegate import QuickSearchDelegate
from ..quicksearch_registry import QuickSearchRegistry
from ..quicksearch_window import QuickSearchWindow

CURRENT_PATH = Path(__file__).parent.joinpath("../../data")


WINDOW_WIDTH = 350
WINDOW_HEIGHT = 500


class TestModel(ui.AbstractItemModel):
    class _TestItem(ui.AbstractItem):
        """Single item of the model"""

        def __init__(self, text: str, description: str, icon: str):
            super().__init__()
            self.name_model = ui.SimpleStringModel(text)
            self.description_model = ui.SimpleStringModel(description)
            self.icon_model = ui.SimpleStringModel(icon)

        def __repr__(self):
            return f'"{self.name_model.as_string}"'

    def __init__(self, *args, **kwargs):
        super().__init__()
        self._children = [
            self._TestItem("Child 1", "Description 1", ""),
            self._TestItem("Child 2", "Description 2", ""),
            self._TestItem("Child 3", "Description 3", ""),
        ]

    def can_item_have_children(self, item):
        return False

    def get_item_children(self, item):
        """Returns all the children when the widget asks it."""
        if item is not None:
            # Since we are doing a flat list, we return the children of root only.
            # If it's not root we return.
            return []

        return self._children

    def get_item_value_model_count(self, item):
        """The number of columns"""
        return 3

    def get_item_value_model(self, item, column_id):
        """
        Return value model.
        It's the object that tracks the specific value.
        In our case we use ui.SimpleStringModel.
        """
        if column_id == 0:
            return item.name_model
        if column_id == 1:
            return item.description_model
        if column_id == 2:
            return item.icon_model

    def execute(self, item):
        pass

    def complete(self, current_value: str, item):
        pass


class TestQuicksearch(OmniUiTest):
    # Before running each test
    async def setUp(self):
        await super().setUp()
        self._golden_img_dir = Path(
            carb.tokens.get_tokens_interface().resolve("${omni.kit.window.quicksearch}/data/tests")
        )
        self._sub = QuickSearchRegistry().register_quick_search_model("Test Model 1", TestModel, None)
        self._sub1 = QuickSearchRegistry().register_quick_search_model("Test Model 2", TestModel, None)
        self._sub2 = QuickSearchRegistry().register_quick_search_model("Test Model 3", TestModel, None)
        self._window = await self.create_test_window(width=WINDOW_WIDTH, height=WINDOW_HEIGHT)

        self._quicksearch = QuickSearchWindow()
        self._quicksearch.flags = (
            ui.WINDOW_FLAGS_NO_SCROLLBAR | ui.WINDOW_FLAGS_NO_TITLE_BAR | ui.WINDOW_FLAGS_NO_RESIZE
        )
        self._quicksearch.position_x = 0
        self._quicksearch.position_y = 0
        self._quicksearch.width = WINDOW_WIDTH
        self._quicksearch.height = WINDOW_HEIGHT
        self._quicksearch.auto_resize = False

        await ui_test.wait_n_updates(50)

    # After running each test
    async def tearDown(self):
        self._quicksearch.destroy()
        self._quicksearch = None
        self._sub = None
        self._sub1 = None
        self._sub2 = None
        self._golden_img_dir = None
        await super().tearDown()

    async def test_general(self):
        await self.finalize_test(golden_img_dir=self._golden_img_dir)

    async def test_hide_show(self):
        self._quicksearch.hide()
        await ui_test.wait_n_updates(10)
        self.assertFalse(self._quicksearch.visible)
        self._quicksearch.show()
        await ui_test.wait_n_updates(10)
        await self.finalize_test(golden_img_dir=self._golden_img_dir)

    async def test_expand(self):
        quicksearch_window = ui_test.find("Quick Search")
        treeviews = quicksearch_window.find_all("**/TreeView[*].keep_expanded==False")
        # expand first item
        treeviews[1].widget.set_expanded(None, True, True)
        treeviews[1].widget.keep_expanded = True
        await ui_test.wait_n_updates(10)
        await self.finalize_test(golden_img_dir=self._golden_img_dir)

    async def test_keys(self):
        app_window = omni.appwindow.get_default_app_window()
        app_window.set_input_blocking_state(DeviceType.KEYBOARD, False)
        await ui_test.emulate_keyboard_press(KeyboardInput.DOWN)
        await ui_test.wait_n_updates(5)
        down_count = random.randint(1, 8)
        for _ in range(down_count):
            await ui_test.emulate_keyboard_press(KeyboardInput.DOWN)
            await ui_test.wait_n_updates(5)
        items = ["Child 1", "Child 2", "Child 3"]
        self.assertEqual(
            self._quicksearch._QuickSearchWindow__selected_item.name_model.as_string, items[down_count % 3]
        )
        up_count = random.randint(0, down_count - 1)
        for _ in range(up_count):
            await ui_test.emulate_keyboard_press(KeyboardInput.UP)
            await ui_test.wait_n_updates(5)
        self.assertEqual(
            self._quicksearch._QuickSearchWindow__selected_item.name_model.as_string, items[(down_count - up_count) % 3]
        )
        with patch.object(TestModel, "execute") as mock_execute, patch.object(QuickSearchWindow, "hide") as mock_hide:
            await ui_test.emulate_keyboard_press(KeyboardInput.ENTER)
            await ui_test.wait_n_updates(5)
            mock_execute.assert_called_once()
        with patch.object(TestModel, "complete") as mock_complete:
            await ui_test.emulate_keyboard_press(KeyboardInput.TAB)
            await ui_test.wait_n_updates(5)
            mock_complete.assert_called_once()
        with patch.object(QuickSearchWindow, "hide") as mock_hide:
            await ui_test.emulate_keyboard_press(KeyboardInput.ESCAPE)
            await ui_test.wait_n_updates(5)
            mock_hide.assert_called_once()
        await self.finalize_test_no_image()
