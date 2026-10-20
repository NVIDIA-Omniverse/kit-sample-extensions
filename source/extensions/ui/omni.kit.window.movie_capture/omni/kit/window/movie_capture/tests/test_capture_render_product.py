import os
import pathlib
from tempfile import mkdtemp

import carb
import omni.kit.app
import omni.kit.test
import omni.kit.ui_test as ui_test
import omni.ui
import omni.usd
from omni.kit.capture.viewport import CaptureExtension, CaptureOptions, CaptureRenderPreset
from omni.kit.test_suite.helpers import wait_stage_loading
from omni.kit.window.movie_capture import MovieCaptureExtension
from omni.ui.tests.test_base import OmniUiTest

from .test_helper import wait_for_capture_done

DATA_PATH = pathlib.Path(__file__).parent.joinpath("../../../../../data")
TEST_USD_DIR = DATA_PATH.joinpath("tests/usd")
EXPECTED_AOVS = [
    "LdrColor",
    "HdrColor",
    "PtDirectIllumation",
    "PtGlobalIllumination",
    "PtReflections",
    "PtRefractions",
    "PtSelfIllumination",
    "PtBackground",
    "PtWorldNormal",
    "PtWorldPos",
    "PtZDepth",
    "PtVolumes",
]

# Kit 111 EA1: a render-product capture in RTX-Minimal writes no image. The renderer's postprocessing provides no
# tonemap input for the requested LdrColor output ("Cannot populate requested LdrColor output: postprocessing did not
# provide a tonemap input"), so nothing is written. The window offers RTX-Minimal since omni.kit.capture.viewport added
# CaptureRenderPreset.RTX_MINIMAL (Kit 1451c6e0cc, the 110.4 backports). EA2 ticket: OMPE-<to be filed>.
RTX_MINIMAL_RENDER_PRODUCT_SKIP = (
    "RTX-Minimal: a render-product capture writes no image in Kit 111 EA1 (no tonemap input for LdrColor); "
    "EA2 ticket OMPE-<to be filed>"
)


class TestCaptureRenderProduct(OmniUiTest):
    async def setUp(self) -> None:
        await super().setUp()
        self._movie_capture_ext = MovieCaptureExtension().get_instance()
        self._capture_instance = CaptureExtension.get_instance()
        self._capture_instance.options = CaptureOptions()

    async def tearDown(self):
        await super().tearDown()
        self._movie_capture_ext = None
        self._capture_instance.options = CaptureOptions()

    async def test_capture_with_render_product_all_modes(self):
        usd_path = os.path.join(TEST_USD_DIR, "multimatte.usda")
        context = omni.usd.get_context()
        await context.open_stage_async(usd_path)
        await wait_stage_loading()
        for _ in range(2):
            await omni.kit.app.get_app().next_update_async()

        # Show Movie Capture window
        self._movie_capture_ext.show_window(None, True)
        mc_window = omni.ui.Workspace.get_window("Movie Capture")
        self.assertIsNotNone(mc_window, "Failed to get Movie Capture window")
        capture_settings_frame = ui_test.find(f"Movie Capture//Frame/**/CollapsableFrame[*].title=='Capture Settings'")
        capture_settings_frame.widget.collapsed = True

        # Enable render product
        render_settings_widget = self._movie_capture_ext._window._render_settings_widget
        render_settings_widget._ui_use_render_product_check.model.set_value(True)
        for _ in range(2):
            await omni.kit.app.get_app().next_update_async()

        title = "Movie Capture - render product notes"
        msg_wnd = omni.ui.Workspace.get_window(title)
        if msg_wnd is not None:
            msg_wnd.visible = False
            for _ in range(2):
                await omni.kit.app.get_app().next_update_async()

        try:
            # Select the specific render product path
            rp_model = render_settings_widget._ui_render_product.model
            rp_index = None
            for index, item in enumerate(rp_model.get_item_children()):
                if rp_model.get_item_value_model(item).as_string == "/Render/RenderView":
                    rp_index = index
                    rp_model.get_item_value_model(None, 0).set_value(index)
            self.assertIsNotNone(rp_index, "Failed to find render product")

            # Capture render product for every render mode:
            output_settings_widget = self._movie_capture_ext._window._output_settings_widget
            render_model = render_settings_widget._render_model
            items = render_model.get_item_children()[1:]
            rp_model = render_settings_widget._ui_kit_render_preset.model
            saved_index = rp_model.get_item_value_model(None, 0).as_int
            rtx_minimal_preset = getattr(CaptureRenderPreset, "RTX_MINIMAL", None)
            for index, render_item in enumerate(items):
                if not render_item.render_info:
                    continue
                preset = render_item.render_info.capture_render_preset
                if rtx_minimal_preset is not None and preset == rtx_minimal_preset:
                    # A warning, not a skipped subtest: omni.kit.test reports such a test as not passed.
                    carb.log_warn(f"Skipping {render_item.render_info.mode}: {RTX_MINIMAL_RENDER_PRODUCT_SKIP}")
                    continue

                # Select the render mode
                rp_model.get_item_value_model(None, 0).set_value(index + 1)
                for _ in range(10):
                    await omni.kit.app.get_app().next_update_async()

                render_mode = render_item.render_info.mode
                carb.log_info(f"Capture render product for render mode: {render_mode}")

                expected_aovs = EXPECTED_AOVS

                with self.__get_temp_directory(f"rp_{render_mode}") as image_folder:
                    output_settings_widget._ui_kit_path.model.set_value(image_folder)
                    output_settings_widget._ui_kit_default_capture_name.model.set_value(render_mode)
                    for _ in range(10):
                        await omni.kit.app.get_app().next_update_async()

                    output_settings_widget._ui_kit_capture_button.call_clicked_fn()
                    expect_outputs = [self._get_exr_path(image_folder, render_mode, aov) for aov in expected_aovs]
                    await wait_for_capture_done(output_settings_widget._capture_instance, expect_outputs=expect_outputs)
        finally:
            await context.new_stage_async()
            await wait_stage_loading()
            self._movie_capture_ext._clean_up_window()

    def _get_exr_path(self, capture_folder_name, render_mode, aov_channel, index=1):
        exr_path = os.path.join(str(capture_folder_name), f"{render_mode}{index}_" + aov_channel + ".exr")
        return exr_path

    def __get_temp_directory(self, suffix):
        class NoDeleteTempDir:
            def __init__(self, tmpdir):
                carb.log_info(f"Temporary directory created: {tmpdir}")
                self.name = tmpdir

            def __enter__(self, *args, **kwargs):
                return self.name

            def __exit__(self, *args, **kwargs):
                return

        return NoDeleteTempDir(mkdtemp(suffix=f"_{suffix}", dir=omni.kit.test.get_test_output_path()))
