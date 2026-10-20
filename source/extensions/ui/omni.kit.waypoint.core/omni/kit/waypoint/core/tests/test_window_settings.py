# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
from pathlib import Path

import carb
import omni.kit.app
import omni.kit.ui_test as ui_test
import omni.ui as ui
import omni.usd
from omni.kit.test_suite.helpers import wait_stage_loading
from omni.kit.waypoint.core import get_instance
from omni.ui.tests.test_base import OmniUiTest
from pxr import Gf, UsdGeom

from ..pereference import WaypointPerefenceWindow, WaypointPereference

CURRENT_PATH = Path(__file__).parent
TEST_DATA_PATH = CURRENT_PATH.parent.parent.parent.parent.parent.joinpath("data").joinpath("tests")


class TestWindowSettings(OmniUiTest):
    # Before running each test
    async def setUp(self):
        await super().setUp()

        await omni.usd.get_context().open_stage_async(f"{TEST_DATA_PATH}/stage/cubes_no_waypoints.usda")
        await wait_stage_loading()

        WaypointPereference._restore_defaults("Cameras")
        WaypointPereference._restore_defaults("Render Settings")
        WaypointPereference._restore_defaults("Sunstudy Settings")
        WaypointPereference._restore_defaults("Prim Visibility")

        self._golden_img_dir = TEST_DATA_PATH.absolute().joinpath("golden_img").absolute()
        self._window = WaypointPerefenceWindow()

        for i in range(4):
            await omni.kit.app.get_app().next_update_async()

        layer_window = ui.Workspace.get_window("Layer")
        if layer_window:
            layer_window.visible = False

        # NOTE: This 4px buffer causes a difference around the window when running in dev mode.
        await self.create_test_area(
            width=self._window.frame.computed_width + 4,
            height=self._window.frame.computed_height + 4,
            block_devices=False,
        )
        self._window.position_x = 0
        self._window.position_y = 0

    # After running each test
    async def tearDown(self):
        self._window.visible = False
        self._window.destroy()
        self._window = None
        await super().tearDown()

    async def test_1_startup(self):
        """Testing general look of BrowserWidget"""
        await omni.kit.app.get_app().next_update_async()
        await self.finalize_test("settings")

    async def test_2_disable_capture(self):
        await omni.kit.app.get_app().next_update_async()
        await ui_test.human_delay()
        checkbox = ui_test.find("Waypoint Settings//Frame/**/CheckBox[*].name=='Render Settings Capture Checkbox'")
        await checkbox.click()
        await ui_test.human_delay()
        await self.finalize_test("disable_render_setting_capture")

    async def test_3_disable_recall(self):
        await omni.kit.app.get_app().next_update_async()
        await ui_test.human_delay()
        checkbox = ui_test.find("Waypoint Settings//Frame/**/CheckBox[*].name=='Render Settings Recall Checkbox'")
        await checkbox.click()
        await ui_test.human_delay()
        await self.finalize_test("disable_render_setting_recall")

    async def test_4_reset_setting(self):
        await omni.kit.app.get_app().next_update_async()

        # Disable capture setting (to show the reset)
        await ui_test.human_delay()
        checkbox = ui_test.find("Waypoint Settings//Frame/**/CheckBox[*].name=='Render Settings Capture Checkbox'")
        await checkbox.click()
        await ui_test.human_delay()

        # Reset the capture setting.
        await ui_test.human_delay()
        reset_button = ui_test.find("Waypoint Settings//Frame/**/Rectangle[*].identifier=='Render Settings_reset'")
        self.assertTrue(reset_button.widget.visible)
        await reset_button.click()
        await self.finalize_test("reset_render_setting")

    async def test_5_setting_and_function(self):
        # Original settings
        stage = omni.usd.get_context().get_stage()
        stage.SetEditTarget(stage.GetEditTargetForLocalLayer(stage.GetSessionLayer()))
        camera = UsdGeom.Xformable(stage.GetPrimAtPath("/OmniverseKit_Persp"))

        carb.settings.get_settings().set("/rtx/renderpreset", 1)

        def get_settings():
            camera_trsfm = camera.GetLocalTransformation()
            render = carb.settings.get_settings().get("/rtx/renderpreset")
            sunstudy = stage.GetPrimAtPath("/Environment").GetAttribute("time:current").Get()
            return (camera_trsfm, render, sunstudy)

        def set_settings():
            camera.GetPrim().GetAttribute("xformOp:translate").Set(Gf.Vec3d(99, 99, 99))
            carb.settings.get_settings().set("/rtx/renderpreset", 123)
            stage.GetPrimAtPath("/Environment").GetAttribute("time:current").Set(321)

        org_settings = get_settings()

        # Create a waypoint
        await get_instance().create_waypoint_async()
        waypoint = list(get_instance().get_waypoints())[0]

        # Change settings
        set_settings()
        changed_settings = get_settings()

        self.assertNotEqual(changed_settings, org_settings)
        self.assertTrue(waypoint.is_dirty)

        # Disable recall
        camera_recall = ui_test.find("Waypoint Settings//Frame/**/CheckBox[*].name=='Cameras Recall Checkbox'")
        render_recall = ui_test.find("Waypoint Settings//Frame/**/CheckBox[*].name=='Render Settings Recall Checkbox'")
        sunstudy_recall = ui_test.find(
            "Waypoint Settings//Frame/**/CheckBox[*].name=='Sunstudy Settings Recall Checkbox'"
        )
        await camera_recall.click()
        await render_recall.click()
        await sunstudy_recall.click()

        # Recall
        get_instance().recall_waypoint(waypoint, force=True)

        recalled_settings = get_settings()
        self.assertEqual(recalled_settings, changed_settings)

        # Enable recall
        await camera_recall.click()
        await render_recall.click()
        await sunstudy_recall.click()

        # Recall
        get_instance().recall_waypoint(waypoint, force=True)

        recalled_settings = get_settings()
        self.assertEqual(recalled_settings, org_settings)
        self.assertFalse(waypoint.is_dirty)

        # Disable capture
        render_capture = ui_test.find(
            "Waypoint Settings//Frame/**/CheckBox[*].name=='Render Settings Capture Checkbox'"
        )
        sunstudy_capture = ui_test.find(
            "Waypoint Settings//Frame/**/CheckBox[*].name=='Sunstudy Settings Capture Checkbox'"
        )
        await render_capture.click()
        await sunstudy_capture.click()

        # Create waypoint
        get_instance().delete_waypoint(waypoint)
        await get_instance().create_waypoint_async()

        # Change settings
        set_settings()

        changed_settings = get_settings()
        self.assertNotEqual(changed_settings, org_settings)

        # Recall
        waypoint = list(get_instance().get_waypoints())[0]
        get_instance().recall_waypoint(waypoint, force=True)

        recalled_settings = get_settings()
        self.assertEqual(recalled_settings[0], org_settings[0])
        self.assertEqual(recalled_settings[1:], changed_settings[1:])

        await self.finalize_test_no_image()

    async def finalize_test(self, golden_img_name: str):
        await super().finalize_test(golden_img_dir=self._golden_img_dir, golden_img_name=golden_img_name + ".png")
