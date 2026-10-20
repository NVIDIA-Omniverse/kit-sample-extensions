import asyncio
from pathlib import Path, PurePath

import carb
import carb.settings
import omni.kit.app
import omni.kit.ui_test as ui_test
import omni.ui as ui
from omni.kit.test_helpers_gfx.compare_utils import capture_and_compare
from omni.kit.ui_test import Vec2
from omni.kit.viewport.utility import get_active_viewport_window
from omni.kit.viewport.window import get_viewport_window_instances
from omni.ui.tests.test_base import OmniUiTest

from ..button import TimelineButton

CURRENT_PATH = Path(__file__).parent
TEST_DATA_PATH = CURRENT_PATH.parent.parent.parent.parent.parent.parent.joinpath("data").joinpath("tests")
TEST_WIDTH = 800
TEST_HEIGHT = 600

SETTINGS_PATH_TIMELINE_TOGGLE = "/exts/omni.kit.timeline.minibar/visible"

from omni.kit.viewport.utility import get_active_viewport, get_active_viewport_window


async def wait_n_frames(frame_count):
    await asyncio.sleep(frame_count * 0.05)
    return


class TestTimelineButton(OmniUiTest):
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
        ext_id = "omni.kit.viewport.menubar.timeline"
        self.assertTrue(ext_id)
        self.assertTrue(manager.is_extension_enabled(ext_id))
        manager.set_extension_enabled(ext_id, False)
        await ui_test.human_delay()
        self.assertTrue(not manager.is_extension_enabled(ext_id))
        manager.set_extension_enabled(ext_id, True)
        await ui_test.human_delay()
        self.assertTrue(manager.is_extension_enabled(ext_id))

    async def test_timeline_button_on(self):
        self._settings.set_bool(SETTINGS_PATH_TIMELINE_TOGGLE, True)
        await ui_test.human_delay()
        await super().finalize_test(
            threshold=100, golden_img_dir=self._golden_img_dir, golden_img_name="timeline-on.png"
        )

    async def test_toggle_button_off(self):
        self._settings.set_bool(SETTINGS_PATH_TIMELINE_TOGGLE, False)
        await ui_test.human_delay()
        await super().finalize_test(
            threshold=100, golden_img_dir=self._golden_img_dir, golden_img_name="timeline-off.png"
        )
