## Copyright (c) 2023, NVIDIA CORPORATION.  All rights reserved.
##
## NVIDIA CORPORATION and its licensors retain all intellectual property
## and proprietary rights in and to this software, related documentation
## and any modifications thereto.  Any use, reproduction, disclosure or
## distribution of this software and related documentation without an express
## license agreement from NVIDIA CORPORATION is strictly prohibited.
##
import os
import pathlib
import sys
import unittest

import carb
import carb.settings
import omni.kit.app
import omni.kit.commands
import omni.kit.test
import omni.kit.undo
import omni.ui
from omni.kit.test_suite.helpers import wait_stage_loading
from omni.ui.tests.test_base import OmniUiTest

DATA_PATH = pathlib.Path(__file__).parent.joinpath("../../../../../data")
OUTPUTS_DIR = pathlib.Path(omni.kit.test.get_test_output_path())


# This test captures the automation task OM-105513 for (OM-90352).
# The actual test code is in 'test_movie_capture_restart'.
# All function here that start with "movie_capture_" are potentially fragile
# against changes in the actual movie maker, therefore I isolated them.
def movie_capture_setup_settings(output_path=None, pt_spp=None, seq_start=None, seq_end=None):
    movie_cap_ext = omni.kit.window.movie_capture.MovieCaptureExtension.get_instance()
    movie_cap_ext.show_window(None, True)

    output_widget = movie_cap_ext._window._output_settings_widget

    if output_path is not None:
        output_widget._ui_kit_path.model.set_value(output_path)

    rendersettings_widget = movie_cap_ext._window._render_settings_widget
    capture_settings_widget = movie_cap_ext._window._capture_settings_widget

    # SPP for Path tracing:
    if pt_spp is not None:
        rendersettings_widget._ui_spp_input.value = pt_spp

    if seq_start is not None:
        capture_settings_widget._ui_start_frame_input.value = seq_start

    if seq_end is not None:
        capture_settings_widget._ui_end_frame_input.value = seq_end

    # make sure app level capture is not enabled
    capture_settings_widget = movie_cap_ext._window._capture_settings_widget
    capture_settings_widget._ui_kit_capture_app_check.model.as_bool = False

    # @todo: render preset RTX?
    # _ui_kit_render_preset
    # _on_render_preset_selection_changed


def movie_capture_start_capturing():
    # Simulate click on "Capture Sequence" button
    movie_cap_ext = omni.kit.window.movie_capture.MovieCaptureExtension.get_instance()
    output_widget = movie_cap_ext._window._output_settings_widget
    output_widget._ui_kit_capture_sequence_button.call_clicked_fn()
    carb.log_info("Movie capturing started...")


def movie_capture_cancel():
    # movie capture uses this viewport capture extension
    cap_ext = omni.kit.capture.viewport.CaptureExtension.get_instance()
    if cap_ext._progress.capture_status != omni.kit.capture.viewport.CaptureStatus.CAPTURING:
        carb.log_warn("Trying to cancel movie capture while it's not capturing.")
        return
    cap_ext.cancel()


# Unit test for starting/cancelling/restarting movie capture on particular scene.
class TestMovieCaptureWindowTestReset(OmniUiTest):
    # This folder will be used write the goldens under
    # kit\source\extensions\omni.rtx.tests\data\golden\
    TEST_PATH = "rtx_movie_capture_restart"

    async def setUp(self):

        # wait settings to take effect (relevant for loading)
        await self.wait_n_updates(10)

        # The original bug-report scene, collected into the test data:
        scene_path = os.path.join(DATA_PATH, "tests", "usd", "Collected_CaptureCrash_OM-105513_OM-90352.usd")
        self._context = omni.usd.get_context()
        await self._context.open_stage_async(scene_path)
        await wait_stage_loading()

        # wait on stage load
        await omni.kit.app.get_app().next_update_async()

    async def tearDown(self):
        await super().tearDown()

    # the "test_" prefix flags this as a test automatically
    @unittest.skipIf(os.getenv("ETM_ACTIVE"), "skipped in ETM")
    async def test_movie_capture_window_test_restart(self):
        # # await wait_for_update()
        # The original repro steps for OM-105513 where given as:
        #   1) Load the bug-report scene (Collected_CaptureCrash)
        #      =>Done in 'setUp'
        #   2) Open Movie Capture (extension: omni.kit.window.movie_capture)
        #   3) Change the output path to some valid path.
        #   4) Start the capture. After it started, cancel it.
        #   5) Start a capture again. It will crash.

        # 2) Grab the extension, make it visible.
        movie_cap_ext = omni.kit.window.movie_capture.MovieCaptureExtension.get_instance()
        movie_cap_ext.show_window(None, True)

        # 3) Modify movie capture settings
        # *) Fix some extra settings. we are not really interested in long path tracing with high spp
        target_path = OUTPUTS_DIR.joinpath(self.TEST_PATH)
        pt_spp = 16
        seq_start = 0
        seq_end = 100
        movie_capture_setup_settings(str(target_path), pt_spp, seq_start, seq_end)

        await self.wait_n_updates(2)

        # 4) Start the capture...
        # The capturing will run in the background.
        movie_capture_start_capturing()
        carb.log_info("Capturing In progress")

        # Wait for several frames before cancelling.
        frames_wait = 20
        await self.wait_n_updates(20)
        carb.log_info(f"{frames_wait} frames passed. Attempting to cancel.")

        # 4) ... After it started, cancel it.
        movie_capture_cancel()
        cap_ext = omni.kit.capture.viewport.CaptureExtension.get_instance()
        while not cap_ext.done:
            await omni.kit.app.get_app().next_update_async()

        # 5) Start a capture again. Should not crash.
        # Using a different output directory to avoid potential problems
        # with overwriting existing files (the related checkbox in the movie capture ext
        # is not easy to trigger from python script and internally also creates
        # a message box).
        target_path = OUTPUTS_DIR.joinpath(self.TEST_PATH + "_02")
        movie_capture_setup_settings(str(target_path))
        movie_capture_start_capturing()
        frames_wait = 25
        await self.wait_n_updates(frames_wait)
        carb.log_info(f"{frames_wait} frames passed. Attempting to cancel again.")
        movie_capture_cancel()
        while not cap_ext.done:
            await omni.kit.app.get_app().next_update_async()

        carb.log_info("Test Finished. Didn't crash. No image output.")
