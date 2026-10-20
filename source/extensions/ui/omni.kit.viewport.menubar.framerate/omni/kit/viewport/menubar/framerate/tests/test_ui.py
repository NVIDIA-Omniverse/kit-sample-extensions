# Copyright (c) 2021-2023, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#
import asyncio
from pathlib import Path

import carb
import omni.kit.app
import omni.kit.ui_test as ui_test
from omni.kit.ui_test import Vec2
from omni.ui.tests.test_base import OmniUiTest

EXT_TEST_PATH = Path(carb.tokens.get_tokens_interface().resolve("${omni.kit.viewport.menubar.framerate}")).absolute()
TEST_DATA_PATH = EXT_TEST_PATH.joinpath("data", "tests")
TEST_GOLDEN_IMAGE_PATH = TEST_DATA_PATH.joinpath("golden_images")
TEST_WIDTH, TEST_HEIGHT = 600, 400


async def _wait_for_viewport_frames(frames: int = 3):
    """Kit 111: the viewport renders the (empty) stage with OVRTX, starting ~0.4 s after startup. Wait for presented
    frames so a capture doesn't race the first one (black before, rendered after). Kit 110's test viewport has no
    renderer and never presents a frame, so only wait on Kit 111+."""
    if float(omni.kit.app.get_app().get_kit_version_short()) < 111.0:
        return
    from omni.kit.viewport.utility import get_active_viewport

    viewport = get_active_viewport()
    if viewport:
        await asyncio.wait_for(viewport.wait_for_rendered_frames(frames), timeout=30)


class TestSettingMenuWindow(OmniUiTest):
    async def setUp(self):
        await self.create_test_area(width=TEST_WIDTH, height=TEST_HEIGHT, block_devices=False)
        await self.wait_frames()
        await _wait_for_viewport_frames()

    async def finalize_test(self, golden_img_dir: Path = TEST_GOLDEN_IMAGE_PATH, **kwargs):
        await _wait_for_viewport_frames()
        await super().finalize_test(golden_img_dir=golden_img_dir, **kwargs)

    # After running each test
    async def tearDown(self):
        await super().tearDown()
        await self.wait_frames()

    async def wait_frames(self, n_frames: int = 5):
        app = omni.kit.app.get_app()
        for _ in range(n_frames):
            await app.next_update_async()

    async def test_menuitem_created(self):
        """Test creation of the menubar item."""
        await ui_test.emulate_mouse_move_and_click(Vec2(TEST_WIDTH / 2, TEST_HEIGHT / 2))
        await self.finalize_test(golden_img_dir=TEST_GOLDEN_IMAGE_PATH)

    async def test_menu_item_clicked(self):
        """Test clicking the menu item portion opens the drop down."""
        await ui_test.emulate_mouse_move_and_click(Vec2(TEST_WIDTH - 25, 40))
        await self.finalize_test(golden_img_dir=TEST_GOLDEN_IMAGE_PATH)
