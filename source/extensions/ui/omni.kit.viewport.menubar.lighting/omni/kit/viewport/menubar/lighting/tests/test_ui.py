# Copyright (c) 2021-2022, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#
from pathlib import Path

import carb
import omni.kit.actions.core
import omni.kit.app
import omni.kit.ui_test as ui_test
from omni.kit.ui_test import Vec2
from omni.ui.tests.test_base import OmniUiTest

EXT_TEST_PATH = Path(carb.tokens.get_tokens_interface().resolve("${omni.kit.viewport.menubar.lighting}")).absolute()
TEST_DATA_PATH = EXT_TEST_PATH.joinpath("data", "tests")
TEST_USD_PATH = TEST_DATA_PATH.joinpath("scenes")
TEST_GOLDEN_IMAGE_PATH = TEST_DATA_PATH.joinpath("golden_images")
TEST_USD_RIGS_PATH = TEST_DATA_PATH.joinpath("usd_files")
TEST_WIDTH, TEST_HEIGHT = 600, 400


class TestSettingMenuWindow(OmniUiTest):
    async def setUp(self):
        await self.create_test_area(width=TEST_WIDTH, height=TEST_HEIGHT, block_devices=False)
        await self.wait_n_updates()

    # After running each test
    async def tearDown(self):
        await super().tearDown()
        await self.wait_n_updates()

    async def wait_n_updates(self, n_frames: int = 5):
        await super().wait_n_updates(n_frames)

    async def test_menuitem_created(self):
        """Test creation of the menubar item."""
        await ui_test.emulate_mouse_move_and_click(Vec2(TEST_WIDTH / 2, TEST_HEIGHT / 2))
        await self.finalize_test(golden_img_dir=TEST_GOLDEN_IMAGE_PATH)

    async def test_menu_item_clicked(self):
        """Test clicking the menu item portion opens the drop down."""
        await ui_test.emulate_mouse_move_and_click(Vec2(TEST_WIDTH - 75, 40))
        await self.finalize_test(golden_img_dir=TEST_GOLDEN_IMAGE_PATH)

    async def test_menu_item_set_to_stage(self):
        """Test clicking the menu item portion opens the drop down and clicks camera + stage properly."""
        try:

            async def run_menu_click_test(y_pos: int, golden_img_name: str):
                await ui_test.emulate_mouse_move_and_click(Vec2(TEST_WIDTH / 2, TEST_HEIGHT / 2))
                await ui_test.emulate_mouse_move_and_click(Vec2(TEST_WIDTH - 75, 40))
                await ui_test.emulate_mouse_move_and_click(Vec2(TEST_WIDTH - 75, y_pos))
                await ui_test.emulate_mouse_move_and_click(Vec2(TEST_WIDTH / 2, TEST_HEIGHT / 2))
                await ui_test.emulate_mouse_move_and_click(Vec2(TEST_WIDTH - 75, 40))
                await self.capture_and_compare(golden_img_dir=TEST_GOLDEN_IMAGE_PATH, golden_img_name=golden_img_name)
                await self.wait_n_updates()

            await run_menu_click_test(105, "test_menu_item_set_to_camera.png")
            await run_menu_click_test(130, "test_menu_item_set_to_stage.png")

        finally:
            await self.finalize_test_no_image()
            default_rig = carb.settings.get_settings().get("/exts/omni.kit.viewport.menubar.lighting/defaultRig")
            ar = omni.kit.actions.core.get_action_registry()
            set_lighting_mode_rig = ar.get_action("omni.kit.viewport.menubar.lighting", "set_lighting_mode_rig")
            set_lighting_mode_rig.execute(default_rig)

    async def test_menu_item_custom_rig_path(self):
        """Test clicking the menu item portion opens the drop down and show custom items."""
        settings = carb.settings.get_settings()
        rig_key = "/exts/omni.kit.viewport.menubar.lighting/rigs"
        dflt_value = settings.get(rig_key)

        try:
            settings.set(rig_key, str(TEST_DATA_PATH.joinpath("blank_light_rigs").absolute()))
            await ui_test.emulate_mouse_move_and_click(Vec2(TEST_WIDTH / 2, TEST_HEIGHT / 2))
            await self.wait_n_updates()
            await ui_test.emulate_mouse_move_and_click(Vec2(TEST_WIDTH - 75, 40))
            await self.wait_n_updates()
            await self.finalize_test(golden_img_dir=TEST_GOLDEN_IMAGE_PATH)
        finally:
            settings.set(rig_key, dflt_value)

    async def test_stage_open_with_notification(self):
        """Test opening a stage with no lights shows a notification."""
        settings = carb.settings.get_settings()
        dflt_value = settings.set("/exts/omni.kit.viewport.menubar.lighting/notificationDuration", 2)
        await self.wait_n_updates()
        try:
            usd_path = TEST_USD_PATH.joinpath(f"no_lights.usda")
            await omni.usd.get_context().open_stage_async(str(usd_path))
            await self.wait_n_updates(60)
            await self.finalize_test(golden_img_dir=TEST_GOLDEN_IMAGE_PATH)
            await self.wait_n_updates()
        finally:
            settings.set("/exts/omni.kit.viewport.menubar.lighting/notificationDuration", 0)

    async def test_stage_open_with_no_notification(self):
        """Test opening a stage in memory with no lights shows no notification."""
        settings = carb.settings.get_settings()
        dflt_value = settings.set("/exts/omni.kit.viewport.menubar.lighting/notificationDuration", 1)
        await self.wait_n_updates()
        try:
            await omni.usd.get_context().new_stage_async()
            await self.wait_n_updates(60)
            await self.finalize_test(golden_img_dir=TEST_GOLDEN_IMAGE_PATH)
            await self.wait_n_updates()
        finally:
            settings.set("/exts/omni.kit.viewport.menubar.lighting/notificationDuration", 0)

    async def test_show_hide_item(self):
        """Test showing and hiding the menbar item doesn't cause errors"""

        settings = carb.settings.get_settings()
        usd_context = omni.usd.get_context()

        await usd_context.new_stage_async()
        settings.set("/persistent/exts/omni.kit.viewport.menubar.lighting/visible", False)
        await self.wait_n_updates()

        await usd_context.new_stage_async()
        settings.set("/persistent/exts/omni.kit.viewport.menubar.lighting/visible", True)
        await self.wait_n_updates()

        await usd_context.new_stage_async()
        settings.set("/persistent/exts/omni.kit.viewport.menubar.lighting/visible", False)
        await self.wait_n_updates()

        await usd_context.new_stage_async()
        settings.set("/persistent/exts/omni.kit.viewport.menubar.lighting/visible", True)
        await self.wait_n_updates()

        await self.finalize_test_no_image()
