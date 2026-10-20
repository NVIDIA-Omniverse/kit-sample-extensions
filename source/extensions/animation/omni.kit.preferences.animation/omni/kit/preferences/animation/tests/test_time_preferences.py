from pathlib import Path
from unittest import mock

from omni.kit.preferences.animation import (
    FrameRate,
    TimeDisplay,
    g_time_display_model,
    get_auto_key_all_xform,
    get_compensate_play_dely_in_secs,
    get_frame_rate,
    get_play_every_frame,
    get_snap_to_frame,
    get_ticks_per_frame,
    get_time_code_range,
    get_time_display,
    get_use_fixed_time_stepping,
    set_auto_key_all_xform,
    set_compensate_play_dely_in_secs,
    set_frame_rate,
    set_play_every_frame,
    set_snap_to_frame,
    set_ticks_per_frame,
    set_time_code_range,
    set_time_display,
    set_use_fixed_time_stepping,
)
from omni.kit.test.async_unittest import AsyncTestCase
from omni.kit.window.preferences import get_page_list


class TestTimePreferences(AsyncTestCase):
    async def test_animation_preferences_page(self):
        page_titles = [page.get_title() for page in get_page_list()]
        self.assertTrue("Animation" in page_titles)

    async def test_time_preferences_setter(self):
        self.assertRaises(ValueError, set_time_display, "foo")

        self.assertIsNone(set_time_display("frames"))
        self.assertEqual(get_time_display(), TimeDisplay.FRAMES)

        self.assertIsNone(set_time_display("FRAMES"))
        self.assertEqual(get_time_display(), TimeDisplay.FRAMES)

        self.assertIsNone(set_time_display("Seconds"))
        self.assertEqual(get_time_display(), TimeDisplay.SECONDS)

        self.assertIsNone(set_time_display("SMPTE"))
        self.assertEqual(get_time_display(), TimeDisplay.SMPTE)

    async def test_time_display_enum(self):
        self.assertRaises(ValueError, TimeDisplay.from_string, "foo")
        self.assertEqual(TimeDisplay.FRAMES, TimeDisplay.from_string("frames"))
        self.assertEqual(TimeDisplay.SECONDS, TimeDisplay.from_string("seconds"))
        self.assertEqual(TimeDisplay.SMPTE, TimeDisplay.from_string("smpte"))

    async def test_time_display_model(self):
        self.assertIsNotNone(g_time_display_model)
        self.assertRaises(ValueError, g_time_display_model.set_value, "foo")

        # set model updates time display
        set_time_display("seconds")  # set initial value
        self.assertEqual(get_time_display(), TimeDisplay.SECONDS)

        self.assertIsNone(g_time_display_model.set_value("frames"))  # change with model
        self.assertEqual(get_time_display(), TimeDisplay.FRAMES)

        set_time_display("seconds")
        self.assertTrue(g_time_display_model.as_string == TimeDisplay.SECONDS)

        _mock = mock.Mock()
        sub = g_time_display_model.subscribe_value_changed_fn(_mock)
        set_time_display(TimeDisplay.FRAMES)
        _mock.assert_called_once()

    async def test_frame_rate_access(self):
        self.assertRaises(ValueError, set_frame_rate, 0)

        self.assertIsNone(set_frame_rate(24))
        self.assertEqual(get_frame_rate(), FrameRate.TWENTY_FOUR.value)

        self.assertIsNone(set_frame_rate(29.97))
        self.assertEqual(get_frame_rate(), FrameRate.TWENTY_NINE_POINT_NINE_SEVEN.value)

        self.assertIsNone(set_frame_rate(30))
        self.assertEqual(get_frame_rate(), FrameRate.THIRTY.value)

        self.assertIsNone(set_frame_rate(60))
        self.assertEqual(get_frame_rate(), FrameRate.SIXTY.value)

        self.assertIsNone(set_frame_rate(120))
        self.assertEqual(get_frame_rate(), FrameRate.ONE_HUNDRED_TWENTY.value)

    async def test_auto_key_all_xform_access(self):
        self.assertIsNone(set_auto_key_all_xform(True))
        self.assertEqual(get_auto_key_all_xform(), True)

        self.assertIsNone(set_auto_key_all_xform(False))
        self.assertEqual(get_auto_key_all_xform(), False)

    async def test_time_code_range_access(self):
        self.assertIsNone(set_time_code_range(-1, 101))
        self.assertEqual(get_time_code_range(), [-1, 101])

        self.assertIsNone(set_time_code_range(0, 100))
        self.assertEqual(get_time_code_range(), [0, 100])

    async def test_use_fixed_time_stepping_access(self):
        self.assertIsNone(set_use_fixed_time_stepping(True))
        self.assertEqual(get_use_fixed_time_stepping(), True)

        self.assertIsNone(set_use_fixed_time_stepping(False))
        self.assertEqual(get_use_fixed_time_stepping(), False)

    async def test_compensate_play_dely_in_secs_access(self):
        self.assertRaises(ValueError, set_compensate_play_dely_in_secs, -1)

        self.assertIsNone(set_compensate_play_dely_in_secs(0))
        self.assertEqual(get_compensate_play_dely_in_secs(), 0)

        self.assertIsNone(set_compensate_play_dely_in_secs(1.5))
        self.assertEqual(get_compensate_play_dely_in_secs(), 1.5)

    async def test_snap_to_frame_access(self):
        self.assertIsNone(set_snap_to_frame(True))
        self.assertEqual(get_snap_to_frame(), True)

        self.assertIsNone(set_snap_to_frame(False))
        self.assertEqual(get_snap_to_frame(), False)

    async def test_play_every_frame(self):
        self.assertIsNone(set_play_every_frame(True))
        self.assertEqual(get_play_every_frame(), True)

        self.assertIsNone(set_play_every_frame(False))
        self.assertEqual(get_play_every_frame(), False)

    async def test_ticks_per_frame(self):
        self.assertRaises(ValueError, set_ticks_per_frame, 0)
        self.assertRaises(ValueError, set_ticks_per_frame, 31)
        self.assertRaises(ValueError, set_ticks_per_frame, 0.5)

        self.assertIsNone(set_ticks_per_frame(2))
        self.assertEqual(get_ticks_per_frame(), 2)

        self.assertIsNone(set_ticks_per_frame(1))
        self.assertEqual(get_ticks_per_frame(), 1)
