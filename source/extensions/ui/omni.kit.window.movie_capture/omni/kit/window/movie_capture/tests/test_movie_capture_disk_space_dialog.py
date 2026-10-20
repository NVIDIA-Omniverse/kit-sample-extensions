# Copyright (c) 2021-2023, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.

"""Tests for the low-disk-space dialog shown when capturing to a remote URI."""

import os
import tempfile
from unittest.mock import MagicMock, patch

import omni.kit.app
import omni.kit.ui_test as ui_test
from omni.kit.window.movie_capture import MovieCaptureExtension
from omni.ui.tests.test_base import OmniUiTest

_MODULE = "omni.kit.window.movie_capture.output_settings_widget"


class TestMovieCaptureDiskSpaceDialog(OmniUiTest):
    async def setUp(self):
        self._movie_capture_ext = MovieCaptureExtension().get_instance()
        self._movie_capture_ext.show_window(None, True)
        await self.wait_n_updates()
        self._output_widget = self._movie_capture_ext._window._output_settings_widget

    async def tearDown(self):
        if self._output_widget and self._output_widget._disk_space_dialog is not None:
            self._output_widget._disk_space_dialog.destroy()
            self._output_widget._disk_space_dialog = None
        self._movie_capture_ext = None

    async def _open_dialog(self, required_mb=500, available_mb=100):
        """Show the dialog with the given space values and wait one frame."""
        self._output_widget._show_disk_space_dialog(required_mb, available_mb)
        await self.wait_n_updates()

    def _find_button(self, identifier):
        return ui_test.find(f"Movie Capture - Low Disk Space//Frame/**/Button[*].identifier=='{identifier}'")

    async def test_disk_space_1_cancel_closes_dialog_without_capture(self):
        """Cancel destroys the dialog without initiating capture or deleting any files."""
        with (
            patch.object(self._output_widget, "_check_mp4_and_initiate") as mock_initiate,
            patch(f"{_MODULE}.shutil.rmtree") as mock_rmtree,
        ):
            await self._open_dialog()
            self.assertIsNotNone(self._output_widget._disk_space_dialog)

            btn = self._find_button("disk_space_dialog_cancel")
            self.assertIsNotNone(btn, "Cancel button not found in dialog")
            btn.widget.call_clicked_fn()
            await self.wait_n_updates()

            self.assertIsNone(self._output_widget._disk_space_dialog, "Dialog should be destroyed after Cancel")
            mock_initiate.assert_not_called()
            mock_rmtree.assert_not_called()

    async def test_disk_space_2_continue_anyway_initiates_without_cleanup(self):
        """Continue Anyway initiates capture immediately without touching the temp directory."""
        with (
            patch.object(self._output_widget, "_check_mp4_and_initiate") as mock_initiate,
            patch(f"{_MODULE}.shutil.rmtree") as mock_rmtree,
        ):
            await self._open_dialog()

            btn = self._find_button("disk_space_dialog_continue")
            self.assertIsNotNone(btn, "Continue Anyway button not found in dialog")
            btn.widget.call_clicked_fn()
            await self.wait_n_updates()

            self.assertIsNone(self._output_widget._disk_space_dialog, "Dialog should be destroyed after Continue")
            mock_initiate.assert_called_once()
            mock_rmtree.assert_not_called()

    async def test_disk_space_3_clear_temp_deletes_stale_dirs_and_retries(self):
        """Clear Temp & Retry removes stale temp dirs then initiates capture when space is freed."""
        stale_dirs = [
            os.path.join(tempfile.gettempdir(), "omni_capture_viewport_aaa"),
            os.path.join(tempfile.gettempdir(), "omni_capture_viewport_bbb"),
        ]
        # After cleanup, report 2000 MB free — enough to proceed past the 500 MB requirement.
        mock_disk_usage = MagicMock()
        mock_disk_usage.return_value.free = 2000 * 1024 * 1024

        with (
            patch.object(self._output_widget, "_check_mp4_and_initiate") as mock_initiate,
            patch(f"{_MODULE}.glob.glob", return_value=stale_dirs),
            patch(f"{_MODULE}.shutil.rmtree") as mock_rmtree,
            patch(f"{_MODULE}.shutil.disk_usage", mock_disk_usage),
        ):
            await self._open_dialog(required_mb=500, available_mb=100)

            btn = self._find_button("disk_space_dialog_clear_retry")
            self.assertIsNotNone(btn, "Clear Temp & Retry button not found in dialog")
            btn.widget.call_clicked_fn()
            await self.wait_n_updates()

            self.assertIsNone(self._output_widget._disk_space_dialog, "Dialog should be destroyed after Clear Temp")
            self.assertEqual(mock_rmtree.call_count, len(stale_dirs))
            for stale in stale_dirs:
                mock_rmtree.assert_any_call(stale, ignore_errors=True)
            mock_initiate.assert_called_once()
