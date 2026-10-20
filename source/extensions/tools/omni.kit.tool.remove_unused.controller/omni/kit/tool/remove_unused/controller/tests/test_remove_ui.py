# Copyright (c) 2022, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

import asyncio
import pathlib

import omni.kit.app
from omni.ui.tests.test_base import OmniUiTest
from pxr import Usd

from ..extension import get_instance as get_controller_inst

EXTENSION_FOLDER_PATH = pathlib.Path(
    omni.kit.app.get_app().get_extension_manager().get_extension_path_by_module(__name__)
)
DATA_DIR = EXTENSION_FOLDER_PATH.joinpath("data")


class TestRemoveUIWindow(OmniUiTest):
    # Before running each test
    async def setUp(self):
        await super().setUp()
        self._golden_img_dir = DATA_DIR.absolute().joinpath("golden_img").absolute()
        self._test_stage = self._open_stage("mat_removal_test")

    # After running each test
    async def tearDown(self):
        await super().tearDown()
        self._test_stage = None

    async def capture_golden_image(self, filename):
        import omni.renderer_capture

        capture_next_frame = omni.renderer_capture.acquire_renderer_capture_interface().capture_next_frame_swapchain
        wait_async_capture = omni.renderer_capture.acquire_renderer_capture_interface().wait_async_capture

        capture_next_frame(str(self._golden_img_dir.joinpath(filename)))

        await omni.kit.app.get_app().next_update_async()

        wait_async_capture()

    # Test the material remover UI
    async def test_popup(self):
        controller = get_controller_inst()
        controller._open_popup_dialog()
        popup = controller._popup

        await self.docked_test_window(window=popup, width=400, height=270)

        # This is here to update the golden image.  NEVER CHECK IN WITH THE FOLLOWING LINE UNCOMMENTED
        # await self.capture_golden_image("test_popup.png")

        await self.finalize_test(use_log=True, golden_img_dir=self._golden_img_dir, golden_img_name="test_popup.png")

    # ============= UTILITY ===============

    def _open_stage(self, stage_name: str, usd_context_name: str = ""):
        usd_context = omni.usd.get_context(usd_context_name)
        path = DATA_DIR.joinpath(stage_name + ".usda")
        usd_context.open_stage(str(path))
        stage = usd_context.get_stage()
        return stage
