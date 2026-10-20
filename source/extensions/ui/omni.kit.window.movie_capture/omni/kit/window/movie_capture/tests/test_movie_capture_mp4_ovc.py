# Copyright (c) 2021-2023, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.

"""Tests for the MP4-on-OVC related behaviours in the movie capture output settings widget.

These cover the URI-aware code paths added by OMPE-52319 that did not previously have
automated coverage (NVBugs 6173205):

A) Remote URL detection (``__is_remote_url``)
B) Remote folder creation via ``omni.client.create_folder`` (``_make_sure_dir_existed``)
C) MP4 overwrite check via ``omni.client.stat`` (``_check_mp4_and_initiate``)
D) Disk-space estimation (``_estimate_required_temp_mb``) and low-disk dialog trigger
   from ``_on_capture_sequence_clicked``
E) Optional ``video_encoding`` import gate for the MP4 capture file type.

All side-effecting dependencies (``omni.client``, ``shutil``, ``os.path``, ``MessageDialog``,
``is_in_live_session``) are patched inside the
``omni.kit.window.movie_capture.output_settings_widget`` module so the tests do not need a
real Nucleus server, real disk, or a real renderer.
"""

from unittest.mock import MagicMock, patch

import omni.client
import omni.kit.app
from omni.kit.window.movie_capture import MovieCaptureExtension
from omni.kit.window.movie_capture.output_settings_widget import (
    CAPTURE_FILE_TYPES,
    OutputSettingsWidget,
)
from omni.ui.tests.test_base import OmniUiTest

_MODULE = "omni.kit.window.movie_capture.output_settings_widget"


def _make_capture_options(
    res_width=1920,
    res_height=1080,
    start_frame=1,
    end_frame=100,
    start_time=0.0,
    end_time=10.0,
    file_type=".mp4",
    hdr_output=False,
    animation_fps=24.0,
    is_video=True,
    is_capturing_frame_=True,
):
    """Build a mock capture-options object compatible with the static disk estimator."""
    opts = MagicMock()
    opts.res_width = res_width
    opts.res_height = res_height
    opts.start_frame = start_frame
    opts.end_frame = end_frame
    opts.start_time = start_time
    opts.end_time = end_time
    opts.file_type = file_type
    opts.hdr_output = hdr_output
    opts.animation_fps = animation_fps
    opts.is_video.return_value = is_video
    opts.is_capturing_frame.return_value = is_capturing_frame_
    return opts


class TestMovieCaptureMp4Ovc(OmniUiTest):
    async def setUp(self):
        self._movie_capture_ext = MovieCaptureExtension().get_instance()
        self._movie_capture_ext.show_window(None, True)
        await self.wait_n_updates()
        self._output_widget = self._movie_capture_ext._window._output_settings_widget

        # NVBugs-6173205: The MovieCaptureExtension window is a singleton shared with the
        # other test modules in this extension (notably ``test_movie_capture_window_startup``).
        # Several tests below mutate live widget fields directly — output path, capture name,
        # capture-type combobox index, and the ``_collect_capture_settings_fn`` callback. If
        # we do not restore these in tearDown, the polluted state leaks into later tests and
        # causes hard-to-diagnose failures (empty output folder, mocked callback, golden image
        # mismatch). Snapshot the original values here so tearDown can put them back.
        self._original_output_path = self._output_widget._ui_kit_path.model.get_value_as_string()
        self._original_capture_name = self._output_widget._ui_kit_default_capture_name.model.get_value_as_string()
        self._original_capture_type_index = self._output_widget._ui_kit_capture_type.model.get_item_value_model().as_int
        self._original_collect_capture_settings_fn = self._output_widget._collect_capture_settings_fn

    async def tearDown(self):
        # Restore widget state before releasing references so the singleton window is left
        # exactly as we found it for any subsequent test module.
        if self._output_widget is not None:
            if self._output_widget._disk_space_dialog is not None:
                self._output_widget._disk_space_dialog.destroy()
                self._output_widget._disk_space_dialog = None
            self._output_widget._collect_capture_settings_fn = self._original_collect_capture_settings_fn
            self._output_widget._ui_kit_path.model.set_value(self._original_output_path)
            self._output_widget._ui_kit_default_capture_name.model.set_value(self._original_capture_name)
            self._output_widget._ui_kit_capture_type.model.get_item_value_model().as_int = (
                self._original_capture_type_index
            )
        self._movie_capture_ext = None

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _is_remote_url(self, url):
        # Bypass Python's name mangling on the private ``__is_remote_url`` method.
        return self._output_widget._OutputSettingsWidget__is_remote_url(url)

    @staticmethod
    def _initiate_attr():
        return "_OutputSettingsWidget__initiate_capture"

    # ------------------------------------------------------------------
    # A) Remote URL detection
    # ------------------------------------------------------------------
    async def test_mp4_ovc_a_remote_url_detection(self):
        """Predicate returns True only for non-file URI schemes longer than one character."""
        # Remote / non-local URIs
        self.assertTrue(self._is_remote_url("omniverse://server/path/out"))
        self.assertTrue(self._is_remote_url("omniverse://server/"))
        self.assertTrue(self._is_remote_url("s3://bucket/key"))
        self.assertTrue(self._is_remote_url("http://host/x"))

        # Local-style inputs must NOT be classified as remote.
        self.assertFalse(self._is_remote_url("/local/path"))
        self.assertFalse(self._is_remote_url("relative/path"))
        self.assertFalse(self._is_remote_url("file:///tmp/out.mp4"))
        self.assertFalse(self._is_remote_url(""))
        # Windows drive letter: scheme would be the single-letter drive (e.g. "C"), filtered out
        # by the ``len(url.scheme) > 1`` guard so the path is treated as local.
        self.assertFalse(self._is_remote_url("C:\\local\\path"))

    # ------------------------------------------------------------------
    # B) Remote folder creation
    # ------------------------------------------------------------------
    async def test_mp4_ovc_b_remote_folder_creation_uses_omni_client(self):
        """For a remote URL, ``_make_sure_dir_existed`` calls ``omni.client.create_folder`` once."""
        remote = "omniverse://server/capture_out"
        with (
            patch(f"{_MODULE}.omni.client.create_folder", return_value=omni.client.Result.OK) as mock_create,
            patch(f"{_MODULE}.os.makedirs") as mock_makedirs,
        ):
            ok = self._output_widget._make_sure_dir_existed(remote)
            self.assertTrue(ok)
            mock_create.assert_called_once_with(remote)
            mock_makedirs.assert_not_called()

    async def test_mp4_ovc_b_remote_folder_already_exists_is_ok(self):
        """``ERROR_ALREADY_EXISTS`` returned by ``create_folder`` is treated as success."""
        remote = "omniverse://server/already_there"
        with patch(
            f"{_MODULE}.omni.client.create_folder",
            return_value=omni.client.Result.ERROR_ALREADY_EXISTS,
        ) as mock_create:
            ok = self._output_widget._make_sure_dir_existed(remote)
            self.assertTrue(ok)
            mock_create.assert_called_once_with(remote)

    async def test_mp4_ovc_b_local_folder_creation_skips_omni_client(self):
        """For a local path, ``omni.client.create_folder`` must NOT be called."""
        local = "/tmp/movie_capture_unit_test_local_dir"
        with (
            patch(f"{_MODULE}.omni.client.create_folder") as mock_create,
            patch(f"{_MODULE}.os.makedirs") as mock_makedirs,
            patch(f"{_MODULE}.os.path.exists", return_value=False),
        ):
            ok = self._output_widget._make_sure_dir_existed(local)
            self.assertTrue(ok)
            mock_create.assert_not_called()
            mock_makedirs.assert_called_once_with(local, exist_ok=True)

    # ------------------------------------------------------------------
    # C) MP4 overwrite check via omni.client.stat on a remote path
    # ------------------------------------------------------------------
    def _prep_mp4_state(self, path="omniverse://server/movies", capture_name="Capture"):
        self.assertIn(".mp4", CAPTURE_FILE_TYPES, "Expected .mp4 to be available for the MP4 OVC tests")
        self._output_widget._ui_kit_path.model.set_value(path)
        self._output_widget._ui_kit_default_capture_name.model.set_value(capture_name)
        self._output_widget._set_combobox_string_value(self._output_widget._ui_kit_capture_type, ".mp4")

    async def test_mp4_ovc_c_remote_existing_mp4_prompts_overwrite(self):
        """On a remote URL with an existing .mp4 the user is prompted before capture starts."""
        self._prep_mp4_state()
        stat_exists = (omni.client.Result.OK, MagicMock())  # (result, entry)

        with (
            patch(f"{_MODULE}.omni.client.stat", return_value=stat_exists) as mock_stat,
            patch.object(self._output_widget, self._initiate_attr()) as mock_initiate,
            patch(f"{_MODULE}.MessageDialog") as mock_dialog_ctor,
        ):
            self._output_widget._check_mp4_and_initiate()

            # Remote path => stat goes through omni.client, not os.path.exists.
            mock_stat.assert_called_once()
            called_url = mock_stat.call_args.args[0]
            self.assertTrue(called_url.startswith("omniverse://server/movies"))
            self.assertTrue(called_url.endswith("Capture.mp4"))

            # Existing file => overwrite dialog shown, capture not yet initiated.
            mock_dialog_ctor.assert_called_once()
            mock_dialog_ctor.return_value.show.assert_called_once()
            mock_initiate.assert_not_called()

    async def test_mp4_ovc_c_remote_missing_mp4_initiates_capture(self):
        """On a remote URL with no existing .mp4, capture proceeds without a prompt."""
        self._prep_mp4_state()
        # Explicit ERROR_NOT_FOUND tuple form so the test simulates the precise
        # "file not found" condition rather than any non-OK result.
        stat_missing = (omni.client.Result.ERROR_NOT_FOUND, None)

        with (
            patch(f"{_MODULE}.omni.client.stat", return_value=stat_missing) as mock_stat,
            patch.object(self._output_widget, self._initiate_attr()) as mock_initiate,
            patch(f"{_MODULE}.MessageDialog") as mock_dialog_ctor,
        ):
            self._output_widget._check_mp4_and_initiate()

            mock_stat.assert_called_once()
            mock_dialog_ctor.assert_not_called()
            mock_initiate.assert_called_once()

    async def test_mp4_ovc_c_local_mp4_uses_os_path_exists(self):
        """On a local path the overwrite check uses ``os.path.exists``, not ``omni.client.stat``."""
        self._output_widget._ui_kit_path.model.set_value("/tmp/local_movies")
        self._output_widget._ui_kit_default_capture_name.model.set_value("LocalCap")
        self.assertIn(".mp4", CAPTURE_FILE_TYPES)
        self._output_widget._set_combobox_string_value(self._output_widget._ui_kit_capture_type, ".mp4")

        with (
            patch(f"{_MODULE}.omni.client.stat") as mock_stat,
            patch(f"{_MODULE}.os.path.exists", return_value=False) as mock_exists,
            patch.object(self._output_widget, self._initiate_attr()) as mock_initiate,
            patch(f"{_MODULE}.MessageDialog") as mock_dialog_ctor,
        ):
            self._output_widget._check_mp4_and_initiate()
            mock_stat.assert_not_called()
            mock_exists.assert_called_once()
            mock_dialog_ctor.assert_not_called()
            mock_initiate.assert_called_once()

    # ------------------------------------------------------------------
    # D) Disk-space estimation and low-disk dialog trigger
    # ------------------------------------------------------------------
    async def test_mp4_ovc_d_estimate_required_temp_mb_is_positive_and_scales(self):
        """The estimator returns a positive int that grows with frame count and resolution."""
        baseline_opts = _make_capture_options(
            res_width=640,
            res_height=480,
            start_frame=1,
            end_frame=10,
            file_type=".png",
            is_video=False,
            is_capturing_frame_=True,
            hdr_output=False,
        )
        baseline = OutputSettingsWidget._estimate_required_temp_mb(baseline_opts)
        self.assertGreater(baseline, 0, "Required temp MB must be a positive integer")

        # Doubling frame count must increase the estimate.
        double_frames_opts = _make_capture_options(
            res_width=640,
            res_height=480,
            start_frame=1,
            end_frame=20,
            file_type=".png",
            is_video=False,
            is_capturing_frame_=True,
            hdr_output=False,
        )
        self.assertGreater(
            OutputSettingsWidget._estimate_required_temp_mb(double_frames_opts),
            baseline,
            "Doubling the frame range must increase the temp MB estimate",
        )

        # Doubling each spatial dimension quadruples the per-frame bytes.
        double_res_opts = _make_capture_options(
            res_width=1280,
            res_height=960,
            start_frame=1,
            end_frame=10,
            file_type=".png",
            is_video=False,
            is_capturing_frame_=True,
            hdr_output=False,
        )
        self.assertGreater(
            OutputSettingsWidget._estimate_required_temp_mb(double_res_opts),
            baseline,
            "Increasing resolution must increase the temp MB estimate",
        )

        # Video output occupies ~2x bytes (frames dir + encoded MP4).
        mp4_opts = _make_capture_options(
            res_width=640,
            res_height=480,
            start_frame=1,
            end_frame=10,
            file_type=".mp4",
            is_video=True,
            is_capturing_frame_=True,
            hdr_output=False,
        )
        self.assertGreater(
            OutputSettingsWidget._estimate_required_temp_mb(mp4_opts),
            baseline,
            "Video output should require more temp space than equivalent image-only capture",
        )

    async def test_mp4_ovc_d_capture_sequence_remote_low_disk_triggers_dialog(self):
        """Sequence capture on a remote URI with insufficient free space shows the disk-space dialog."""
        self._output_widget._ui_kit_path.model.set_value("omniverse://server/seq_out")

        capture_opts = _make_capture_options()
        self._output_widget._collect_capture_settings_fn = MagicMock(return_value=(capture_opts, {}))

        required_mb = 500
        available_bytes = 100 * 1024 * 1024
        mock_disk = MagicMock()
        mock_disk.return_value.free = available_bytes

        with (
            patch.object(OutputSettingsWidget, "_estimate_required_temp_mb", return_value=required_mb),
            patch(f"{_MODULE}.shutil.disk_usage", mock_disk),
            patch.object(self._output_widget, "_show_disk_space_dialog") as mock_show,
            patch.object(self._output_widget, "_check_mp4_and_initiate") as mock_mp4_initiate,
            patch(f"{_MODULE}.is_in_live_session", return_value=False),
        ):
            self._output_widget._on_capture_sequence_clicked()

            mock_show.assert_called_once()
            args, _ = mock_show.call_args
            self.assertEqual(args[0], required_mb)
            self.assertEqual(args[1], available_bytes // (1024 * 1024))
            # Dialog short-circuits capture initiation.
            mock_mp4_initiate.assert_not_called()

    async def test_mp4_ovc_d_capture_sequence_remote_enough_disk_proceeds(self):
        """Sequence capture on a remote URI with enough free space skips the disk-space dialog."""
        self._output_widget._ui_kit_path.model.set_value("omniverse://server/seq_out_ok")

        capture_opts = _make_capture_options()
        self._output_widget._collect_capture_settings_fn = MagicMock(return_value=(capture_opts, {}))

        required_mb = 50
        available_bytes = 4096 * 1024 * 1024  # 4 GiB free, plenty
        mock_disk = MagicMock()
        mock_disk.return_value.free = available_bytes

        with (
            patch.object(OutputSettingsWidget, "_estimate_required_temp_mb", return_value=required_mb),
            patch(f"{_MODULE}.shutil.disk_usage", mock_disk),
            patch.object(self._output_widget, "_show_disk_space_dialog") as mock_show,
            patch.object(self._output_widget, "_check_mp4_and_initiate") as mock_mp4_initiate,
            patch(f"{_MODULE}.is_in_live_session", return_value=False),
        ):
            self._output_widget._on_capture_sequence_clicked()

            mock_show.assert_not_called()
            mock_mp4_initiate.assert_called_once()

    async def test_mp4_ovc_d_capture_sequence_local_skips_disk_preflight(self):
        """For a local path the disk-space pre-flight is bypassed entirely."""
        self._output_widget._ui_kit_path.model.set_value("/tmp/local_seq_out")

        capture_opts = _make_capture_options()
        self._output_widget._collect_capture_settings_fn = MagicMock(return_value=(capture_opts, {}))

        with (
            patch.object(OutputSettingsWidget, "_estimate_required_temp_mb") as mock_estimate,
            patch(f"{_MODULE}.shutil.disk_usage") as mock_disk,
            patch.object(self._output_widget, "_show_disk_space_dialog") as mock_show,
            patch.object(self._output_widget, "_check_mp4_and_initiate") as mock_mp4_initiate,
            patch(f"{_MODULE}.is_in_live_session", return_value=False),
        ):
            self._output_widget._on_capture_sequence_clicked()

            mock_estimate.assert_not_called()
            mock_disk.assert_not_called()
            mock_show.assert_not_called()
            mock_mp4_initiate.assert_called_once()

    # ------------------------------------------------------------------
    # E) Optional video_encoding import gate for MP4 capture type
    # ------------------------------------------------------------------
    async def test_mp4_ovc_e_mp4_listed_when_video_encoding_available(self):
        """In the test environment ``video_encoding`` is importable so ``.mp4`` is offered.

        The optional ``import video_encoding`` happens once at extension load time and
        appends ``.mp4`` to ``CAPTURE_FILE_TYPES``. Because the test suite runs with
        ``omni.videoencoding`` enabled, the post-condition is that ``.mp4`` is present.
        """
        self.assertIn(".mp4", CAPTURE_FILE_TYPES)

        # And the capture-type combobox in the running widget exposes the .mp4 option,
        # so users can select it for OVC captures.
        items = self._output_widget._ui_kit_capture_type.model.get_item_children()
        labels = [self._output_widget._ui_kit_capture_type.model.get_item_value_model(item).as_string for item in items]
        self.assertIn(".mp4", labels)

    # ------------------------------------------------------------------
    # F) End-to-end real DGXC capture (OVC-only)
    # ------------------------------------------------------------------
    async def test_mp4_ovc_f_real_dgxc_sequence_capture_lands_on_nucleus(self):
        """Render a short MP4 sequence and assert the file lands on the DGXC Nucleus server.

        Sections A-E above validate the URI-aware branching with mocked boundaries. This
        test is the counterpart that exercises the same code paths end-to-end against a
        real Nucleus server, real ``omni.client`` calls, real ``omni.videoencoding`` encode
        and a real capture pipeline -- the thing Roman asked for on MR !549 ("nothing about
        that call sequence guarantees the render was captured to a video file").

        Gated to skip unless the kit app is running in OVC mode, since it requires:
          - a real renderer producing frames into a real temp directory,
          - a real ``omni.videoencoding`` encode pass,
          - network reachability to ``dev.eu-swe.dgxctest.omniverse.nvidia.com``.

        Under the standard local / CI test runner ``_is_ovc_mode()`` is False, so the test
        skips cleanly. Under the ETM-on-DGXC runner the test executes for real.
        """
        import time

        import carb
        from omni.kit.capture.viewport import CaptureExtension, CaptureOptions, CaptureStatus

        if not self._output_widget._is_ovc_mode():
            self.skipTest("Real DGXC capture test requires kit running in OVC mode")

        # video_encoding must be importable in the test environment so .mp4 is a real option.
        self.assertIn(".mp4", CAPTURE_FILE_TYPES)

        nucleus_root = "omniverse://dev.eu-swe.dgxctest.omniverse.nvidia.com/Projects/omni.kit.window.movie_capture"

        # Verify the test bucket exists on Nucleus. If it does not, try to create it; if
        # creation fails, fail the test rather than silently uploading to a path the runner
        # cannot read back. ERROR_ALREADY_EXISTS is treated as success (race-tolerant).
        stat_result, _stat_entry = await omni.client.stat_async(nucleus_root)
        if stat_result != omni.client.Result.OK:
            create_result = await omni.client.create_folder_async(nucleus_root)
            self.assertIn(
                create_result,
                (omni.client.Result.OK, omni.client.Result.ERROR_ALREADY_EXISTS),
                f"Nucleus root {nucleus_root} is not accessible (stat={stat_result}) "
                f"and could not be created (create_folder={create_result})",
            )

        # Timestamped, run-unique capture name so concurrent runs don't collide and so we
        # can match the resulting .mp4 exactly.
        capture_name = f"mp4_ovc_e2e_{int(time.time())}"
        expected_mp4_url = f"{nucleus_root}/{capture_name}.mp4"

        # Drive the same UI fields a user would set on DGXC so the widget's URI-aware
        # paths (__is_remote_url, _make_sure_dir_existed, _check_mp4_and_initiate) all
        # see remote inputs.
        self._output_widget._ui_kit_path.model.set_value(nucleus_root)
        self._output_widget._ui_kit_default_capture_name.model.set_value(capture_name)
        self._output_widget._set_combobox_string_value(self._output_widget._ui_kit_capture_type, ".mp4")

        # Supply real CaptureOptions instead of relying on the full window's capture- and
        # render-settings widget state. A 5-frame, 256x256 sequence keeps the encode quick
        # while still proving the render -> encode -> upload path end-to-end.
        capture_instance = CaptureExtension.get_instance()

        def collect_real_options(to_capture_sequence: bool, to_send_to_farm: bool = False):
            opts = CaptureOptions()
            opts.output_folder = nucleus_root
            opts.file_name = capture_name
            opts.file_type = ".mp4"
            opts.res_width = 256
            opts.res_height = 256
            opts.start_frame = 1
            opts.end_frame = 5
            opts.start_time = 0.0
            opts.end_time = 5.0 / 24.0
            opts.animation_fps = 24.0
            # -1 means "do not capture every Nth frame" -- required for .mp4 sequence output.
            opts.capture_every_Nth_frames = -1
            capture_instance.options = opts
            return opts, {}

        self._output_widget._collect_capture_settings_fn = collect_real_options

        # Snapshot capture state BEFORE clicking. The capture_instance singleton may carry
        # a leftover ``DONE`` from a prior test; without this check the post-click DONE-wait
        # could pass instantly without ever running our capture. We require an explicit
        # transition out of NONE/DONE to confirm the click actually started a new capture.
        pre_click_status = capture_instance.progress.capture_status
        carb.log_info(f"[mp4_ovc_f] Pre-click capture_status={pre_click_status}; target={expected_mp4_url}")

        # Trigger the sequence-capture path users hit for movie capture. This runs the
        # disk-space pre-flight, remote folder creation, MP4 overwrite check and
        # __initiate_capture -- all unmocked.
        self._output_widget._on_capture_sequence_clicked()
        carb.log_info(
            f"[mp4_ovc_f] _on_capture_sequence_clicked returned; " f"status={capture_instance.progress.capture_status}"
        )

        # Phase 1: confirm the capture actually STARTED (status leaves the idle states).
        # Without this gate, a short-circuit in _on_capture_sequence_clicked (live session
        # check, _check_output_path failure, etc.) would leave the status in NONE/DONE and
        # the DONE-wait below would either time out silently or, worse, pass on a stale
        # DONE from a previous capture.
        start_timeout_s = 30.0
        start_deadline = time.time() + start_timeout_s
        while time.time() < start_deadline:
            status = capture_instance.progress.capture_status
            if status not in (CaptureStatus.NONE, CaptureStatus.DONE):
                carb.log_info(f"[mp4_ovc_f] Capture started: status={status}")
                break
            await self.wait_n_updates(1)
        else:
            self.fail(
                f"Capture never left idle within {start_timeout_s}s after click "
                f"(status={capture_instance.progress.capture_status}). "
                f"_on_capture_sequence_clicked likely short-circuited (live session, "
                f"output-path check, etc.) and no capture was actually initiated."
            )

        # Phase 2: wait for the capture pipeline to reach DONE, logging status transitions
        # and a heartbeat every 5s so a frozen pipeline is visible in the test log instead
        # of just timing out silently.
        finish_timeout_s = 180.0
        finish_deadline = time.time() + finish_timeout_s
        last_status = capture_instance.progress.capture_status
        last_log_time = time.time()
        while time.time() < finish_deadline:
            status = capture_instance.progress.capture_status
            if status != last_status:
                carb.log_info(f"[mp4_ovc_f] Status transition: {last_status} -> {status}")
                last_status = status
            if status == CaptureStatus.DONE:
                break
            now = time.time()
            if now - last_log_time >= 5.0:
                carb.log_info(f"[mp4_ovc_f] Still capturing: status={status} elapsed={now - last_log_time:.1f}s")
                last_log_time = now
            await self.wait_n_updates(1)
        else:
            self.fail(
                f"Capture did not reach DONE within {finish_timeout_s}s; "
                f"last status: {capture_instance.progress.capture_status}"
            )

        carb.log_info(f"[mp4_ovc_f] Capture reached DONE; verifying {expected_mp4_url} on Nucleus")

        # Verify the .mp4 actually landed on the remote Nucleus server.
        result, _entry = await omni.client.stat_async(expected_mp4_url)
        self.assertEqual(
            result,
            omni.client.Result.OK,
            f"Captured .mp4 not found at {expected_mp4_url}: {result}",
        )
        carb.log_info(f"[mp4_ovc_f] Verified .mp4 on Nucleus; cleaning up {expected_mp4_url}")

        # Clean up so the test bucket does not accumulate artifacts across runs.
        await omni.client.delete_async(expected_mp4_url)
