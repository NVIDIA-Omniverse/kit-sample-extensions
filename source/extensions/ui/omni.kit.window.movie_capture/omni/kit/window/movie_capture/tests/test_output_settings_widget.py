import omni.kit.test
from omni.kit.window.movie_capture import output_settings_widget


class TestOutputFolderSettings(omni.kit.test.AsyncTestCase):

    async def setUp(self) -> None:
        super().setUp()
        self._widget = output_settings_widget.OutputSettingsWidget(None, None)
        self._widget._build_ui_output_path()

    async def tearDown(self) -> None:
        self._widget.destroy()
        super().tearDown()

    async def test_strips_output(self):
        self._widget._ui_kit_path.model.set_value("/home/user/")
        self.assertEquals("/home/user", self._widget._sanitize_output_folder())


class TestOutputSettingsWidgetTeardown(omni.kit.test.AsyncTestCase):
    """Regression tests for NVBug 5856171.

    destroy() must release every carb.settings observer registered in __init__
    (tracked in _setting_subs); a leaked one outlives the widget and aborts with
    SIGABRT when carb.dictionary unloads. Asserting on the registry covers any
    newly added subscription automatically.
    """

    async def test_destroy_releases_every_settings_subscription(self):
        widget = output_settings_widget.OutputSettingsWidget(None, None)
        self.assertTrue(widget._setting_subs, msg="__init__ registered no settings observers.")

        widget.destroy()

        self.assertEqual(widget._setting_subs, [], msg="destroy() left settings observers registered (NVBug 5856171).")

    async def test_destroy_is_idempotent(self):
        # Reachable from both extension shutdown and manual window close, so calling it
        # twice must not raise or double-unsubscribe.
        widget = output_settings_widget.OutputSettingsWidget(None, None)
        widget.destroy()
        widget.destroy()
        self.assertEqual(widget._setting_subs, [])

    async def test_destroy_safe_after_partial_init(self):
        # If __init__ raised before its attributes were set, destroy() must still not
        # raise. Build an uninitialized instance via __new__ (no __init__) so no real
        # carb.settings subscriptions are created -- constructing the full widget and
        # deleting _setting_subs would orphan the live subscriptions and reintroduce
        # the very leak this MR fixes (NVBug 5856171).
        widget = output_settings_widget.OutputSettingsWidget.__new__(output_settings_widget.OutputSettingsWidget)
        widget.destroy()  # must not raise even though __init__ never ran
        self.assertEqual(widget._setting_subs, [])


class TestBatchSettings(omni.kit.test.AsyncTestCase):

    async def setUp(self) -> None:
        super().setUp()
        self._widget = output_settings_widget.OutputSettingsWidget(None, None)

    async def tearDown(self) -> None:
        self._widget.destroy()
        super().tearDown()

    async def test_valid_even_batch(self):
        start_frame = 201
        end_frame = 500
        batch_count = 10

        batches = self._widget._prepare_batches(start_frame, end_frame, batch_count)
        self.assertEqual(len(batches), batch_count)

        first_batch = batches[0]
        final_batch = batches[-1]

        self.assertEqual(first_batch[0], start_frame)
        self.assertEqual(final_batch[1], end_frame)

    async def test_valid_even_batch_2(self):
        start_frame = 1
        end_frame = 100
        batch_count = 4

        batches = self._widget._prepare_batches(start_frame, end_frame, batch_count)
        self.assertEqual(len(batches), batch_count)

        first_batch = batches[0]
        final_batch = batches[-1]

        self.assertEqual(first_batch[0], start_frame)
        self.assertEqual(final_batch[0], 76)
        self.assertEqual(final_batch[1], end_frame)

    async def test_valid_no_batch(self):
        start_frame = 200
        end_frame = 500
        batch_count = 0

        batches = self._widget._prepare_batches(start_frame, end_frame, batch_count)
        self.assertEqual(len(batches), 1)

        first_batch = batches[0]
        final_batch = batches[-1]

        self.assertEqual(first_batch[0], start_frame)
        self.assertEqual(final_batch[1], end_frame)

    async def test_valid_single_batch(self):
        start_frame = 200
        end_frame = 500
        batch_count = 1

        batches = self._widget._prepare_batches(start_frame, end_frame, batch_count)
        self.assertEqual(len(batches), batch_count)

        first_batch = batches[0]
        final_batch = batches[-1]

        self.assertEqual(first_batch[0], start_frame)
        self.assertEqual(final_batch[1], end_frame)

    async def test_valid_uneven_batch(self):

        start_frame = 200
        end_frame = 500
        batch_count = 17

        batches = self._widget._prepare_batches(start_frame, end_frame, batch_count)
        self.assertEqual(len(batches), batch_count)

        first_batch = batches[0]
        final_batch = batches[-1]

        self.assertEqual(first_batch[0], start_frame)
        self.assertEqual(final_batch[1], end_frame)

    async def test_valid_uneven_batch_2(self):

        start_frame = 0
        end_frame = 109
        batch_count = 53

        batches = self._widget._prepare_batches(start_frame, end_frame, batch_count)
        self.assertEqual(len(batches), batch_count)

        first_batch = batches[0]
        mid_batch = batches[23]
        mid_batch_48 = batches[48]
        mid_batch_49 = batches[49]
        final_batch = batches[-1]

        # expect batch 0 - 48 have 2 frames each, and batch 49 - 52(the last one) has 3 frames each
        self.assertEqual(first_batch[0], start_frame)
        self.assertEqual(first_batch[1], 1)
        self.assertEqual(mid_batch[0], 46)
        self.assertEqual(mid_batch[1], 47)
        self.assertEqual(mid_batch_48[0], 96)
        self.assertEqual(mid_batch_48[1], 97)
        self.assertEqual(mid_batch_49[0], 98)
        self.assertEqual(mid_batch_49[1], 100)
        self.assertEqual(final_batch[0], 107)
        self.assertEqual(final_batch[1], end_frame)

    async def test_valid_uneven_batch_3(self):

        start_frame = 0
        end_frame = 100
        batch_count = 10

        batches = self._widget._prepare_batches(start_frame, end_frame, batch_count)
        self.assertEqual(len(batches), batch_count)

        first_batch = batches[0]
        mid_batch = batches[8]
        final_batch = batches[-1]

        # expect only the last batch has 11 frames, and others all have 10 frames
        self.assertEqual(first_batch[0], start_frame)
        self.assertEqual(first_batch[1], 9)
        self.assertEqual(mid_batch[0], 80)
        self.assertEqual(mid_batch[1], 89)
        self.assertEqual(final_batch[0], 90)
        self.assertEqual(final_batch[1], end_frame)

    async def test_no_frame_overlap(self):

        start_frame = 200
        end_frame = 500
        batch_count = 17
        batches = self._widget._prepare_batches(start_frame, end_frame, batch_count)

        for index, batch in enumerate(batches[:-1]):
            next_batch = batches[index + 1]
            last_Frame = batch[1]
            first_frame = next_batch[0]
            self.assertEqual(first_frame - last_Frame, 1)

    async def test_batch_count_to_large(self):
        start_frame = 200
        end_frame = 500
        batch_count = 500

        with self.assertRaises(ValueError):
            self._widget._prepare_batches(start_frame, end_frame, batch_count)
