import asyncio
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
TEST_DATA_PATH = CURRENT_PATH.parent.parent.parent.parent.parent.parent.parent.joinpath("data").joinpath("tests")
TEST_WIDTH, TEST_HEIGHT = 800, 300
SETTING_COMPARE_COLDEN = "/app.navigation.test/golden_compare"


class TestMarkupMenuWindow(OmniUiTest):
    async def setUp(self):
        self._golden_img_dir = TEST_DATA_PATH.absolute().joinpath("golden_img").absolute()
        self._settings = carb.settings.get_settings()
        self._golden_compare = self._settings.get(SETTING_COMPARE_COLDEN)

        viewport_window = get_active_viewport_window()
        await self.docked_test_window(window=viewport_window, width=TEST_WIDTH, height=TEST_HEIGHT, block_devices=False)
        for i in range(4):
            await omni.kit.app.get_app().next_update_async()

        self._button = ui_test.find("Viewport//Frame/**/Button[*].name=='look'")

    async def finalize_test(self, golden_img_name: str):
        if self._golden_compare:
            await omni.kit.app.get_app().next_update_async()
            await super().finalize_test(
                threshold=500, golden_img_dir=self._golden_img_dir, golden_img_name=golden_img_name
            )
            await omni.kit.app.get_app().next_update_async()
        else:
            self.assertTrue(self._button)

    async def test_general(self):
        await self.finalize_test(golden_img_name="navigation_view.png")

    # async def test_waypoint_active(self):
    #     # Create a new stage to show camera parameters
    #     await omni.usd.get_context().new_stage_async()
    #     await self._button.click()
    #     for i in range(3):
    #         await omni.kit.app.get_app().next_update_async()
    #     while True:
    #         creating_prompt = ui.Workspace.get_window("Please Wait")
    #         if not creating_prompt or not creating_prompt.visible:
    #             break
    #         await omni.kit.app.get_app().next_update_async()
    #     await self.finalize_test(golden_img_name="navigation_view_active.png")
