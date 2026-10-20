from pathlib import Path

import carb.settings
import carb.tokens
import omni.kit.app
import omni.kit.test
import omni.timeline
from omni.kit.widget.timeline import *

from ..scripts.timeline_view_component import *


class TestTimelineView(omni.kit.test.AsyncTestCase):
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

    async def test_timeline_loaded(self):
        settings = carb.settings.get_settings()
        app_version = settings.get("/app/version")

    async def test_timeline_defaults(self):
        timeline_interface = omni.timeline.get_timeline_interface()

        timeline = TimelineView(None)
        self.assertTrue(timeline is not None)
        time: float = timeline.get_time()
        timeline_begin = timeline.get_timeline_begin()
        timeline_interface_begin = timeline_interface.get_start_time() * timeline_interface.get_time_codes_per_seconds()
        range_begin = timeline.get_range_begin()
        self.assertTrue(timeline_begin == timeline_interface_begin)
        self.assertTrue(time == 0.0)

        top = TimelineViewTopDefault(timeline)
        top.build_ui()
        timeline.set_timeline_top(top)

        bottom = TimelineViewBottomDefault(timeline)
        timeline.set_timeline_bottom(bottom)
        timeline.build_ui()
        timeline.set_range(0.0, 100.0)
        timeline.update_ui()
        timeline.update_scrubber_ui()

        x, y = timeline.get_current_mouse_coords()
        self.assertAlmostEqual(x, 0.0)
        self.assertAlmostEqual(y, 0.0)

        timeline.zoom_location = (0.0, 0.0)
        zoom_location_x, zoom_location_y = timeline.zoom_location
        self.assertAlmostEqual(zoom_location_x, 0.0)
        self.assertAlmostEqual(zoom_location_y, 0.0)

        timeline._on_built()
        self.assertIsNone(timeline.get_parent_window())
        self.assertIsNotNone(timeline.get_frame())
        self.assertIsNotNone(timeline.get_timeline_frame())
        self.assertIsNotNone(timeline.get_bottom_frame())
        self.assertIsNotNone(timeline.get_timeline_bottom_frame())
        self.assertIsNotNone(timeline.get_timeline_draw_top_frame())
        self.assertIsNotNone(timeline.get_timeline_padding())
        self.assertIsNotNone(timeline.get_view_bottom())
        self.assertIsNotNone(timeline.get_view_top())

        timeline._timeline_view_top.build_ui()
        timeline.get_scrubber().build_ui()
        for i in range(4):
            await omni.kit.app.get_app().next_update_async()
        timeline_interface.set_start_time(0.0)
        timeline_interface.set_end_time(100.0)

        zoom = timeline.zoom
        self.assertAlmostEqual(zoom, 0.0)
        new_zoom = zoom + 1
        timeline.zoom = new_zoom
        self.assertTrue(timeline._zoom == new_zoom)

        timeline.set_range(0.0, 100.0)
        timeline.update_timeline_codes(2.0)
        timeline.update_scrubber_ui()
        self.assertAlmostEqual(timeline.transform_position_to_timeline(0), 0.0)
        self.assertEqual(timeline.transform_window_to_timeline(0), 0)

        timeline.set_range_slider_visible(True)
        slider = timeline._range_slider
        self.assertTrue(slider.is_visible())
        slider._on_slider_built()
        range_slider_placer = slider._range_slider_placer

        range_slider_placer.fill_body()
        self.assertIsNotNone(range_slider_placer.get_style_type_name_override())
        self.assertIsNotNone(range_slider_placer.get_left_handle_style())
        self.assertIsNotNone(range_slider_placer.get_right_handle_style())
        range_slider_placer._update_ui()
        range_slider_placer.begin = 1
        range_slider_placer.end = 2
        range_slider_placer._update_ui()
        # simulate dragging the range slider
        range_slider_placer.right_handle.offset_x = range_slider_placer.right_handle.offset_x + 10
        range_slider_placer._begin_moved(
            range_slider_placer.left_handle, range_slider_placer.body, range_slider_placer.right_handle, None
        )
        range_slider_placer._body_moved(
            range_slider_placer.left_handle, range_slider_placer.body, range_slider_placer.right_handle, None
        )
        range_slider_placer._end_moved(
            range_slider_placer.left_handle, range_slider_placer.body, range_slider_placer.right_handle, None
        )

        timeline.set_snap_to_frame(True)
        self.assertTrue(timeline.get_snap_to_frame())
        timeline.get_scrubber().on_timeline_event(5)
        timeline.set_scrubber_disable_line(True)
        self.assertIsNotNone(timeline.get_scrubber_disable_line())
        timeline.get_scrubber().on_timeline_event(5)
        timeline.get_scrubber().destroy()
        timeline = None
