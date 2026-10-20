import asyncio
from pathlib import Path

import carb
import omni.kit.app
import omni.kit.ui_test as ui_test
import omni.ui as ui
from omni.kit.viewport.menubar.core import get_instance as get_menubar_instance
from omni.kit.viewport.utility import get_active_viewport_window
from omni.ui.tests.test_base import OmniUiTest

from .. import get_bottombar_name
from .button import MenubarButton

CURRENT_PATH = Path(__file__).parent
ICON_PATH = CURRENT_PATH.parent.parent.parent.parent.parent.parent.joinpath("data/tests")
SETTINGS_ROOT = "/exts/omni.kit.viewport.menubar/bottom"
TEST_DATA_PATH = CURRENT_PATH.parent.parent.parent.parent.parent.parent.joinpath("data").joinpath("tests")
TEST_WIDTH, TEST_HEIGHT = 800, 600

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


async def wait_n_frames(frame_count):
    for i in range(frame_count):
        await omni.kit.app.get_app().next_update_async()


class TestBottomBar(OmniUiTest):

    # Before running each test
    async def setUp(self):
        await super().setUp()
        self._golden_img_dir = TEST_DATA_PATH.absolute().joinpath("golden_img").absolute()
        clear_viewport_display()

        viewport_window = get_active_viewport_window()
        await self.docked_test_window(window=viewport_window, width=TEST_WIDTH, height=TEST_HEIGHT)

        bottombar_name = get_bottombar_name()
        self._bottombar = get_menubar_instance().get_menubar(bottombar_name)

    # After running each test
    async def tearDown(self):
        await super().tearDown()

    async def test_general(self):
        settings = carb.settings.get_settings()
        settings.set_int(f"{SETTINGS_ROOT}/left", -100)
        settings.set_int(f"{SETTINGS_ROOT}/right", 100)

        # Add 2 image buttons, left and right
        with self._bottombar:
            self._left = MenubarButton("left", f"{SETTINGS_ROOT}/left", f"{ICON_PATH}/left.svg")
            self._right = MenubarButton("right", f"{SETTINGS_ROOT}/right", f"{ICON_PATH}/right.svg")

        await self.finalize_test(golden_img_name="menubar_bottom.png")

    async def finalize_test(self, golden_img_name: str):
        await omni.kit.app.get_app().next_update_async()
        await super().finalize_test(golden_img_dir=self._golden_img_dir, golden_img_name=golden_img_name)
        await omni.kit.app.get_app().next_update_async()
