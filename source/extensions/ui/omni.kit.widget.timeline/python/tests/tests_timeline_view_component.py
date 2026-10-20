import omni.kit.app
import omni.kit.test

from ..scripts.timeline_view import TimelineView
from ..scripts.timeline_view_component import *


class TestTimelineViewRoot(omni.kit.test.AsyncTestCase):
    async def setUp(self):
        pass

    async def tearDown(self):
        pass

    async def test_view_root(self):
        view_root = TimelineViewRoot()
        self.assertIsNotNone(view_root)
        view_root.enable_scrubber(True)
        view_root.zoom = 1
        self.assertAlmostEqual(view_root.zoom, 1.0)
        view_root.zoom_location = (0, 0)
        self.assertAlmostEqual(view_root.zoom_location[0], 0.0)
        mx, my = view_root.get_current_mouse_coords()
        self.assertAlmostEqual(mx, 0.0)
        self.assertAlmostEqual(my, 0.0)
        self.assertAlmostEqual(view_root.transform_timeline_to_position(0.0), 0.0)


class TestTimelineViewElement(omni.kit.test.AsyncTestCase):
    async def setUp(self):
        pass

    async def tearDown(self):
        pass

    async def test_view_element(self):
        view_root = TimelineViewRoot()
        view_element = TimelineViewElement(view_root)
        self.assertIsNotNone(view_element)
        view_element.on_zoom(1.0)
        view_element.on_zoom_width(1.0)
        view_element.on_zoom_height(1.0)
        view_element.enable_scrubber(True)
        view_element.zoom = 1
        self.assertAlmostEqual(view_element.zoom, 1.0)
        view_element.zoom_location = (0, 0)
        self.assertAlmostEqual(view_element.zoom_location[0], 0.0)
        view_element.zoom_step(0.1)
        with self.assertRaises(Exception):
            view_element.set_x(10)
        with self.assertRaises(Exception):
            view_element.set_y(10)
        with self.assertRaises(Exception):
            view_element.get_x()
        with self.assertRaises(Exception):
            view_element.get_y()

    async def test_view_element_top_default(self):
        view_root = TimelineView(None)
        view_element = TimelineViewTopPlacerDefault(view_root)
        self.assertIsNotNone(view_element)
        view_element.build_ui()
        self.assertIsNotNone(view_element.get_bottom_frame())
        self.assertIsNotNone(view_element.get_top_frame())
        view_element.set_x(10)
        view_element.set_y(10)
        self.assertAlmostEqual(view_element.get_frame_x(), -10.0)
        self.assertAlmostEqual(view_element.get_x(), 10)
