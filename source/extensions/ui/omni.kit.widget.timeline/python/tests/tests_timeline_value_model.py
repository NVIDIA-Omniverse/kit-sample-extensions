import omni.kit.app
import omni.kit.test

from ..scripts.timeline_value_model import *


class TestTimelineValueModel(omni.kit.test.AsyncTestCase):
    async def setUp(self):
        self._timeline = omni.timeline.get_timeline_interface()
        self._time_codes = self._timeline.get_time_codes_per_seconds()
        self._start_time = self._timeline.get_start_time()
        self._end_time = self._timeline.get_end_time()
        self.model = TimelineValueModel(event_type=omni.timeline.TimelineEventType.END_TIME_CHANGED)
        self.model._time_codes = 30

    async def tearDown(self):
        self.model = None
        self._timeline.set_time_codes_per_second(self._time_codes)
        self._timeline.set_start_time(self._start_time)
        self._timeline.set_end_time(self._end_time)

    async def test_initial_value(self):
        self.assertIsNotNone(self.model.get_value_as_string())
        self.assertIsNotNone(self.model.get_value_as_float())

    async def test_set_value(self):
        initial_value = self.model.get_value_as_float()
        self.model.set_value(1000.0)
        self.model.end_edit()
        self.assertNotEqual(initial_value, self.model.get_value_as_float())

    async def test_set_invalid_value(self):
        initial_value = self.model.get_value_as_float()
        self.model.set_value("invalid")
        self.model.end_edit()
        self.assertEqual(initial_value, self.model.get_value_as_float())
