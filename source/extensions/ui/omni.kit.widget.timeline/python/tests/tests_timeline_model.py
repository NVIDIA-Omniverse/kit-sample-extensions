from pathlib import Path

import carb.settings
import carb.tokens
import omni.kit.app
import omni.kit.test
import omni.ui as ui
from omni.kit.widget.timeline import *
from omni.ui.tests.test_base import OmniUiTest


class TestTimelineValueModel(omni.kit.test.AsyncTestCase):
    async def setUp(self):
        self.model = TimelineValueModel(event_type=omni.timeline.TimelineEventType.END_TIME_CHANGED)

    async def tearDown(self):
        self.model = None

    async def test_initial_value(self):
        self.assertIsNotNone(self.model.get_value_as_string())
        self.assertIsNotNone(self.model.get_value_as_float())

    async def test_set_value(self):
        initial_value = self.model.get_value_as_float()
        self.model.set_value(100.0)
        self.model.end_edit()
        self.assertNotEqual(initial_value, self.model.get_value_as_float())

    async def test_set_invalid_value(self):
        initial_value = self.model.get_value_as_float()
        self.model.set_value("invalid")
        self.model.end_edit()
        self.assertEqual(initial_value, self.model.get_value_as_float())

    async def test_clamped_value(self):
        self.model.set_value(1000000.0)
        self.model.end_edit()
        self.assertEqual(self.model.get_value_as_float(), 999999 * self.model._time_codes)

    async def test_timeline_event(self):
        initial_value = self.model.get_value_as_float()
        _timeline = omni.timeline.get_timeline_interface()
        _timeline.set_end_time(200.0)
        self.assertNotEqual(initial_value, self.model.get_value_as_float())
