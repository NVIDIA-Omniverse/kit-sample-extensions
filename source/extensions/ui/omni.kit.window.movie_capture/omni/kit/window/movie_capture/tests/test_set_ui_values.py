import asyncio
import os
import pathlib
from unittest.mock import patch

import carb
import omni.kit.actions.core
import omni.kit.app
import omni.kit.capture.viewport
import omni.kit.test
import omni.kit.ui_test as ui_test
import omni.ui
from omni.kit.test_suite.helpers import wait_stage_loading
from omni.kit.window.movie_capture import MovieCaptureExtension
from omni.kit.window.movie_capture.base_widget import WINDOW_HEIGHT, WINDOW_WIDTH
from omni.kit.window.movie_capture.render_settings_widget import RenderInfo
from omni.ui.tests.test_base import OmniUiTest
from pxr import UsdRender

KIT_ROOT = pathlib.Path(carb.tokens.acquire_tokens_interface().resolve("${kit}")).parent.parent.parent
OUTPUTS_DIR = pathlib.Path(omni.kit.test.get_test_output_path())
DATA_PATH = pathlib.Path(__file__).parent.joinpath("../../../../../data")
TEST_USD_DIR = DATA_PATH.joinpath("tests/usd")
DEFAULT_RENDER_PRODUCT_SETTING_PATH = "/exts/omni.kit.window.movie_capture/default_render_product"
DEFAULT_RENDER_PRESET_SETTING_PATH = "/exts/omni.kit.window.movie_capture/default_render_preset"
DEFAULT_SPP_PER_ITERATION_SETTING_PATH = "/exts/omni.kit.window.movie_capture/default_spp_per_iteration"
DEFAULT_SPP_PER_SUBFRAME_SETTING_PATH = "/exts/omni.kit.window.movie_capture/default_spp_per_subframe"
DEFAULT_SUBFRAME_PER_FRAME_SETTING_PATH = "/exts/omni.kit.window.movie_capture/default_subframe_per_frame"
DEFAULT_FRAME_SHUTTER_OPEN_SETTING_PATH = "/exts/omni.kit.window.movie_capture/default_frame_shutter_open"
DEFAULT_FRAME_SHUTTER_CLOSE_SETTING_PATH = "/exts/omni.kit.window.movie_capture/default_frame_shutter_close"
DEFAULT_IRAY_ITERATION_SETTING_PATH = "/exts/omni.kit.window.movie_capture/default_iray_iterations"
DEFAULT_IRAY_SUBFRAMES_PER_FRAME_SETTING_PATH = "/exts/omni.kit.window.movie_capture/default_iray_subframes_per_frame"


class TestSetUiValues(OmniUiTest):
    async def setUp(self) -> None:
        await super().setUp()
        self._frames_wait_for_capture_resource_ready = 6
        self._movie_capture_ext = MovieCaptureExtension().get_instance()
        self._golden_img_dir = DATA_PATH.absolute().resolve().joinpath("tests")
        self._settings = carb.settings.get_settings()
        self._settings.set("exts/omni.kit.window.movie_capture/available_farms", None)
        for _ in range(2):
            await omni.kit.app.get_app().next_update_async()

    async def tearDown(self):
        await super().tearDown()
        self._movie_capture_ext = None

    async def test_set_ui_values_1_read_back_saved_options(self):
        test_usd_path = os.path.join(TEST_USD_DIR, "options_save_test.usda")
        self._context = omni.usd.get_context()
        await self._context.open_stage_async(test_usd_path)
        await wait_stage_loading()

        for _ in range(2):
            await omni.kit.app.get_app().next_update_async()

        self._movie_capture_ext.show_window(None, True)
        mc_window = omni.ui.Workspace.get_window("Movie Capture")
        if mc_window is None:
            self.fail("Failed to get Movie Capture window")
        else:
            capture_options, farm_options = self._movie_capture_ext._window._read_kit_capture_options(True)
            self.assertEqual(capture_options.fps, 30)
            self.assertEqual(capture_options.start_frame, 0)
            self.assertEqual(capture_options.camera, "/OmniverseKit_Persp")
            self.assertEqual(capture_options.res_width, 3840)
            self.assertEqual(capture_options.res_height, 2160)
            self.assertEqual(capture_options.render_preset, 0)
            self.assertEqual(capture_options.ptmb_fso, 0.1)
            self.assertEqual(capture_options.ptmb_fsc, 0.6)
            self.assertEqual(capture_options.capture_every_Nth_frames, 10)
            self.assertEqual(capture_options.app_level_capture, True)
            self.assertEqual(capture_options.real_time_settle_latency_frames, 8)
            self.assertEqual(capture_options.preroll_frames, 10)
            self.assertEqual(capture_options.spp_per_iteration, 1)
            self.assertEqual(capture_options.path_trace_spp, 64)
            self.assertEqual(capture_options.ptmb_subframes_per_frame, 16)

    async def test_set_ui_values_2_change_ui(self):
        self._movie_capture_ext.show_window(None, True)
        mc_window = omni.ui.Workspace.get_window("Movie Capture")
        if mc_window is None:
            self.fail("Failed to get Movie Capture window")
        else:
            capture_settings_widget = self._movie_capture_ext._window._capture_settings_widget

            default_fps = capture_settings_widget._animation_fps_model.get_current_fps()
            capture_settings_widget._ui_kit_combobox_fps.model.get_item_value_model(None, 0).as_int = 1
            new_fps = capture_settings_widget._animation_fps_model.get_current_fps()
            self.assertNotEqual(default_fps, new_fps)

            # test start time will not be greater than end time, and vice versa
            capture_settings_widget._ui_kit_combobox_range.model.get_item_value_model(None, 0).as_int = 1
            self.assertEqual(capture_settings_widget._ui_kit_capture_range_input_seconds.visible, True)
            self.assertEqual(capture_settings_widget._ui_kit_capture_range_input_frames.visible, False)
            default_start_time = capture_settings_widget._ui_start_time_input.value
            default_end_time = capture_settings_widget._ui_end_time_input.value
            capture_settings_widget._ui_start_time_input.value = default_end_time + 0.1
            self.assertEqual(capture_settings_widget._ui_start_time_input.value, default_end_time)
            capture_settings_widget._ui_start_time_input.value = default_start_time
            capture_settings_widget._ui_end_time_input.value = default_start_time - 0.1
            self.assertEqual(capture_settings_widget._ui_end_time_input.value, default_start_time)
            capture_settings_widget._ui_end_time_input.value = default_end_time

            # test start frame will not be greater than end frame, and vice versa
            capture_settings_widget._ui_kit_combobox_range.model.get_item_value_model(None, 0).as_int = 0
            self.assertEqual(capture_settings_widget._ui_kit_capture_range_input_seconds.visible, False)
            self.assertEqual(capture_settings_widget._ui_kit_capture_range_input_frames.visible, True)
            default_start_frame = capture_settings_widget._ui_start_frame_input.value
            default_end_frame = capture_settings_widget._ui_end_frame_input.value
            capture_settings_widget._ui_start_frame_input.value = default_end_frame + 1
            self.assertEqual(capture_settings_widget._ui_start_frame_input.value, default_end_frame)
            capture_settings_widget._ui_start_frame_input.value = default_start_frame
            capture_settings_widget._ui_end_frame_input.value = default_start_frame - 1
            self.assertEqual(capture_settings_widget._ui_end_frame_input.value, default_start_frame)

            # test resolution
            self.assertEqual(capture_settings_widget._res_linked, True)
            ## test 16:9
            capture_settings_widget._ui_res_width_input.value = 1280
            self.assertEqual(capture_settings_widget._ui_res_height_input.value, 720)
            capture_settings_widget._ui_res_height_input.value = 1080
            self.assertEqual(capture_settings_widget._ui_res_width_input.value, 1920)
            ## test to break the link between width and height
            capture_settings_widget._on_res_link_clicked()
            self.assertEqual(capture_settings_widget._res_linked, False)
            for _ in range(10):
                await omni.kit.app.get_app().next_update_async()
            capture_settings_widget._ui_res_width_input.value = 1280
            self.assertEqual(capture_settings_widget._ui_res_height_input.value, 1080)
            capture_settings_widget._ui_res_height_input.value = 1000
            self.assertEqual(capture_settings_widget._ui_res_width_input.value, 1280)
            ## test to restore the link between width and height
            capture_settings_widget._on_res_link_clicked()
            self.assertEqual(capture_settings_widget._res_linked, True)
            for _ in range(10):
                await omni.kit.app.get_app().next_update_async()
            ## test 4:3
            capture_settings_widget._ui_kit_res_ratio.model.get_item_value_model(None, 0).as_int = 2
            capture_settings_widget._ui_res_width_input.value = 1280
            self.assertEqual(capture_settings_widget._ui_res_height_input.value, 960)
            capture_settings_widget._ui_res_height_input.value = 1440
            self.assertEqual(capture_settings_widget._ui_res_width_input.value, 1920)
            ## set resolution to HD, it should be 1920x1080
            capture_settings_widget._ui_kit_combobox_res_type.model.get_item_value_model(None, 0).as_int = 0
            self.assertEqual(capture_settings_widget._ui_res_width_input.value, 1920)
            self.assertEqual(capture_settings_widget._ui_res_height_input.value, 1080)

            # test motion blur frame shutter open will not be greater than close, and vice versa
            render_settings_widget = self._movie_capture_ext._window._render_settings_widget
            render_model = render_settings_widget._render_model
            items = render_model.get_item_children()
            path_tracing_index = -1
            for index, render_item in enumerate(items):
                if render_item.render_info.mode == "PathTracing":
                    path_tracing_index = index
                    break
            self.assertNotEqual(path_tracing_index, -1, "Path Tracing should be in the render preset list")
            render_settings_widget._ui_kit_render_preset.model.get_item_value_model(None, 0).as_int = path_tracing_index
            default_fso = render_settings_widget._ui_ptmb_fso_input.value
            default_fsc = render_settings_widget._ui_ptmb_fsc_input.value
            render_settings_widget._ui_ptmb_fso_input.value = default_fsc + 0.01
            self.assertEqual(render_settings_widget._ui_ptmb_fso_input.value, default_fsc)
            render_settings_widget._ui_ptmb_fso_input.value = default_fso
            render_settings_widget._ui_ptmb_fsc_input.value = default_fso - 0.01
            self.assertEqual(render_settings_widget._ui_ptmb_fsc_input.value, default_fso)
            render_settings_widget._ui_ptmb_fso_input.value = -1.0
            render_settings_widget._ui_ptmb_fsc_input.value = 1.0

            # set values for readback verification
            capture_settings_widget._ui_end_frame_input.value = 101
            capture_settings_widget._ui_start_frame_input.value = 1

            # readback and verify
            capture_options, farm_options = self._movie_capture_ext._window._read_kit_capture_options(False)
            self.assertEqual(capture_options.fps, 24)
            self.assertEqual(capture_options.start_frame, 1)
            self.assertEqual(capture_options.end_frame, 101)
            self.assertEqual(capture_options.res_width, 1920)
            self.assertEqual(capture_options.res_height, 1080)
            self.assertEqual(capture_options.render_preset, 0)
            self.assertEqual(capture_options.ptmb_fso, -1.0)
            self.assertEqual(capture_options.ptmb_fsc, 1.0)

    async def test_set_ui_values_3_sunstudy(self):
        # The Sunstudy movie type exists only when omni.kit.environment.sunstudy is enabled (it is optional, and absent
        # from Kit 111 builds and registries); selecting it otherwise also breaks the next test's movie-type index.
        if not omni.kit.app.get_app().get_extension_manager().is_extension_enabled("omni.kit.environment.sunstudy"):
            self.skipTest("omni.kit.environment.sunstudy is not available")
        self._movie_capture_ext.show_window(None, True)
        mc_window = omni.ui.Workspace.get_window("Movie Capture")
        if mc_window is None:
            self.fail("Failed to get Movie Capture window")
        else:
            capture_settings_widget = self._movie_capture_ext._window._capture_settings_widget
            # switch to sunstudy ui
            capture_settings_widget._ui_kit_combobox_movie_type.model.get_item_value_model(None, 0).as_int = 1
            for _ in range(2):
                await omni.kit.app.get_app().next_update_async()

            self.assertEqual(capture_settings_widget._ui_capture_range_sunstudy.visible, True)
            self.assertEqual(capture_settings_widget._ui_capture_range_sequence.visible, False)
            # 2 minutes 10 seconds is 130 seconds
            capture_settings_widget._ui_sunstudy_movie_length_minutes_input.value = 2
            capture_settings_widget._ui_sunstudy_movie_length_seconds_input.value = 10

            capture_options, farm_options = self._movie_capture_ext._window._read_kit_capture_options(False)
            self.assertEqual(capture_options.movie_type, 1)
            self.assertEqual(capture_options.sunstudy_movie_length_in_seconds, 130)

    async def test_set_ui_values_4_render_product_and_ext_settings(self):
        self._movie_capture_ext.show_window(None, True)
        mc_window = omni.ui.Workspace.get_window("Movie Capture")
        if mc_window is None:
            self.fail("Failed to get Movie Capture window")
        else:
            render_settings_widget = self._movie_capture_ext._window._render_settings_widget
            # switch to PT mode to show render product options
            render_settings_widget._ui_kit_render_preset.model.get_item_value_model(None, 0).as_int = 1
            self.assertEqual(render_settings_widget._ui_render_product_input_area.visible, False)
            render_settings_widget._ui_use_render_product_check.model.as_bool = True
            for _ in range(2):
                await omni.kit.app.get_app().next_update_async()

            # Handle the message box to enable render product extentions
            title = "Movie Capture - enable render product extentions"
            msg_wnd = omni.ui.Workspace.get_window(title)
            if msg_wnd is not None:
                # msg_wnd.visible = False
                ok_widget = ui_test.find(f"{title}//Frame/**/Button[*].text=='Yes'")
                if ok_widget is not None:
                    await ok_widget.click()
                    for _ in range(2):
                        await omni.kit.app.get_app().next_update_async()
                    title = "Movie Capture - render product enable results"
                    msg_wnd = omni.ui.Workspace.get_window(title)
                    if msg_wnd is not None:
                        msg_wnd.visible = False
                    for _ in range(2):
                        await omni.kit.app.get_app().next_update_async()

            # hide the render product notes message box
            title = "Movie Capture - render product notes"
            msg_wnd = omni.ui.Workspace.get_window(title)
            if msg_wnd is None:
                carb.log_warn("Failed to find the render product notes window to close")
            else:
                msg_wnd.visible = False
            self.assertEqual(render_settings_widget._ui_render_product_input_area.visible, True)

            # set capture options via extension's settings
            self._settings.set(DEFAULT_RENDER_PRESET_SETTING_PATH, "PathTracing")
            self._settings.set(DEFAULT_SPP_PER_ITERATION_SETTING_PATH, 4)
            self._settings.set(DEFAULT_SPP_PER_SUBFRAME_SETTING_PATH, 128)
            self._settings.set(DEFAULT_SUBFRAME_PER_FRAME_SETTING_PATH, 8)
            self._settings.set(DEFAULT_FRAME_SHUTTER_OPEN_SETTING_PATH, -0.5)
            self._settings.set(DEFAULT_FRAME_SHUTTER_CLOSE_SETTING_PATH, 0.5)

            # if we don't choose a render product, then there will be no actual render product
            capture_options, farm_options = self._movie_capture_ext._window._read_kit_capture_options(False)
            self.assertEqual(len(capture_options.render_product), 0)
            self.assertEqual(capture_options.file_type, ".exr")
            self.assertEqual(capture_options.render_preset, 0)
            self.assertEqual(capture_options.spp_per_iteration, 4)
            self.assertEqual(capture_options.path_trace_spp, 128)
            self.assertEqual(capture_options.ptmb_subframes_per_frame, 8)
            self.assertEqual(capture_options.ptmb_fso, -0.5)
            self.assertEqual(capture_options.ptmb_fsc, 0.5)

            # Create a new render product
            action_registry = omni.kit.actions.core.get_action_registry()
            action_registry.execute_action("omni.kit.menu.aov", "create_single_aov")
            # Make sure the render product is created
            await self.assertTrueWithRetry(
                lambda: omni.usd.get_context().get_stage().GetPrimAtPath("/Render/RenderView") is not None
            )

            # Choose the new render product
            await self.wait_n_updates(10)
            render_settings_widget._refresh_render_products()
            render_product_model = render_settings_widget._ui_render_product.model
            for index, item in enumerate(render_product_model.get_item_children()):
                if render_product_model.get_item_value_model(item).as_string == "/Render/RenderView":
                    render_product_model.get_item_value_model(None, 0).set_value(index)
            capture_options, _ = self._movie_capture_ext._window._read_kit_capture_options(False)
            self.assertEqual(capture_options.render_product, "/Render/RenderView")
            self.assertEqual(capture_options.file_type, ".exr")

            with patch.object(omni.kit.capture.viewport.CaptureExtension, "start") as mock_start_capture:
                self._movie_capture_ext._window._output_settings_widget._on_capture_current_frame_clicked()
                mock_start_capture.assert_called_once()

                # Verify the camera target in render product is set to the camera in capture options
                stage = omni.usd.get_context().get_stage()
                usd_rp = UsdRender.Product(stage.GetPrimAtPath(capture_options.render_product))
                self.assertIsNotNone(usd_rp)
                came_rel = usd_rp.GetCameraRel()

                current_targets = came_rel.GetTargets()
                self.assertEqual(current_targets, [capture_options.camera])

    async def test_set_ui_values_5_rt2_hides_unsupported_settings(self):
        # OMPE-68149: both settings are hidden and not forwarded to capture options for RT 2.0.
        self._movie_capture_ext.show_window(None, True)
        mc_window = omni.ui.Workspace.get_window("Movie Capture")
        self.assertIsNotNone(mc_window, "Failed to get Movie Capture window")
        render_settings_widget = self._movie_capture_ext._window._render_settings_widget

        rt2_render = RenderInfo(
            "rtx",
            "RealTimePathTracing",
            "RTX - Real-Time 2.0",
            omni.kit.capture.viewport.CaptureRenderPreset.REAL_TIME_PATHTRACING,
            "Real-Time 2.0 (Preview)",
        )
        rt1_render = RenderInfo(
            "rtx",
            "RaytracedLighting",
            "RTX - Real-Time",
            omni.kit.capture.viewport.CaptureRenderPreset.RAY_TRACE,
            "Real-Time",
        )

        original_render = render_settings_widget._render_model._selected_render
        original_wait = render_settings_widget._ui_wait_for_render_resolve_time_input.value
        original_settle = render_settings_widget._ui_common_settle_latency_input.value
        try:
            # RT2 hides both settings; RT1 keeps them visible
            render_settings_widget._on_render_preset_selection_changed(rt2_render)
            self.assertFalse(render_settings_widget._ui_kit_realtime_settings_area.visible)
            self.assertFalse(render_settings_widget._ui_kit_common_render_settings_area.visible)
            render_settings_widget._on_render_preset_selection_changed(rt1_render)
            self.assertTrue(render_settings_widget._ui_kit_realtime_settings_area.visible)
            self.assertTrue(render_settings_widget._ui_kit_common_render_settings_area.visible)

            # RT2 must not forward the hidden values to the capture options; RT1 still does
            render_settings_widget._ui_wait_for_render_resolve_time_input.value = 7
            render_settings_widget._ui_common_settle_latency_input.value = 9
            has_wait_option = hasattr(
                omni.kit.capture.viewport.capture_options.CaptureOptions(),
                "rt_wait_for_render_resolve_in_seconds",
            )

            options = omni.kit.capture.viewport.capture_options.CaptureOptions()
            render_settings_widget._render_model._selected_render = rt2_render
            self.assertTrue(render_settings_widget.collect_settings(options))
            self.assertEqual(options.real_time_settle_latency_frames, 0)
            if has_wait_option:
                self.assertEqual(options.rt_wait_for_render_resolve_in_seconds, 0)

            options = omni.kit.capture.viewport.capture_options.CaptureOptions()
            render_settings_widget._render_model._selected_render = rt1_render
            self.assertTrue(render_settings_widget.collect_settings(options))
            self.assertEqual(options.real_time_settle_latency_frames, 9)
            if has_wait_option:
                self.assertEqual(options.rt_wait_for_render_resolve_in_seconds, 7)
        finally:
            render_settings_widget._render_model._selected_render = original_render
            render_settings_widget._ui_wait_for_render_resolve_time_input.value = original_wait
            render_settings_widget._ui_common_settle_latency_input.value = original_settle
            render_settings_widget._on_render_preset_selection_changed(original_render)
