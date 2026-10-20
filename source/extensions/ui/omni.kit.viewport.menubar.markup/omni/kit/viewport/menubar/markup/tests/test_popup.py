import asyncio
import unittest
from pathlib import Path
from re import I

import carb.input
import omni.kit.app
import omni.kit.ui_test as ui_test
import omni.ui as ui
import omni.usd
from omni.kit.ui_test import Vec2
from omni.kit.viewport.utility import get_active_viewport_window
from omni.ui.tests.test_base import OmniUiTest

CURRENT_PATH = Path(__file__).parent
TEST_DATA_PATH = CURRENT_PATH.parent.parent.parent.parent.parent.parent.joinpath("data").joinpath("tests")
TEST_WIDTH, TEST_HEIGHT = 800, 300


class TestMarkupMenuPopup(OmniUiTest):
    async def setUp(self):
        self._golden_img_dir = TEST_DATA_PATH.absolute().joinpath("golden_img").absolute()

        viewport_window = get_active_viewport_window()
        await self.docked_test_window(window=viewport_window, width=TEST_WIDTH, height=TEST_HEIGHT, block_devices=False)
        for i in range(4):
            await omni.kit.app.get_app().next_update_async()

        self._button = ui_test.find("Viewport//Frame/**/Button[*].name=='Markup'")

    @unittest.skip("Fails golden image test, skipping for now.")  # OM-111421
    async def test_popup(self):
        await self._button.right_click()
        await self.finalize_test(golden_img_name="menubar_markup_popup.png")

    async def finalize_test(self, golden_img_name: str):
        await omni.kit.app.get_app().next_update_async()
        await super().finalize_test(golden_img_dir=self._golden_img_dir, golden_img_name=golden_img_name)
        await omni.kit.app.get_app().next_update_async()
