# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
import asyncio
from pathlib import Path

import carb.settings
import omni.kit.app
import omni.kit.ui_test as ui_test
import omni.ui as ui
import omni.usd
from carb.input import KeyboardInput
from omni.kit.test_suite.helpers import wait_stage_loading
from omni.kit.waypoint.core.common import CURRENT_TOOL_PATH
from omni.kit.waypoint.core.extension import get_instance
from omni.kit.waypoint.core.widgets.list_window import WaypointListWindow
from omni.ui.tests.test_base import OmniUiTest

CURRENT_PATH = Path(__file__).parent
TEST_DATA_PATH = CURRENT_PATH.parent.parent.parent.parent.parent.joinpath("data").joinpath("tests").absolute()
GOLDEN_IMG_PATH = TEST_DATA_PATH.joinpath("golden_img").joinpath("list_window").absolute()


class TestListWindowBase(OmniUiTest):

    async def setUp(self):
        await super().setUp()

        self._window = ui.Workspace.get_window("Waypoints")
        if self._window is None:
            self._window = WaypointListWindow()
        self._window.visible = True

        for i in range(4):
            await omni.kit.app.get_app().next_update_async()

        layer_window = ui.Workspace.get_window("Layer")
        if layer_window:
            layer_window.visible = False

        await self.create_test_area(
            width=self._window.frame.computed_width + 4,
            height=self._window.frame.computed_height + 4,
            block_devices=False,
        )
        self._window.position_x = 0
        self._window.position_y = 0

        await ui_test.wait_n_updates()

        self._context = omni.usd.get_context()
        await self._context.new_stage_async()

    async def tearDown(self):
        if self._window is not None:
            self._window.visible = False
            self._window = None

        # Clean up the preference window
        ext = get_instance()
        if ext._preference_window is not None:
            ext._preference_window.destroy()
            ext._preference_window = None

        await super().tearDown()

    async def finalize_test(self, golden_img_name: str, threshold=None):
        await super().finalize_test(
            threshold=threshold, golden_img_dir=GOLDEN_IMG_PATH, golden_img_name=golden_img_name + ".png"
        )

    async def _wait_for_waypoint_load(self):
        # This is currently imprecise.
        for i in range(4):
            await omni.kit.app.get_app().next_update_async()


class TestListWindowGeneral(TestListWindowBase):

    async def test_1_startup(self):
        """Test basic startup of list window."""
        await omni.kit.app.get_app().next_update_async()
        await self.finalize_test("lw_startup")

    async def test_2_load_and_playback(self):
        """Test loading a stage with waypoints and playback controls."""
        ext = get_instance()

        await self._context.open_stage_async(f"{TEST_DATA_PATH}/stage/cubes_with_waypoints.usda")
        await wait_stage_loading()
        await self._wait_for_waypoint_load()

        self.assertEqual(len(ext.get_waypoints()), 2)
        self.assertIsNone(self._window.selected_index)

        # Get playback buttons.
        prev_button = ui_test.find("Waypoints//Frame/**/Button[*].name=='previous'")
        self.assertIsNotNone(prev_button)
        next_button = ui_test.find("Waypoints//Frame/**/Button[*].name=='next'")
        self.assertIsNotNone(next_button)
        play_button = ui_test.find("Waypoints//Frame/**/Button[*].name=='play'")
        self.assertIsNotNone(play_button)

        # Test player mode.
        await play_button.click()
        await asyncio.sleep(6)  # Give the player enough time to cycle to the second waypoint (5 seconds)
        await play_button.click()
        await ui_test.human_delay()
        self.assertEqual(self._window.selected_index, 1)

        # Prev button.
        await prev_button.click()
        await ui_test.human_delay()
        self.assertEqual(self._window.selected_index, 0)

        # Next button.
        await next_button.click()
        await ui_test.human_delay()
        self.assertEqual(self._window.selected_index, 1)

        await self.finalize_test("lw_load")

    async def test_3_edit(self):
        """Test edit functionality of list window."""
        ext = get_instance()

        # Locate the "Add" button.
        add_button = ui_test.find("Waypoints//Frame/**/Button[*].name=='add_waypoint'")
        self.assertIsNotNone(add_button)
        self.assertEqual(len(ext.get_waypoints()), 0)

        # Add one.
        await add_button.click()
        while True:
            creating_prompt = ui.Workspace.get_window("Please Wait")
            if not creating_prompt or not creating_prompt.visible:
                await ui_test.human_delay(10)
                break
            await omni.kit.app.get_app().next_update_async()
        self.assertEqual(len(ext.get_waypoints()), 1)

        # Rename
        # Kit 111: the list shows the new waypoint once its thumbnail capture completes (the viewport presents its
        # first OVRTX frame ~30 updates after the stage opens), so wait for the label instead of a fixed delay.
        label = None
        for _ in range(300):
            label = ui_test.find("Waypoints//Frame/**/Label[*].text=='Waypoint_00'")
            if label:
                break
            await omni.kit.app.get_app().next_update_async()
        self.assertIsNotNone(label)
        await label.right_click()
        await ui_test.human_delay(10)
        await ui_test.select_context_menu("Rename Waypoint", None, ui_test.Vec2(10, 10))
        await ui_test.human_delay()
        await ui_test.emulate_char_press("Test")
        await ui_test.emulate_keyboard_press(KeyboardInput.ENTER)

        # Expand Comment
        await label.click()
        await ui_test.human_delay()

        string_field = ui_test.find("Waypoints//Frame/**/StringField[*].name=='Test Comment'")
        await string_field.click()
        await ui_test.human_delay()
        await ui_test.emulate_char_press("Test Comment")
        await ui_test.human_delay()
        await label.click()
        await ui_test.human_delay()
        wp = ext.get_waypoint("Test")
        self.assertEqual(wp.comment, "Test Comment")

        # Hover
        thumbnail = ui_test.find("Waypoints//Frame/**/ImageWithProvider[*].name=='Test Thumbnail'")
        await ui_test.emulate_mouse_move(thumbnail.center)
        await ui_test.human_delay()

    async def test_4_show_preference(self):
        button = ui_test.find("Waypoints//Frame/**/Button[*].name=='show_preference'")
        await button.click()
        await ui_test.human_delay(10)

        window = ui.Workspace.get_window("Waypoint Settings")
        self.assertTrue(window is not None and window.visible)
        await ui_test.human_delay()

        # We have other tests for the visual look of the settings window, hide it.
        window.hide()
        await ui_test.human_delay()

        await self.finalize_test("lw_pref")

    async def test_5_click_close_window(self):
        """Click close button on the window title"""
        pos_right_top_x = ui_test.Vec2(
            self._window.position_x + self._window.width - self._window.padding_x - 7, self._window.position_y + 7
        )
        await ui_test.emulate_mouse_move_and_click(pos_right_top_x, right_click=False, double=False)
        await ui_test.human_delay(10)
        await omni.kit.app.get_app().next_update_async()

        self.assertFalse(self._window.visible)
        await self.finalize_test("lw_closed")

    async def test_6_load_create(self):
        """Test Add Waypoint after loading a scene with predefined waypoints."""
        await self._context.open_stage_async(f"{TEST_DATA_PATH}/stage/cubes_with_waypoints.usda")
        await wait_stage_loading()
        await self._wait_for_waypoint_load()

        ext = get_instance()

        # Verify predefined waypoints
        self.assertEqual(len(ext.get_waypoints()), 2)

        # Locate the "Add" button.
        add_button = ui_test.find("Waypoints//Frame/**/Button[*].name=='add_waypoint'")
        self.assertIsNotNone(add_button)
        settings = carb.settings.get_settings()
        # to make sure the render settings are different
        f_number = settings.get("/rtx/post/dof/fNumber")
        settings.set("/rtx/post/dof/fNumber", f_number + 1)
        await ui_test.human_delay(10)
        # Add a new waypoint.
        await add_button.click()
        while True:
            creating_prompt = ui.Workspace.get_window("Please Wait")
            if not creating_prompt or not creating_prompt.visible:
                await ui_test.human_delay(10)
                break
            await omni.kit.app.get_app().next_update_async()
        self.assertEqual(len(ext.get_waypoints()), 3)
        # TODO: generate different golden image with different kit sdk
        # await self.finalize_test("lw_load_create")

    async def test_7_tool_change(self):
        settings = carb.settings.get_settings()

        # Show the Preference Window (which should be hidden)
        button = ui_test.find("Waypoints//Frame/**/Button[*].name=='show_preference'")
        await button.click()
        await ui_test.human_delay(10)

        window = ui.Workspace.get_window("Waypoint Settings")
        self.assertTrue(window is not None and window.visible)

        await ui_test.human_delay(10)

        settings.set(CURRENT_TOOL_PATH, "None")

        await ui_test.human_delay(10)

        self.assertFalse(window.visible)
        self.assertFalse(self._window.visible)

        # Show the window again to finalize
        self._window.visible = True

        await self.finalize_test("lw_tool_change")


class TestListWindowThumbnail(TestListWindowBase):

    async def setUp(self):
        await super().setUp()

        await self._context.open_stage_async(f"{TEST_DATA_PATH}/stage/cubes_with_waypoints.usda")
        await wait_stage_loading()
        await self._wait_for_waypoint_load()

        ext = get_instance()

        self.thumbnail1 = ui_test.find("Waypoints//Frame/**/ImageWithProvider[*].name=='Waypoint_1 Thumbnail'")
        self.thumbnail2 = ui_test.find("Waypoints//Frame/**/ImageWithProvider[*].name=='Waypoint_2 Thumbnail'")

        self.label1 = ui_test.find("Waypoints//Frame/**/Label[*].text=='Waypoint_1'")
        self.label2 = ui_test.find("Waypoints//Frame/**/Label[*].text=='Waypoint_2'")

        self.wp1 = ext.get_waypoint("Waypoint_1")
        self.wp2 = ext.get_waypoint("Waypoint_2")

    async def test_1_click_thumbnail(self):
        """Click a thumbnail on the WaypointListWindow"""
        await self.thumbnail1.click()

        self.assertEqual(self._window.selected_index, 0)

    async def test_1a_click_thumbnail_expanded_self(self):
        """Click a thumbnail while the comment frame is expanded"""
        # Expand Comment
        await self.label1.click()
        await ui_test.human_delay()
        await omni.kit.app.get_app().next_update_async()

        # Click thumbnail
        await self.thumbnail1.click()
        await ui_test.human_delay()
        await omni.kit.app.get_app().next_update_async()

        self.assertEqual(self._window.selected_index, 0)
        await self.finalize_test("lw_click_expanded_self")

    async def test_1b_click_thumbnail_expanded_another(self):
        """Click a thumbnail while another comment frame is expanded"""
        # Expand Comment
        await self.label2.click()
        await ui_test.human_delay()
        await omni.kit.app.get_app().next_update_async()

        # Click thumbnail
        await self.thumbnail1.click()
        await ui_test.human_delay()
        await omni.kit.app.get_app().next_update_async()

        self.assertEqual(self._window.selected_index, 0)
        await self.finalize_test("lw_click_expanded_another")

    async def test_1c_click_thumbnail_expanded_with_comment(self):
        """Click a thumbnail with comment field expanded"""
        # Expand Comment
        self.wp1.comment = "Waypoint 1 Test Comment"
        await ui_test.human_delay()
        await omni.kit.app.get_app().next_update_async()

        # Click thumbnail
        await self.thumbnail1.click()
        await ui_test.human_delay()
        await omni.kit.app.get_app().next_update_async()

        # self.assertEqual(self._window.selected_index, 0)
        await self.finalize_test("lw_click_expanded_with_comment")

    async def test_1d_click_thumbnail_hovered_edit(self):
        """Click a thumbnail edit hovering button"""
        # Hover
        await ui_test.emulate_mouse_move(self.thumbnail1.center)
        await ui_test.human_delay()
        await omni.kit.app.get_app().next_update_async()

        edit_buttons = ui_test.find_all("Waypoints//Frame/**/Button[*].name=='edit'")

        # Click a Hovering Button
        await ui_test.emulate_mouse_move(edit_buttons[0].center)
        await ui_test.human_delay()
        await ui_test.emulate_mouse_click()
        await omni.kit.app.get_app().next_update_async()

    async def test_1e_click_thumbnail_editing_another(self):
        """Click a thumbnail while editing another waypoint."""
        # Enter edit another
        await ui_test.emulate_mouse_move(self.thumbnail2.center)
        await ui_test.human_delay()
        await omni.kit.app.get_app().next_update_async()

        edit_buttons = ui_test.find_all("Waypoints//Frame/**/Button[*].name=='edit'")
        await ui_test.emulate_mouse_move(edit_buttons[-1].center)
        await ui_test.human_delay()
        await ui_test.emulate_mouse_click()
        await omni.kit.app.get_app().next_update_async()

        # Click thumbnail
        await self.thumbnail1.click()
        await ui_test.human_delay()
        await omni.kit.app.get_app().next_update_async()

        self.assertEqual(self._window.selected_index, 1)

    async def test_2_double_click_thumbnail(self):
        """Double click a thumbnail"""
        # NOTE: Currently, having two click tests in one function affects each other.
        #   Please avoid mixing click test and double_click test in one test unit
        await self.thumbnail2.double_click()
        await ui_test.human_delay()

        self.assertEqual(self._window.selected_index, 1)
        await self.finalize_test("lw_double_click")

    async def test_2a_double_click_thumbnail_expanded_self(self):
        """Double click a thumbnail while comment field is expanded"""
        # Expand Comment
        await self.label2.click()
        await ui_test.human_delay(100)
        await omni.kit.app.get_app().next_update_async()

        # Double-click thumbnail
        await self.thumbnail2.double_click()
        await ui_test.human_delay()

        self.assertEqual(self._window.selected_index, 1)
        await self.finalize_test("lw_double_click_expanded_self")

    async def test_2b_double_click_thumbnail_expanded_another(self):
        """Double click a thumbnail while another waypoint comment field is expanded"""
        # Expand Comment
        await self.label2.click()
        await ui_test.human_delay(100)
        await omni.kit.app.get_app().next_update_async()

        # Double-click thumbnail
        await self.thumbnail1.double_click()
        await ui_test.human_delay()

        self.assertEqual(self._window.selected_index, 0)
        await self.finalize_test("lw_double_click_expanded_another")

    async def test_2c_double_click_thumbnail_expanded_with_comment(self):
        """Double click a thumbnail with comment field expanding"""
        # Expand Comment
        self.wp2.comment = "Waypoint 2 Test Comment"
        await ui_test.human_delay()
        await omni.kit.app.get_app().next_update_async()

        # Click thumbnail
        await self.thumbnail2.double_click()
        await ui_test.human_delay()
        await omni.kit.app.get_app().next_update_async()

        # self.assertEqual(self._window.selected_index, 0)
        await self.finalize_test("lw_double_click_expanded_with_comment")

    async def test_2d_double_click_thumbnail_hovered_edit(self):
        """Click a thumbnail edit hovering button"""
        # Hover
        await ui_test.emulate_mouse_move(self.thumbnail1.center)
        await ui_test.human_delay()
        await omni.kit.app.get_app().next_update_async()

        edit_buttons = ui_test.find_all("Waypoints//Frame/**/Button[*].name=='edit'")

        # Double Click a Hovering Button
        await ui_test.emulate_mouse_move(edit_buttons[0].center)
        await ui_test.human_delay()
        await ui_test.emulate_mouse_click()
        await ui_test.human_delay(1)
        await ui_test.emulate_mouse_click()
        await omni.kit.app.get_app().next_update_async()

        await self.finalize_test("lw_double_click_hovered_edit")

    async def test_2e_double_click_thumbnail_editing_another(self):
        """Click a thumbnail while editing another waypoint."""
        # Enter edit another
        await ui_test.emulate_mouse_move(self.thumbnail2.center)
        await ui_test.human_delay()
        await omni.kit.app.get_app().next_update_async()

        edit_buttons = ui_test.find_all("Waypoints//Frame/**/Button[*].name=='edit'")
        await ui_test.emulate_mouse_move(edit_buttons[-1].center)
        await ui_test.human_delay()
        await ui_test.emulate_mouse_click()
        await ui_test.human_delay(200)
        await omni.kit.app.get_app().next_update_async()

        # Click thumbnail
        await self.thumbnail1.double_click()
        await ui_test.human_delay()
        await omni.kit.app.get_app().next_update_async()

        self.assertEqual(self._window.selected_index, 1)
        await self.finalize_test("lw_double_click_editing_another")

    async def test_3_click_thumbnail_edit(self):
        """Click thumbnail edit hovering button and open edit mode"""
        await self._context.open_stage_async(f"{TEST_DATA_PATH}/stage/cubes_with_waypoints.usda")
        await wait_stage_loading()
        await self._wait_for_waypoint_load()

        waypoint_1_thumbnail = ui_test.find("Waypoints//Frame/**/ImageWithProvider[*].name=='Waypoint_1 Thumbnail'")
        await waypoint_1_thumbnail.click()

        edit_buttons = ui_test.find_all("Waypoints//Frame/**/Button[*].name=='edit'")
        pos = edit_buttons[0].center

        await edit_buttons[0].click()

        self.assertEqual(self._window.selected_index, 0)
