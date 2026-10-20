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

from omni.kit.viewport.utility import get_active_viewport, get_active_viewport_window


def clear_viewport_display():
    def __set_viewport_display(setting: str, enable: bool):
        viewport_api_id = get_active_viewport().id
        carb.settings.get_settings().set(f"/persistent/app/viewport/{viewport_api_id}/{setting}/visible", enable)

    __set_viewport_display("guide/grid", False)
    __set_viewport_display("guide/axis", False)
    vp = get_active_viewport_window()
    if hasattr(vp, "_find_viewport_layer"):
        layer = vp._find_viewport_layer("Viewport HUD")
        if layer:
            layer.visible = False


class TestMarkupMenuWindow(OmniUiTest):
    async def setUp(self):
        self._golden_img_dir = TEST_DATA_PATH.absolute().joinpath("golden_img").absolute()
        clear_viewport_display()

        viewport_window = get_active_viewport_window()
        await self.docked_test_window(window=viewport_window, width=TEST_WIDTH, height=TEST_HEIGHT, block_devices=False)
        for i in range(4):
            await omni.kit.app.get_app().next_update_async()

        self._button = ui_test.find("Viewport//Frame/**/Button[*].name=='Markup'")

    async def finalize_test(self, golden_img_name: str):
        await omni.kit.app.get_app().next_update_async()
        await super().finalize_test(golden_img_dir=self._golden_img_dir, golden_img_name=golden_img_name)
        await omni.kit.app.get_app().next_update_async()

    @unittest.skip("Fails golden image test, skipping for now.")  # OM-111421
    async def test_general(self):
        await self.finalize_test(golden_img_name="menubar_markup.png")

    @unittest.skip("Fails golden image test, skipping for now.")  # OM-111421
    async def test_markup_active(self):
        # # Create a new stage to show camera parameters
        # await omni.usd.get_context().new_stage_async()
        # await self._button.click()
        # for i in range(3):
        #     await omni.kit.app.get_app().next_update_async()
        # while True:
        #     creating_prompt = ui.Workspace.get_window("Please Wait")
        #     if not creating_prompt or not creating_prompt.visible:
        #         break
        #     await omni.kit.app.get_app().next_update_async()
        await self.finalize_test(golden_img_name="menubar_markup_active.png")

    async def _click_markup_icon(self, pos=Vec2(780, 60), right_click=True):
        # Enable mouse input
        app_window = omni.appwindow.get_default_app_window()
        for device in [carb.input.DeviceType.MOUSE]:
            app_window.set_input_blocking_state(device, None)

        await ui_test.emulate_mouse_move_and_click(pos, right_click=right_click)
        await omni.kit.app.get_app().next_update_async()
