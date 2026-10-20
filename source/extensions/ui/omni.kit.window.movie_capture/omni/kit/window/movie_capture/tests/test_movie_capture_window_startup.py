import asyncio
import os
import pathlib
from unittest.mock import patch

import carb
import omni.kit.test
import omni.kit.ui_test as ui_test
import omni.ui
from omni.kit.window.movie_capture import MovieCaptureExtension
from omni.kit.window.movie_capture.base_widget import WINDOW_HEIGHT, WINDOW_WIDTH
from omni.ui.tests.test_base import OmniUiTest

KIT_ROOT = pathlib.Path(carb.tokens.acquire_tokens_interface().resolve("${kit}")).parent.parent.parent
OUTPUTS_DIR = pathlib.Path(omni.kit.test.get_test_output_path())
DATA_PATH = pathlib.Path(__file__).parent.joinpath("../../../../../data")


class TestMovieCaptureWindowStartup(OmniUiTest):
    async def setUp(self) -> None:
        self._frames_wait_for_capture_resource_ready = 6
        self._movie_capture_ext = MovieCaptureExtension().get_instance()
        self._golden_img_dir = DATA_PATH.absolute().resolve().joinpath("tests")
        self._settings = carb.settings.get_settings()
        self._settings.set("exts/omni.kit.window.movie_capture/available_farms", None)

    async def tearDown(self):
        self._movie_capture_ext = None

    def _clean_files_in_directory(self, directory, suffix):
        if not os.path.exists(directory):
            return
        images = os.listdir(directory)
        for item in images:
            if item.endswith(suffix):
                os.remove(os.path.join(directory, item))

    def _make_sure_directory_existed(self, directory):
        if not os.path.exists(directory):
            try:  # pragma: no cover
                os.makedirs(directory, exist_ok=True)
            except OSError as error:
                carb.log_warn(f"Directory cannot be created: {dir}")
                return False
        return True

    async def _wait_for_image_writing(self, image_path, seconds_to_wait: float = 5, seconds_to_sleep: float = 0.1):
        # wait for the image frame is written to disk
        # my tests of scenes of different complexity show a range of 0.2 to 1 seconds wait time
        # so 5 second max time should be enough and we can early quit by checking the last
        # frame every 0.1 seconds.
        seconds_tried = 0.0
        carb.log_info("Waiting for frames to be ready for encoding.")
        while seconds_tried < seconds_to_wait:
            if os.path.isfile(image_path) and os.access(image_path, os.R_OK):
                break
            else:
                await asyncio.sleep(seconds_to_sleep)
                seconds_tried += seconds_to_sleep

        if seconds_tried >= seconds_to_wait:
            carb.log_warn(f"Wait time out. Failed to wait for writting of {image_path}.")
            return False
        else:
            return True

    async def test_movie_capture_1_window_can_show(self):
        self._movie_capture_ext.show_window(None, True)
        mc_window = omni.ui.Workspace.get_window("Movie Capture")
        self.assertTrue(mc_window is not None, "Failed to get Movie Capture window")

        if mc_window is not None:
            await self.docked_test_window(
                window=mc_window,
                width=WINDOW_WIDTH,
                height=WINDOW_HEIGHT,
            )
            # set output path to empty string as it's different from machine to machine
            # as its default value is current user's folder of the os
            output_widget = self._movie_capture_ext._window._output_settings_widget
            output_widget._ui_kit_path.model.set_value("")
            # wait for farm status button to settle, Linux tests shows a much quicker status change
            # so wait for enough frams for windows to be ready.
            frames_waiting_for_farm = 600
            while frames_waiting_for_farm > 0:
                await omni.kit.app.get_app().next_update_async()
                frames_waiting_for_farm -= 1

            # DGXC/OVC renders the window slightly differently than local/ETM, so use a
            # dedicated golden image when running on DGXC (ETM_DGXC_ACTIVE is set there).
            golden_img_name = "mc_win_ovc.png" if os.getenv("ETM_DGXC_ACTIVE") else "mc_win.png"
            await self.finalize_test(
                threshold=0.05, golden_img_dir=self._golden_img_dir, golden_img_name=golden_img_name
            )

    async def test_movie_capture_2_single_frame_capture(self):
        # Wait until the viewport has valid resources
        i = self._frames_wait_for_capture_resource_ready
        while i > 0:
            await omni.kit.app.get_app().next_update_async()
            i -= 1

        self._movie_capture_ext.show_window(None, True)
        mc_window = omni.ui.Workspace.get_window("Movie Capture")
        self.assertIsNotNone(mc_window, "Failed to get Movie Capture window")

        output_widget = self._movie_capture_ext._window._output_settings_widget
        capture_name = "mc_test_single_frame"
        output_folder = pathlib.Path(OUTPUTS_DIR).joinpath(capture_name)
        self._make_sure_directory_existed(output_folder)
        self._clean_files_in_directory(output_folder, ".png")
        image_path = os.path.join(output_folder, "Capture1.png")
        output_widget._ui_kit_path.model.set_value(str(output_folder))
        output_widget._ui_kit_capture_button.call_clicked_fn()

        # wait for file io
        await self._wait_for_image_writing(image_path)
        write_succeeded = os.path.exists(image_path)
        self.assertTrue(write_succeeded)

    async def test_movie_capture_3_multiple_frames_capture(self):
        # Wait until the viewport has valid resources
        i = self._frames_wait_for_capture_resource_ready
        while i > 0:
            await omni.kit.app.get_app().next_update_async()
            i -= 1

        self._movie_capture_ext.show_window(None, True)
        mc_window = omni.ui.Workspace.get_window("Movie Capture")
        if mc_window is None:
            self.assertTrue(False, "Failed to get Movie Capture window")
        else:
            output_widget = self._movie_capture_ext._window._output_settings_widget
            capture_widget = self._movie_capture_ext._window._capture_settings_widget
            # Only render 24 frames, to test sequence...takes too long to wait for 48
            capture_widget._ui_end_frame_input.value = 24
            end_frame = capture_widget._ui_end_frame_input.value
            capture_name = "mc_test_multiple_frames"
            output_folder = pathlib.Path(OUTPUTS_DIR).joinpath(capture_name)
            self._make_sure_directory_existed(output_folder)
            image_folder = os.path.join(output_folder, "Capture_frames")
            self._clean_files_in_directory(image_folder, ".png")
            image_path = os.path.join(image_folder, f"Capture.{str(end_frame).zfill(4)}.png")
            output_widget._ui_kit_path.model.set_value(str(output_folder))
            output_widget._ui_kit_capture_sequence_button.call_clicked_fn()

            # wait for file io
            await self._wait_for_image_writing(image_path, seconds_to_wait=10)
            write_succeeded = os.path.exists(image_path)
            self.assertTrue(write_succeeded)

    async def test_movie_capture_4_disabled_for_live_session(self):
        # Wait until the viewport has valid resources
        i = self._frames_wait_for_capture_resource_ready
        while i > 0:
            await omni.kit.app.get_app().next_update_async()
            i -= 1

        # Test that window is disabled during live session
        with patch("omni.kit.window.movie_capture.extension.is_in_live_session", return_value=True):
            self._movie_capture_ext.show_window(None, True)
            try:
                self.assertTrue(
                    self._movie_capture_ext._window is None or not self._movie_capture_ext._window._window.visible
                )
            finally:
                window_ref = ui_test.find("Movie Capture unavailable")
                if window_ref:
                    window_ref.widget.visible = False

        # Test that window is enabled again when live session turned off
        with patch("omni.kit.window.movie_capture.extension.is_in_live_session", return_value=False):
            self._movie_capture_ext.show_window(None, True)
            self.assertTrue(self._movie_capture_ext._window is not None)
