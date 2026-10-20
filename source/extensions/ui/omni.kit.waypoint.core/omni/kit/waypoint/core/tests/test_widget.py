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

import omni.kit.app
import omni.kit.ui_test as ui_test
import omni.ui as ui
from omni.kit.test_suite.helpers import wait_stage_loading
from omni.kit.ui_test import Vec2
from omni.kit.waypoint.core import WaypointBrowserWidget, WaypointDelegate, WaypointModel
from omni.kit.waypoint.core import get_instance as get_waypoint_instance
from omni.ui.tests.test_base import OmniUiTest
from pxr import Usd

CURRENT_PATH = Path(__file__).parent
TEST_DATA_PATH = CURRENT_PATH.parent.parent.parent.parent.parent.joinpath("data").joinpath("tests")
CAMERA_PRIM_PATH = "/OmniverseKit_Persp"


class TestWaypointWidget(OmniUiTest):
    # Before running each test
    async def setUp(self):
        await super().setUp()
        self._context = omni.usd.get_context()

        await self._context.new_stage_async()
        await self._context.open_stage_async(f"{TEST_DATA_PATH}/stage/cubes_with_waypoints.usda")
        await wait_stage_loading()

        self._instance = get_waypoint_instance()

        self._golden_img_dir = TEST_DATA_PATH.absolute().joinpath("golden_img").absolute()
        self._waypoint_model = WaypointModel()
        self._delegate = WaypointDelegate(self._waypoint_model)

        self._window = await self.create_test_window(width=500, height=600, block_devices=False)
        with self._window.frame:
            self._browser_widget = WaypointBrowserWidget(model=self._waypoint_model, delegate=self._delegate)

        await self.docked_test_window(self._window, width=500, height=600, block_devices=False)

    # After running each test
    async def tearDown(self):
        self._instance.editing_waypoint = None
        self._browser_widget.destroy()
        self._window.visible = False
        self._window = False
        # await self._context.new_stage_async()
        await super().tearDown()

    async def test_1_startup(self):
        """Testing general look of BrowserWidget"""

        await self._move_away()
        await self.finalize_test("startup")

    async def test_2_hover(self):
        await ui_test.emulate_mouse_move(Vec2(80, 50))
        for i in range(4):
            await omni.kit.app.get_app().next_update_async()
        await self.finalize_test("hover")

    async def test_3_edit(self):
        await self._move_edit_icon(click=False)
        await self.finalize_test("edit")

    async def test_4_edit_cancel(self):
        await self._move_edit_icon()
        await ui_test.human_delay(10)

        # Right click should have no effect, since edit is live.
        await ui_test.emulate_mouse_click(right_click=True)

        # Click on "Cancel"
        await ui_test.emulate_mouse_move_and_click(Vec2(136, 55))
        for i in range(4):
            await omni.kit.app.get_app().next_update_async()

        await self.finalize_test("edit_cancel")

    async def test_5_edit_apply(self):
        await self._move_edit_icon()
        # Click on "Apply"
        await ui_test.emulate_mouse_move_and_click(Vec2(36, 55))
        await ui_test.human_delay(20)
        # TODO: generate different golden image with different kit sdk
        # await self.finalize_test("edit_apply")

    async def test_6_edit_add(self):
        await self._move_edit_icon()
        await ui_test.human_delay(4)

        # Move the camera
        stage = self._context.get_stage()
        edit_context = Usd.EditContext(stage, Usd.EditTarget(stage.GetSessionLayer()))
        with edit_context:
            camera_prim = stage.GetPrimAtPath(CAMERA_PRIM_PATH)
            camera_prim.GetAttribute("xformOp:translate").Set((1.0, 1.0, 1.0))

        await ui_test.human_delay(20)

        # Click on "Add"
        await ui_test.emulate_mouse_move_and_click(Vec2(86, 45))
        await ui_test.human_delay(4)

        while True:
            creating_prompt = ui.Workspace.get_window("Please Wait")
            if not creating_prompt or not creating_prompt.visible:
                await ui_test.human_delay(4)
                break
            await omni.kit.app.get_app().next_update_async()

        self.assertEqual(len(self._instance.get_waypoints()), 3)
        # TODO: generate different golden image with different kit sdk
        # await self.finalize_test("edit_add")

    async def test_7_edit_add_duplicate(self):
        await self._move_edit_icon()
        await ui_test.human_delay(4)

        # Click on "Add"
        await ui_test.emulate_mouse_move_and_click(Vec2(86, 45))
        await ui_test.human_delay(20)

        self.assertEqual(len(self._instance.get_waypoints()), 2)

        await self.finalize_test("edit_add_duplicate")

    async def test_8_delete(self):
        await ui_test.emulate_mouse_move_and_click(Vec2(155, 70))
        await omni.kit.app.get_app().next_update_async()

        await self.finalize_test("delete")

    async def test_9_right_click(self):
        await ui_test.emulate_mouse_move(Vec2(80, 50))
        await ui_test.human_delay(10)

        await ui_test.emulate_mouse_click(right_click=True)

        # Note: the base delegate does not provide a context menu, so it will just hide the hover icons.
        await self.finalize_test("right_click")

    async def finalize_test(self, golden_img_name: str, threshold=None):
        await super().finalize_test(
            threshold=threshold, golden_img_dir=self._golden_img_dir, golden_img_name=golden_img_name + ".png"
        )

    async def _move_away(self):
        await ui_test.emulate_mouse_move(Vec2(-50, -50))

    async def _move_edit_icon(self, click=True):
        edit_icon_pos = Vec2(155, 38)

        # Move the mouse first so the button is visible.
        await ui_test.emulate_mouse_move(edit_icon_pos)
        await ui_test.human_delay(2)

        # Then click.
        if click:
            await ui_test.emulate_mouse_move_and_click(edit_icon_pos)
            await ui_test.human_delay(2)
