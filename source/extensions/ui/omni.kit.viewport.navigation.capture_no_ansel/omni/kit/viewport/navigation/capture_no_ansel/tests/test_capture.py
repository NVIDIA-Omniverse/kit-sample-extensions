import asyncio
import os
import traceback
from pathlib import Path

import carb.input
import carb.settings
import omni.client
import omni.kit.app
import omni.usd
from omni.kit.viewport.utility import get_active_viewport_and_window
from omni.ui.tests.compare_utils import CompareError, compare
from omni.ui.tests.test_base import OmniUiTest

from ..utils import capture_regular

CURRENT_PATH = Path(__file__).parent
TEST_DATA_PATH = CURRENT_PATH.parent.parent.parent.parent.parent.parent.joinpath("data").joinpath("tests")
TEST_WIDTH, TEST_HEIGHT = 800, 600
SETTING_CAPTURE_VIEWPORT_ONLY = "/persistent/app/captureFrame/viewport"
SETTING_CAPTURE_PATH = "/persistent/app/captureFrame/path"

_DEFAULT_SCREENSHOT_PATH = carb.settings.get_settings().get(SETTING_CAPTURE_PATH)


async def wait_stage_loading(usd_context=omni.usd.get_context()):
    while True:
        _, files_loaded, total_files = usd_context.get_stage_loading_status()
        if files_loaded or total_files:  # pragma: no cover
            await omni.kit.app.get_app().next_update_async()
            continue
        break

    for _ in range(2):
        await omni.kit.app.get_app().next_update_async()


async def open_stage(path: str, usd_context=omni.usd.get_context()):
    await usd_context.open_stage_async(path)
    await wait_stage_loading(usd_context)


class TestCapture(OmniUiTest):  # pragma: no cover

    async def setUp(self):
        self._golden_img_dir = TEST_DATA_PATH.absolute().joinpath("golden_img").absolute()
        self._settings = carb.settings.get_settings()

        # Viewport setting: no title bar, fill frame
        viewport_api, viewport_window = get_active_viewport_and_window()
        await self.docked_test_window(window=viewport_window, width=TEST_WIDTH, height=TEST_HEIGHT, block_devices=False)
        for i in range(4):
            await omni.kit.app.get_app().next_update_async()

        # load stage
        await open_stage(f"{TEST_DATA_PATH}/stage/test_cubes.usda")
        await wait_stage_loading()

    async def tearDown(self):
        await self.finalize_test_no_image()
        await omni.usd.get_context().close_stage_async()
        await super().tearDown()

    async def test_general_all(self):
        self._settings.set(SETTING_CAPTURE_VIEWPORT_ONLY, False)
        self._capture_name = "capture_general_all"
        self._capture_ext = ".png"
        capture_regular(self._on_capture_done)
        while self._capture_name is not None:
            await asyncio.sleep(1)

    async def test_capture_custom_directory(self):
        """Saves capture to a custom directory."""
        import tempfile

        capture_dir = tempfile.mktemp()
        self._settings.set("/persistent/app/captureFrame/path", capture_dir)
        self._capture_name = "capture_general_custom_path"
        self._capture_ext = ".png"

        capture_regular(self._on_capture_done)
        while self._capture_name is not None:
            await asyncio.sleep(1)

        self._settings.set("/persistent/app/captureFrame/path", _DEFAULT_SCREENSHOT_PATH)

        self.assertTrue(os.path.exists(capture_dir))
        self.assertTrue(len(os.listdir(capture_dir)))

    async def test_general_viewport(self):
        self._settings.set(SETTING_CAPTURE_VIEWPORT_ONLY, True)
        self._capture_name = "capture_general_viewport"
        self._capture_ext = ".png"
        capture_regular(self._on_capture_done)
        while self._capture_name is not None:
            await asyncio.sleep(1)

    async def _test_capture(self, image_name: str):
        self._capture_name = image_name
        self._capture_ext = ".jpg"
        while self._capture_name is not None:
            await asyncio.sleep(1)

    def _on_capture_done(self, capture_file: str) -> None:
        self.assertIsNotNone(capture_file)
        output_dir = Path(omni.kit.test.get_test_output_path())
        output_file = output_dir.joinpath(self._capture_name + self._capture_ext)

        if self._capture_ext == ".jpg":
            while True:
                result = omni.client.copy(capture_file, str(output_file), behavior=omni.client.CopyBehavior.OVERWRITE)
                if result == omni.client.Result.OK:
                    break

            golden_filename = self._golden_img_dir.joinpath(self._capture_name + self._capture_ext)
            differ_filename = output_dir.joinpath(self._capture_name + ".differmap.png")

            # avoid hung if compare failed
            self._capture_name = None

            self._compare(output_file, golden_filename, differ_filename)
        else:
            self._capture_name = None

    def _compare(self, capture_filename: Path, golden_filename: Path, differ_filename: Path, threshold=200) -> bool:
        try:
            diff = compare(capture_filename, golden_filename, differ_filename)
            self.assertLess(diff, threshold)
            if diff >= threshold:
                print(f"##teamcity[publishArtifacts '{capture_filename} => results']")
                print(f"##teamcity[publishArtifacts '{differ_filename} => results']")
                print(f"##teamcity[publishArtifacts '{golden_filename} => golden']")
            return diff < threshold
        except CompareError as e:
            carb.log_error(f"[omni.ui.tests.compare] Failed to compare images for {capture_filename}. Error: {e}")
            print(f"##teamcity[publishArtifacts '{capture_filename} => results']")
            print(f"##teamcity[publishArtifacts '{differ_filename} => results']")
            print(f"##teamcity[publishArtifacts '{golden_filename} => golden']")
            exc = traceback.format_exc()
            carb.log_error(f"[omni.ui.tests.compare] Traceback:\n{exc}")
            self.assertTrue(False)
            return False
