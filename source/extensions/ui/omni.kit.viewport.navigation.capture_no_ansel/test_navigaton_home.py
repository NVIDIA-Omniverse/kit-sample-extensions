from pathlib import Path

import carb
import omni.kit.app
import omni.kit.ui_test as ui_test
import omni.ui as ui
from omni.kit.viewport.utility import get_active_viewport_window
from omni.ui.tests.test_base import OmniUiTest

CURRENT_PATH = Path(__file__).parent
ICON_PATH = CURRENT_PATH.parent.parent.parent.parent.parent.parent.joinpath("data/tests")
TEST_DATA_PATH = CURRENT_PATH.parent.parent.parent.parent.parent.parent.joinpath("data").joinpath("tests")
TEST_WIDTH, TEST_HEIGHT = 800, 600


async def wait_n_frames(frame_count):
    for i in range(frame_count):
        await omni.kit.app.get_app().next_update_async()


class TestBottomBar(OmniUiTest):
    # Before running each test
    async def setUp(self):
        await super().setUp()
        self._golden_img_dir = TEST_DATA_PATH.absolute().joinpath("golden_img").absolute()

        viewport_window = get_active_viewport_window()
        await self.docked_test_window(window=viewport_window, width=TEST_WIDTH, height=TEST_HEIGHT)

    # After running each test
    async def tearDown(self):
        await super().tearDown()

    async def test_general(self):
        await self.finalize_test(golden_img_name="navigation_home.png")

    async def finalize_test(self, golden_img_name: str):
        await omni.kit.app.get_app().next_update_async()
        await super().finalize_test(threshold=500, golden_img_dir=self._golden_img_dir, golden_img_name=golden_img_name)
        await omni.kit.app.get_app().next_update_async()
