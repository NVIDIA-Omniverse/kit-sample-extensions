import asyncio
from pathlib import Path

import carb
import carb.settings
import omni.kit.app
import omni.kit.ui_test as ui_test
from omni.ui.tests.test_base import OmniUiTest

CURRENT_PATH = Path(__file__).parent
TEST_DATA_PATH = CURRENT_PATH.parent.parent.parent.parent.parent.parent.joinpath("data").joinpath("tests")
TEST_WIDTH = 800
TEST_HEIGHT = 600


async def wait_n_frames(frame_count):
    await asyncio.sleep(frame_count * 0.05)
    return


class TestToggle(OmniUiTest):
    # Before running each test
    async def setUp(self):
        await super().setUp()
        self._golden_img_dir = TEST_DATA_PATH.absolute().joinpath("golden_img").absolute()
        self._settings = carb.settings.get_settings()

    # After running each test
    async def tearDown(self):
        await super().tearDown()

    async def test_extension(self):
        manager = omni.kit.app.get_app().get_extension_manager()
        ext_id = "omni.kit.viewport.menubar.nav_bar_toggle"
        self.assertTrue(manager.is_extension_enabled(ext_id))
        manager.set_extension_enabled(ext_id, False)
        await ui_test.human_delay()
        self.assertFalse(manager.is_extension_enabled(ext_id))
        manager.set_extension_enabled(ext_id, True)
        await ui_test.human_delay()
        self.assertTrue(manager.is_extension_enabled(ext_id))

    async def test_toggle_button(self):
        self._settings.set_bool("/exts/omni.kit.viewport.navigation.core/isVisible", True)
        await ui_test.human_delay()
        await super().finalize_test(threshold=100, golden_img_dir=self._golden_img_dir, golden_img_name="toggled.png")

    async def test_toggle_button_not_focused(self):
        self._settings.set_bool("/exts/omni.kit.viewport.navigation.core/isVisible", False)
        await ui_test.human_delay()
        await super().finalize_test(
            threshold=100, golden_img_dir=self._golden_img_dir, golden_img_name="not-toggled.png"
        )
