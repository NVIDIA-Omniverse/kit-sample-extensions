from pathlib import Path

import carb.settings
import carb.tokens
import omni.kit.app
import omni.kit.test
import omni.ui as ui
from omni.kit.widget.timeline import *


class MockPos:
    def __init__(self, pos):
        self.value = pos


class TestTimelineScrubber(omni.kit.test.AsyncTestCase):
    async def setUp(self):
        extension_root_folder = Path(
            omni.kit.app.get_app().get_extension_manager().get_extension_path_by_module(__name__)
        )
        self._GOLDEN_IMG_DIR = extension_root_folder.joinpath("data/golden_img")
        self._MAP_DIR = extension_root_folder.joinpath("data/map")
        # hide display options
        settings = carb.settings.get_settings()
        display_op_setting_path = "/persistent/app/viewport/displayOptions"
        settings.set_int(display_op_setting_path, 0)

    async def test_timeline_scrubber(self):
        timeline = TimelineView(None)
        self.assertTrue(timeline is not None)
        time: float = timeline.get_time()
        timeline.build_ui()
        timeline.update_ui()
        timeline._on_built()
        timeline.update_scrubber_ui()
        # wait the delay build
        for i in range(4):
            await omni.kit.app.get_app().next_update_async()
        scrubber = timeline.get_scrubber()
        scrubber.enabled = True
        self.assertTrue(scrubber.enabled)
        scrubber.update_ui()

        self.assertAlmostEqual(scrubber.transform_scrubber_position_to_timeline(0), 0)

        # simulate a mouse drag on pill
        scrubber._on_mouse_pressed(0, 0, 0, 0)
        self.assertTrue(scrubber._left_button_down)
        scrubber._on_mouse_released(0, 0, 0, 0)
        self.assertFalse(scrubber._left_button_down)

        scrubber._on_mouse_line_pressed(0, 0, 0, 0)
        self.assertTrue(scrubber._left_button_down)
        scrubber._on_pill_offset_x_changed(MockPos(10))
        scrubber._on_mouse_line_released(0, 0, 0, 0)
        self.assertFalse(scrubber._left_button_down)

        scrubber.destroy()
        scrubber = None
        timeline.destroy()
