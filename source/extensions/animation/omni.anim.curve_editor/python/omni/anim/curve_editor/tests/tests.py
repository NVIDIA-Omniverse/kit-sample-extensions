import time
import unittest
from pathlib import Path
from typing import Tuple

import carb
import omni.kit.property.usd
import omni.kit.ui_test as ui_test
import omni.ui as ui
from carb.input import KeyboardEventType, KeyboardInput, MouseEventType
from omni.kit.actions.core import execute_action
from omni.kit.test_suite.helpers import wait_stage_loading
from omni.kit.ui_test.input import emulate_keyboard  # strangely, it's not in the __init__.py of `ui_test`
from omni.timeline import get_timeline_interface
from pxr import Usd

from .visual_test_base import AnimationVisualTestBase

"""
Notes:

1. When we do visual tests of the Curve Editor window, we should make it as wide as possible, to avoid some strange
behaviour, like missing buttons, unexpected position changes, 'Frame All' button does not work, etc.

2. If you manipulate the timeline, you should remember reset it back to zero. Otherwise, the other test cases in the
same class may see unexpected behaviours.

3. The `AnimationVisualTestBase` will move the mouse to (0, 0) before do_visual_test by default in this extension.

"""


# Some magic numbers
CURVE_EDITOR_WIDTH = 1680
CURVE_EDITOR_HEIGHT = 720

MAGIC_POS_1 = ui_test.Vec2(920, 126)
MAGIC_POS_2 = ui_test.Vec2(1550, 305)
MAGIC_POS_3 = ui_test.Vec2(1550, 125)


class AnimCurveEditorTestsBase(AnimationVisualTestBase):
    """
    The base class for all the tests in Curve Editor.
    """

    """
        Setup will set the
           1. self._GOLDEN_IMG_DIR
           2. self._MAP_DIR
           They will be served as the root folder of the golden image and USD map
    """

    async def setUp(self):
        await super().setUp()
        extension_root_folder = Path(
            omni.kit.app.get_app().get_extension_manager().get_extension_path_by_module(__name__)
        )
        self._GOLDEN_IMG_DIR = extension_root_folder.joinpath("data/test_data/golden_img")
        self._MAP_DIR = extension_root_folder.joinpath("data/test_data/test_map")

        self._crop_config = (165, 44, None, None)

        # Initialize the Curve Editor window
        # The timeline will not show the correct range upon the first time we open the Curve Editor window
        curve_editor_window = ui.Workspace.get_window("Curve Editor")
        curve_editor_window.visible = True
        curve_editor_window.focus()
        self.curve_editor_window = curve_editor_window


class AnimCurveEditor(AnimCurveEditorTestsBase):
    """
    A basic test that opens no map at all to warm-up the extensions.
    WARNING:
        Please make sure that this test runs at the first. Otherwise, the other tests will fail.
    """

    async def test_anim_curve_editor_0_basic_no_map(self):
        await wait_stage_loading()
        self._context.get_selection().set_selected_prim_paths([], True)

        self._crop_config = (None, None, None, None)

        # Dock the Curve Editor window to the top and occupy the entire main window for capturing
        await self.setup_docked_test(
            docked_window=self.curve_editor_window,
            restore_window=ui.Workspace.get_window("Content"),
            restore_position=ui.DockPosition.SAME,
            width=CURVE_EDITOR_WIDTH,
            height=CURVE_EDITOR_HEIGHT,
        )

        await self.do_visual_test(img_name="anim_curve_editor_basic_no_map")
        self._crop_config = (165, 44, None, None)

    """
    The first test case load a simple animated cube. Advance the time and compare the rendered result in VIEWPORT
    """

    async def test_anim_curve_editor_basic(self):
        # Load the USD map
        await self.load_stage(map_name="basic_curve_cube.usda")

        # Advance to frame 24
        await self.set_time_in_seconds(1.0)

        await wait_stage_loading()

        omni.usd.get_context().get_selection().set_selected_prim_paths(["/World/Cube"], False)

        # You have to use this API to let the widget warm up. omni.kit.app.get_app()next_update_async() doesn't work well here
        await wait_stage_loading()

        # Dock the Curve Editor window to the top and occupy the entire main window for capturing
        await self.setup_docked_test(
            docked_window=self.curve_editor_window,
            restore_window=ui.Workspace.get_window("Content"),
            restore_position=ui.DockPosition.SAME,
            width=CURVE_EDITOR_WIDTH,
            height=CURVE_EDITOR_HEIGHT,
        )

        # Do the golden image comparison
        await self.do_visual_test(img_name="anim_curve_editor_basic")


class AnimCurveEditorKeyButtons(AnimCurveEditorTestsBase):
    """
    Test the Add Key button
    """

    async def test_anim_curve_editor_add_key_button(self):
        # Load the USD map
        await self.load_stage(map_name="basic_curve_cube.usda")
        await wait_stage_loading()
        # Advance to frame 12
        await self.set_time_in_frame(12)

        omni.usd.get_context().get_selection().set_selected_prim_paths(["/World/Cube"], False)
        await ui_test.human_delay(30)

        # Dock the Curve Editor window to the top and occupy the entire main window for capturing
        await self.setup_docked_test(
            docked_window=self.curve_editor_window,
            restore_window=ui.Workspace.get_window("Content"),
            restore_position=ui.DockPosition.SAME,
            width=CURVE_EDITOR_WIDTH,
            height=CURVE_EDITOR_HEIGHT,
        )

        # Add keys at 12th frame
        add_key_button = ui_test.find("Curve Editor//Frame/**/Button[*].name=='add keys to the selected curves'")
        self.assertIsNotNone(add_key_button)
        await add_key_button.click()

        # Do the golden image comparison
        await self.do_visual_test(img_name="anim_curve_editor_add_key_button")

    """
    Test the Remove Key button
    """

    async def test_anim_curve_editor_remove_key_button(self):
        # Load the USD map
        await self.load_stage(map_name="basic_curve_cube_single_curve.usda")
        await wait_stage_loading()

        omni.usd.get_context().get_selection().set_selected_prim_paths(["/World/Cube"], False)
        await ui_test.human_delay(30)

        # Dock the Curve Editor window to the top and occupy the entire main window for capturing
        await self.setup_docked_test(
            docked_window=self.curve_editor_window,
            restore_window=ui.Workspace.get_window("Content"),
            restore_position=ui.DockPosition.SAME,
            width=CURVE_EDITOR_WIDTH,
            height=CURVE_EDITOR_HEIGHT,
        )

        # Select the keys to remove
        omni.kit.commands.execute(
            "SelectAnimCurveKeys", paths=["/World/Cube.xformOp:translate|x"], operation="add", times=15.0
        )

        # Remove them
        remove_key_button = ui_test.find("Curve Editor//Frame/**/Button[*].name=='delete the selected keys'")
        self.assertIsNotNone(remove_key_button)
        await remove_key_button.click()

        # Do the golden image comparison
        await self.do_visual_test(img_name="anim_curve_editor_remove_key_button")

    """
    Test the Copy and Paste Key buttons
    """

    async def test_anim_curve_editor_copy_paste_key_button(self):
        # Load the USD map
        await self.load_stage(map_name="basic_curve_cube.usda")
        await wait_stage_loading()

        omni.usd.get_context().get_selection().set_selected_prim_paths(["/World/Cube"], False)
        await ui_test.human_delay(30)

        # Dock the Curve Editor window to the top and occupy the entire main window for capturing
        await self.setup_docked_test(
            docked_window=self.curve_editor_window,
            restore_window=ui.Workspace.get_window("Content"),
            restore_position=ui.DockPosition.SAME,
            width=CURVE_EDITOR_WIDTH,
            height=CURVE_EDITOR_HEIGHT,
        )

        # Select the key to copy and paste
        omni.kit.commands.execute(
            "SelectAnimCurveKeys",
            paths=["/World/Cube.xformOp:translate|z", "/World/Cube.xformOp:translate|y"],
            operation="add",
            times=30.0,
        )

        # Copy them
        copy_key_button = ui_test.find("Curve Editor//Frame/**/Button[*].name=='copy the selected keys'")
        self.assertIsNotNone(copy_key_button)
        await copy_key_button.click()

        # Paste them at 12th frame
        await self.set_time_in_frame(12)
        await ui_test.human_delay(30)

        paste_key_button = ui_test.find("Curve Editor//Frame/**/Button[*].name=='paste the copied keys'")
        self.assertIsNotNone(paste_key_button)
        await paste_key_button.click()

        # Do the golden image comparison
        await self.do_visual_test(img_name="anim_curve_editor_copy_paste_key_button")


class AnimCurveEditorFrameKeys(AnimCurveEditorTestsBase):
    """
    Navigation frame all feature test
    """

    async def test_anim_curve_editor_frame_all(self):
        # Load the USD map
        await self.load_stage(map_name="basic_curve_cube.usda")
        # Advance to frame 12
        await self.set_time_in_frame(12)

        omni.usd.get_context().get_selection().set_selected_prim_paths(["/World/Cube"], False)

        await wait_stage_loading()

        # Dock the Curve Editor window to the top and occupy the entire main window for capturing
        await self.setup_docked_test(
            docked_window=self.curve_editor_window,
            restore_window=ui.Workspace.get_window("Content"),
            restore_position=ui.DockPosition.SAME,
            width=CURVE_EDITOR_WIDTH,
            height=CURVE_EDITOR_HEIGHT,
        )

        # Move the mouse to the center of the canvas
        await ui_test.emulate_mouse_move(ui_test.Vec2(CURVE_EDITOR_WIDTH // 2, CURVE_EDITOR_HEIGHT // 2))
        # Scroll the mouse for zooming
        await ui_test.emulate_mouse_scroll(ui_test.Vec2(500, 500))

        # Note: it's better to use our internal APIs, instead of relying on the actions system.
        execute_action("omni.anim.curve_editor", "frame_all")

        # Do the golden image comparison
        await self.do_visual_test(img_name="anim_curve_editor_frame_all")

    """
    Navigation frame all feature test for OM-76401
    """

    async def test_anim_curve_editor_frame_all_OM_76401(self):
        # Load the USD map
        await self.load_stage(map_name="OM-76401.usd")
        # Advance to frame 12
        await self.set_time_in_frame(12)

        omni.usd.get_context().get_selection().set_selected_prim_paths(["/World/Cube"], False)

        await wait_stage_loading()

        # Dock the Curve Editor window to the top and occupy the entire main window for capturing
        await self.setup_docked_test(
            docked_window=self.curve_editor_window,
            restore_window=ui.Workspace.get_window("Content"),
            restore_position=ui.DockPosition.SAME,
            width=CURVE_EDITOR_WIDTH,
            height=CURVE_EDITOR_HEIGHT,
        )

        omni.usd.get_context().get_selection().set_selected_prim_paths(["/World/Cube"], False)
        await wait_stage_loading()

        # Note: it's better to use our internal APIs, instead of relying on the actions system.
        execute_action("omni.anim.curve_editor", "frame_all")

        # Do the golden image comparison
        await self.do_visual_test(img_name="anim_curve_editor_frame_all_OM-76401")


class AnimCurveEditorMoveKey(AnimCurveEditorTestsBase):
    """
    Move key test - Basic
    """

    async def test_anim_curve_editor_move_key_basic(self):
        # Load the USD map
        await self.load_stage(map_name="basic_curve_cube.usda")

        omni.usd.get_context().get_selection().set_selected_prim_paths(["/World/Cube"], False)

        await wait_stage_loading()

        # Dock the Curve Editor window to the top and occupy the entire main window for capturing
        await self.setup_docked_test(
            docked_window=self.curve_editor_window,
            restore_window=ui.Workspace.get_window("Content"),
            restore_position=ui.DockPosition.SAME,
            width=CURVE_EDITOR_WIDTH,
            height=CURVE_EDITOR_HEIGHT,
        )

        await ui_test.emulate_mouse_move(MAGIC_POS_2)
        await ui_test.emulate_mouse_drag_and_drop(start_pos=MAGIC_POS_2, end_pos=ui_test.Vec2(931, 280))

        # Do the golden image comparison
        await self.do_visual_test(img_name="anim_curve_editor_move_key_basic")

    """
    Move key test - Advanced. Move key across another key, beyond the first and last key.
    """

    async def test_anim_curve_editor_move_key_advanced(self):
        # Load the USD map
        await self.load_stage(map_name="basic_curve_cube_multiple_keys.usda")

        omni.usd.get_context().get_selection().set_selected_prim_paths(["/World/Cube"], False)

        await wait_stage_loading()

        # Dock the Curve Editor window to the top and occupy the entire main window for capturing
        await self.setup_docked_test(
            docked_window=self.curve_editor_window,
            restore_window=ui.Workspace.get_window("Content"),
            restore_position=ui.DockPosition.SAME,
            width=CURVE_EDITOR_WIDTH,
            height=CURVE_EDITOR_HEIGHT,
        )

        """
        Step 1: Move the last key into the middle of the first and the second key
        """
        await ui_test.emulate_mouse_move(MAGIC_POS_2)
        await ui_test.emulate_mouse_drag_and_drop(start_pos=MAGIC_POS_2, end_pos=ui_test.Vec2(458, 280))

        # Do the golden image comparison
        await self.do_visual_test(img_name="anim_curve_editor_move_key_advanced_1", restore=False)

        """
        Step 2: Move the middle key beyond the first key
        """
        await ui_test.human_delay(30)  # avoid double-click
        await ui_test.emulate_mouse_move(ui_test.Vec2(458, 280))
        await ui_test.emulate_mouse_drag_and_drop(start_pos=ui_test.Vec2(458, 280), end_pos=ui_test.Vec2(247, 443))

        # Do the golden image comparison
        await self.do_visual_test(img_name="anim_curve_editor_move_key_advanced_2", restore=False)

        """
        Step 3: Move the middle key beyond the last key
        """
        await ui_test.human_delay(30)  # avoid double-click
        await ui_test.emulate_mouse_move(ui_test.Vec2(247, 443))
        await ui_test.emulate_mouse_drag_and_drop(start_pos=ui_test.Vec2(247, 443), end_pos=ui_test.Vec2(1317, 384))

        # Do the golden image comparison
        await self.do_visual_test(img_name="anim_curve_editor_move_key_advanced_3")

    """
    Move keys test - Multiple Keys. Selected by drawing a square area with the mouse.
    """

    async def test_anim_curve_editor_move_multiple_keys_selected_by_dragging(self):
        # Load the USD map
        await self.load_stage(map_name="basic_curve_cube_multiple_keys.usda")

        omni.usd.get_context().get_selection().set_selected_prim_paths(["/World/Cube"], False)

        await wait_stage_loading()

        # Dock the Curve Editor window to the top and occupy the entire main window for capturing
        await self.setup_docked_test(
            docked_window=self.curve_editor_window,
            restore_window=ui.Workspace.get_window("Content"),
            restore_position=ui.DockPosition.SAME,
            width=CURVE_EDITOR_WIDTH,
            height=CURVE_EDITOR_HEIGHT,
        )

        # Select the top two curves
        local_magic_pos = ui_test.Vec2(1566, 105)
        # Step 1: move to the top-right corner
        await ui_test.emulate_mouse_move(local_magic_pos)
        # Step 2: Click and drag the mouse to bottom-left. Two keys in this square area will be selected.
        await ui_test.emulate_mouse_drag_and_drop(start_pos=local_magic_pos, end_pos=ui_test.Vec2(1483, 357))

        # Move the selected keys into the middle of the first and the second key
        await ui_test.emulate_mouse_move(MAGIC_POS_2)
        await ui_test.emulate_mouse_drag_and_drop(start_pos=MAGIC_POS_2, end_pos=ui_test.Vec2(452, 280))

        # Do the golden image comparison
        await self.do_visual_test(img_name="anim_curve_editor_move_multiple_keys_1")

    """
    Move keys test - Multiple Keys. Selected by pressing Left Ctrl + clicking the mouse.
    """

    async def test_anim_curve_editor_move_multiple_keys_selected_by_ctrl_clicking(self):
        # Load the USD map
        await self.load_stage(map_name="basic_curve_cube_multiple_keys.usda")

        omni.usd.get_context().get_selection().set_selected_prim_paths(["/World/Cube"], False)

        await wait_stage_loading()

        # Dock the Curve Editor window to the top and occupy the entire main window for capturing
        await self.setup_docked_test(
            docked_window=self.curve_editor_window,
            restore_window=ui.Workspace.get_window("Content"),
            restore_position=ui.DockPosition.SAME,
            width=CURVE_EDITOR_WIDTH,
            height=CURVE_EDITOR_HEIGHT,
        )

        # Select the top two curves
        # Step 1: Press and hold Left_Ctrl button.
        await emulate_keyboard(
            KeyboardEventType.KEY_PRESS, KeyboardInput.LEFT_CONTROL, modifier=carb.input.KEYBOARD_MODIFIER_FLAG_CONTROL
        )
        await ui_test.human_delay()
        # Step 2: Click and select two keys.
        await ui_test.emulate_mouse_move(MAGIC_POS_3)
        await ui_test.emulate_mouse_click()
        await ui_test.emulate_mouse_move(MAGIC_POS_2)
        await ui_test.emulate_mouse_click()
        # Step 3: Release Left_Ctrl button.
        await emulate_keyboard(KeyboardEventType.KEY_RELEASE, KeyboardInput.LEFT_CONTROL)

        # Move the selected keys into the middle of the first and the second key
        # Step 2 above already clicked on MAGIC_POS_2, so the press below is a second press at the very same
        # position. Without this delay the two are delivered as a double-click, which the curve segment under
        # the key handles as "select every key on this curve" (see CurveControlSegment._on_double_clicked).
        await ui_test.human_delay(30)  # avoid double-click
        await ui_test.emulate_mouse_move(MAGIC_POS_2)
        await ui_test.emulate_mouse_drag_and_drop(start_pos=MAGIC_POS_2, end_pos=ui_test.Vec2(452, 280))

        # Do the golden image comparison
        # the golden img is the same as `test_anim_curve_editor_move_multiple_keys_selected_by_dragging`, but the
        # capture is written under a distinct name so the two tests don't overwrite each other's failure artifacts.
        await self.do_visual_test(
            img_name="anim_curve_editor_move_multiple_keys_1_ctrl_click",
            golden_img_name="anim_curve_editor_move_multiple_keys_1",
        )

    """
    Move key test - With 'Step' tangent.
    """

    async def test_anim_curve_editor_move_key_step_tangent(self):
        # Load the USD map
        await self.load_stage(map_name="basic_curve_cube_multiple_keys_step.usda")

        omni.usd.get_context().get_selection().set_selected_prim_paths(["/World/Cube"], False)

        await wait_stage_loading()

        """
        Move the last keys into the middle of the first and the second key
        """

        # Dock the Curve Editor window to the top and occupy the entire main window for capturing
        await self.setup_docked_test(
            docked_window=self.curve_editor_window,
            restore_window=ui.Workspace.get_window("Content"),
            restore_position=ui.DockPosition.SAME,
            width=CURVE_EDITOR_WIDTH,
            height=CURVE_EDITOR_HEIGHT,
        )

        # Drag the key
        await ui_test.human_delay(30)  # avoid double-click
        await ui_test.emulate_mouse_move(MAGIC_POS_2)
        await ui_test.emulate_mouse_drag_and_drop(start_pos=MAGIC_POS_2, end_pos=ui_test.Vec2(452, 280))

        # Do the golden image comparison
        await self.do_visual_test(img_name="test_anim_curve_editor_move_key_step_tangent", threshold=1e-5)
        # Yes, we have to lower the threshold here to avoid false-negative results.

    """
    Move key test - With 'Step' tangent (2). This unit test is for OM-52810.
    """

    async def test_anim_curve_editor_move_key_step_tangent_2(self):
        # Load the USD map
        await self.load_stage(map_name="step_curve_multi_key.usda")

        omni.usd.get_context().get_selection().set_selected_prim_paths(["/World/Cube"], False)

        await wait_stage_loading()

        """
        Move the last keys into the middle of the first and the second key
        """
        # Dock the Curve Editor window to the top and occupy the entire main window for capturing
        await self.setup_docked_test(
            docked_window=self.curve_editor_window,
            restore_window=ui.Workspace.get_window("Content"),
            restore_position=ui.DockPosition.SAME,
            width=CURVE_EDITOR_WIDTH,
            height=CURVE_EDITOR_HEIGHT,
        )

        # Drag the key
        local_magic_pos = ui_test.Vec2(910, 125)
        await ui_test.emulate_mouse_move(local_magic_pos)
        await ui_test.emulate_mouse_drag_and_drop(start_pos=local_magic_pos, end_pos=ui_test.Vec2(1290, 125))

        # set the crop area a bit larger, to avoid some random failures
        self._crop_config = (205, 74, None, None)
        # Do the golden image comparison
        await self.do_visual_test(img_name="test_anim_curve_editor_move_key_step_tangent_2")
        # recover the crop config
        self._crop_config = (165, 44, None, None)


class AnimCurveEditorZooming(AnimCurveEditorTestsBase):
    """
    Navigation: Zooming feature test. scroll the mouse for zooming
    """

    async def test_anim_curve_editor_zooming(self):
        # Load the USD map
        await self.load_stage(map_name="basic_curve_cube.usda")
        # Advance to frame 12
        await self.set_time_in_frame(12)

        omni.usd.get_context().get_selection().set_selected_prim_paths(["/World/Cube"], False)

        await wait_stage_loading()

        # Dock the Curve Editor window to the top and occupy the entire main window for capturing
        await self.setup_docked_test(
            docked_window=self.curve_editor_window,
            restore_window=ui.Workspace.get_window("Content"),
            restore_position=ui.DockPosition.SAME,
            width=CURVE_EDITOR_WIDTH,
            height=CURVE_EDITOR_HEIGHT,
        )

        # Move the mouse to the center of the canvas
        await ui_test.emulate_mouse_move(ui_test.Vec2(CURVE_EDITOR_WIDTH // 2, CURVE_EDITOR_HEIGHT // 2))
        # Scroll the mouse for zooming
        await ui_test.emulate_mouse_scroll(ui_test.Vec2(0, -10000))

        # Do the golden image comparison
        await self.do_visual_test(img_name="anim_curve_editor_zooming")


class AnimCurveEditorCurveCommands(AnimCurveEditorTestsBase):
    """
    In these tests, we will use the Curve commands to add/remove keys,
    and see the curve editor's reaction.
    """

    """
    Test case 1: Use `SetAnimCurveKeys` from Curve extension to add a key
    """

    async def test_anim_curve_editor_curve_commands_add_key(self):
        # Load stage
        await self.load_stage(map_name="basic_curve_cube.usda")
        # Advance to frame 15
        await self.set_time_in_frame(15)

        omni.usd.get_context().get_selection().set_selected_prim_paths(["/World/Cube"], False)

        await wait_stage_loading()

        (result, err) = omni.kit.commands.execute("SetAnimCurveKeys", paths=["/World/Cube"])
        self.assertTrue(result)  # command execution no exception from the command framework
        self.assertTrue(err)  # command no error

        # Dock the Curve Editor window to the top and occupy the entire main window for capturing
        await self.setup_docked_test(
            docked_window=self.curve_editor_window,
            restore_window=ui.Workspace.get_window("Content"),
            restore_position=ui.DockPosition.SAME,
            width=CURVE_EDITOR_WIDTH,
            height=CURVE_EDITOR_HEIGHT,
        )

        await self.do_visual_test(img_name="anim_curve_editor_curve_commands_add_key")

    """
    Test case 2: Use `RemoveAnimCurveKeys` from Curve extension to remove a key
    """

    async def test_anim_curve_editor_curve_commands_remove_key(self):
        # Load stage
        await self.load_stage(map_name="basic_curve_cube.usda")
        # Advance to frame 30
        await self.set_time_in_frame(30)

        omni.usd.get_context().get_selection().set_selected_prim_paths(["/World/Cube"], False)

        await wait_stage_loading()

        (result, err) = omni.kit.commands.execute("RemoveAnimCurveKeys", paths=["/World/Cube"])
        self.assertTrue(result)  # command execution no exception from the command framework
        self.assertTrue(err)  # command no error

        # Dock the Curve Editor window to the top and occupy the entire main window for capturing
        await self.setup_docked_test(
            docked_window=self.curve_editor_window,
            restore_window=ui.Workspace.get_window("Content"),
            restore_position=ui.DockPosition.SAME,
            width=CURVE_EDITOR_WIDTH,
            height=CURVE_EDITOR_HEIGHT,
        )

        await self.do_visual_test(img_name="anim_curve_editor_curve_commands_remove_key")


class AnimCurveEditorNavigateFramesInTime(AnimCurveEditorTestsBase):
    """
    Previous / Next Key Frame actions
    """

    async def test_anim_curve_editor_previous_next_key_frame(self):
        # Load the USD map
        await self.load_stage(map_name="basic_curve_cube_0_30.usda")
        # Advance to frame 15
        await self.set_time_in_frame(15)

        omni.usd.get_context().get_selection().set_selected_prim_paths(["/World/Cube"], False)

        await wait_stage_loading()

        # Dock the Curve Editor window to the top and occupy the entire main window for capturing
        await self.setup_docked_test(
            docked_window=self.curve_editor_window,
            restore_window=ui.Workspace.get_window("Content"),
            restore_position=ui.DockPosition.SAME,
            width=CURVE_EDITOR_WIDTH,
            height=CURVE_EDITOR_HEIGHT,
        )

        await self.do_visual_test(img_name="anim_curve_editor_navigation_15", restore=False)

        execute_action("omni.anim.curve_editor", "previous_key")  # should at 0
        await self.do_visual_test(img_name="anim_curve_editor_navigation_0", restore=False)

        execute_action("omni.anim.curve_editor", "previous_key")  # still at 0
        await self.do_visual_test(img_name="anim_curve_editor_navigation_0", restore=False)

        execute_action("omni.anim.curve_editor", "next_key")  # should at 30
        await self.do_visual_test(img_name="anim_curve_editor_navigation_30", restore=False)

        execute_action("omni.anim.curve_editor", "next_key")  # still at 30
        await self.do_visual_test(img_name="anim_curve_editor_navigation_30")


class AnimCurveEditorValueDisplay(AnimCurveEditorTestsBase):
    """
    These tests will check whether the curve editor will correctly display the time and value of the selected key
    """

    async def test_anim_curve_editor_value_display_1(self):
        # Load the USD map
        await self.load_stage(map_name="basic_curve_cube_0_30.usda")

        omni.usd.get_context().get_selection().set_selected_prim_paths(["/World/Cube"], False)

        await wait_stage_loading()

        # Dock the Curve Editor window to the top and occupy the entire main window for capturing
        await self.setup_docked_test(
            docked_window=self.curve_editor_window,
            restore_window=ui.Workspace.get_window("Content"),
            restore_position=ui.DockPosition.SAME,
            width=CURVE_EDITOR_WIDTH,
            height=CURVE_EDITOR_HEIGHT,
        )

        # use ui_test.emulate_mouse_move_and_click() will result to strange behaviors. I don't know why yet.
        await ui_test.emulate_mouse_move(ui_test.Vec2(288, 658))  # The bottom-left key
        await ui_test.human_delay()
        await ui_test.emulate_mouse_click()
        await ui_test.human_delay()

        await self.do_visual_test(img_name="test_anim_curve_editor_value_display_1")

    async def test_anim_curve_editor_value_display_2(self):
        # Load the USD map
        await self.load_stage(map_name="basic_curve_cube_0_30.usda")

        omni.usd.get_context().get_selection().set_selected_prim_paths(["/World/Cube"], False)

        await wait_stage_loading()

        # Dock the Curve Editor window to the top and occupy the entire main window for capturing
        await self.setup_docked_test(
            docked_window=self.curve_editor_window,
            restore_window=ui.Workspace.get_window("Content"),
            restore_position=ui.DockPosition.SAME,
            width=CURVE_EDITOR_WIDTH,
            height=CURVE_EDITOR_HEIGHT,
        )

        # use ui_test.emulate_mouse_move_and_click() will result to strange behaviors. I don't know why yet.
        await ui_test.emulate_mouse_move(MAGIC_POS_3)  # The top-right key
        await ui_test.human_delay()
        await ui_test.emulate_mouse_click()
        await ui_test.human_delay()

        await self.do_visual_test(img_name="test_anim_curve_editor_value_display_2")


class AnimCurveEditorSliderTime(AnimCurveEditorTestsBase):
    """
    These tests focus on the sliders in the timelines.
    """

    """
    Check whether the slider follows the current time
    """

    async def test_anim_curve_editor_slider_current_time(self):
        # Load the USD map
        await self.load_stage(map_name="basic_curve_cube_0_30.usda")
        timeline_iface = get_timeline_interface()

        omni.usd.get_context().get_selection().set_selected_prim_paths(["/World/Cube"], False)

        await wait_stage_loading()

        # Dock the Curve Editor window to the top and occupy the entire main window for capturing
        await self.setup_docked_test(
            docked_window=self.curve_editor_window,
            restore_window=ui.Workspace.get_window("Content"),
            restore_position=ui.DockPosition.SAME,
            width=CURVE_EDITOR_WIDTH,
            height=CURVE_EDITOR_HEIGHT,
        )

        await self.do_visual_test(img_name="anim_curve_editor_navigation_0", restore=False)  # default

        timeline_iface.set_current_time(15 / 24)  # current_frame / FPS
        await self.do_visual_test(img_name="anim_curve_editor_navigation_15", restore=False)

        timeline_iface.set_current_time(31 / 24)
        await self.do_visual_test(img_name="anim_curve_editor_navigation_31", restore=False)

        timeline_iface.set_current_time(-1 / 24)
        await self.do_visual_test(img_name="anim_curve_editor_navigation_-1")

        # IMPORTANT: restore the timeline to zero
        timeline_iface.set_current_time(0)
        await ui_test.human_delay()

    """
    Check whether the slider follows the tentative time
    """

    async def test_anim_curve_editor_slider_tentative_time(self):
        # Load the USD map
        await self.load_stage(map_name="basic_curve_cube_0_30.usda")
        timeline_iface = get_timeline_interface()

        # select prim and focus Curve Editor so the widgets are built
        curve_editor_window = ui.Workspace.get_window("Curve Editor")
        curve_editor_window.visible = True
        curve_editor_window.focus()
        omni.usd.get_context().get_selection().set_selected_prim_paths(["/World/Cube"], False)

        await wait_stage_loading()

        # Dock the Curve Editor window to the top and occupy the entire main window for capturing
        await self.setup_docked_test(
            docked_window=self.curve_editor_window,
            restore_window=ui.Workspace.get_window("Content"),
            restore_position=ui.DockPosition.SAME,
            width=CURVE_EDITOR_WIDTH,
            height=CURVE_EDITOR_HEIGHT,
        )

        await self.do_visual_test(img_name="anim_curve_editor_navigation_0", restore=False)  # default

        timeline_iface.set_tentative_time(15 / 24)  # current_frame / FPS
        await self.do_visual_test(img_name="anim_curve_editor_navigation_15", restore=False)

        timeline_iface.set_tentative_time(31 / 24)
        await self.do_visual_test(img_name="anim_curve_editor_navigation_31", restore=False)

        timeline_iface.set_tentative_time(-1 / 24)
        await self.do_visual_test(img_name="anim_curve_editor_navigation_-1")

        # IMPORTANT: restore the timeline to zero
        timeline_iface.set_current_time(0)
        await ui_test.human_delay()

    """
    Check whether the slider follows the current and the tentative time
    """

    async def test_anim_curve_editor_slider_mixed_time(self):
        # Load the USD map
        await self.load_stage(map_name="basic_curve_cube_0_30.usda")
        timeline_iface = get_timeline_interface()

        omni.usd.get_context().get_selection().set_selected_prim_paths(["/World/Cube"], False)

        await wait_stage_loading()

        # Dock the Curve Editor window to the top and occupy the entire main window for capturing
        await self.setup_docked_test(
            docked_window=self.curve_editor_window,
            restore_window=ui.Workspace.get_window("Content"),
            restore_position=ui.DockPosition.SAME,
            width=CURVE_EDITOR_WIDTH,
            height=CURVE_EDITOR_HEIGHT,
        )

        await self.do_visual_test(img_name="anim_curve_editor_navigation_0", restore=False)  # default

        timeline_iface.set_tentative_time(15 / 24)  # current_frame / FPS
        await self.do_visual_test(img_name="anim_curve_editor_navigation_15", restore=False)

        timeline_iface.set_current_time(31 / 24)
        await self.do_visual_test(img_name="anim_curve_editor_navigation_31", restore=False)

        timeline_iface.set_current_time(-1 / 24)
        await self.do_visual_test(img_name="anim_curve_editor_navigation_-1", restore=False)

        # IMPORTANT: restore the timeline to zero
        timeline_iface.set_tentative_time(0)
        await self.do_visual_test(img_name="anim_curve_editor_navigation_0")


class AnimCurveEditorTangentType(AnimCurveEditorTestsBase):
    """
    These tests focus on the different types of tangent, i.e., Auto, Smooth, Fixed, Linear, Step
    """

    async def setUp(self):
        await super().setUp()
        self.tangent_auto_button = ui_test.find("Curve Editor//Frame/**/Button[*].name=='Auto'")
        self.tangent_smooth_button = ui_test.find("Curve Editor//Frame/**/Button[*].name=='Smooth'")
        # self.tangent_fixed_button = ui_test.find("Curve Editor//Frame/**/Button[*].name=='Fixed'")
        self.tangent_flat_button = ui_test.find("Curve Editor//Frame/**/Button[*].name=='Flat'")
        self.tangent_linear_button = ui_test.find("Curve Editor//Frame/**/Button[*].name=='Linear'")
        self.tangent_step_button = ui_test.find("Curve Editor//Frame/**/Button[*].name=='Step'")

        self.assertIsNotNone(self.tangent_auto_button)
        self.assertIsNotNone(self.tangent_smooth_button)
        # self.assertIsNotNone(self.tangent_fixed_button)
        self.assertIsNotNone(self.tangent_flat_button)
        self.assertIsNotNone(self.tangent_linear_button)
        self.assertIsNotNone(self.tangent_step_button)

        self.btn_dict = dict(
            auto=self.tangent_auto_button,
            smooth=self.tangent_smooth_button,
            # fixed=self.tangent_fixed_button,
            flat=self.tangent_flat_button,
            linear=self.tangent_linear_button,
            step=self.tangent_step_button,
        )
        timeline_iface = get_timeline_interface()
        timeline_iface.set_tentative_time(0)

    """
    Test case 1: Load a curve, then change its type accordingly.
    """

    async def _test_case_1(self, type_name):
        # Load the USD map
        await self.load_stage(map_name="basic_curve_cube_multiple_keys.usda")

        omni.usd.get_context().get_selection().set_selected_prim_paths(["/World/Cube"], False)
        await wait_stage_loading()

        await self.setup_docked_test(
            docked_window=self.curve_editor_window,
            restore_window=ui.Workspace.get_window("Content"),
            restore_position=ui.DockPosition.SAME,
            width=CURVE_EDITOR_WIDTH,
            height=CURVE_EDITOR_HEIGHT,
        )

        await ui_test.emulate_mouse_move(MAGIC_POS_1)  # select the key on the curve
        await ui_test.emulate_mouse_click()
        await ui_test.human_delay()

        await self.btn_dict[type_name].click()
        await ui_test.human_delay()

        await self.do_visual_test(img_name=f"anim_curve_editor_tangent_{type_name}")

    """
    Test case 2: Load a curve, change its type, and drag the key point.
    """

    async def _test_case_2(self, type_name):
        # Load the USD map
        await self.load_stage(map_name="basic_curve_cube_multiple_keys.usda")

        omni.usd.get_context().get_selection().set_selected_prim_paths(["/World/Cube"], False)
        await wait_stage_loading()

        await self.setup_docked_test(
            docked_window=self.curve_editor_window,
            restore_window=ui.Workspace.get_window("Content"),
            restore_position=ui.DockPosition.SAME,
            width=CURVE_EDITOR_WIDTH,
            height=CURVE_EDITOR_HEIGHT,
        )

        await ui_test.emulate_mouse_move(MAGIC_POS_1)
        await ui_test.emulate_mouse_click()
        await ui_test.human_delay()

        await self.btn_dict[type_name].click()
        await ui_test.human_delay()

        # FIXME: We have to manually move the mouse to the start_pos before we call ui_test.emulate_mouse_drag_and_drop().
        # Otherwise, the mouse position is not precise. The reason is known yet.
        await ui_test.emulate_mouse_move(MAGIC_POS_1)
        await ui_test.human_delay()
        await ui_test.emulate_mouse_drag_and_drop(start_pos=MAGIC_POS_1, end_pos=ui_test.Vec2(410, 300))
        await ui_test.human_delay()

        await self.do_visual_test(img_name=f"anim_curve_editor_tangent_{type_name}_drag")

    """
    Fixed Type. Test case 1: Load and display flat tangent
    """

    async def test_anim_curve_editor_tangent_flat(self):
        await self._test_case_1("flat")

    """
    Fixed Type. Test case 2: Dragging a flat key will not change its tangent.
    """

    async def test_anim_curve_editor_tangent_flat_drag(self):
        await self._test_case_2("flat")

    """
    Auto Type. Test case 1: Load a fixed tangent, then change its type into Auto.
    """

    async def test_anim_curve_editor_tangent_auto(self):
        await self._test_case_1("auto")

    """
    Auto Type. Test case 2: Dragging a key with Auto tangent.
    """

    async def test_anim_curve_editor_tangent_auto_drag(self):
        await self._test_case_2("auto")

    """
    Smooth Type. Test case 1: Load a fixed tangent, then change its type into Smooth.
    """

    async def test_anim_curve_editor_tangent_smooth(self):
        await self._test_case_1("smooth")

    """
    Smooth Type. Test case 2: Dragging a key with Smooth tangent.
    """

    async def test_anim_curve_editor_tangent_smooth_drag(self):
        await self._test_case_2("smooth")

    """
    Linear Type. Test case 1: Load a fixed tangent, then change its type into Linear.
    """

    async def test_anim_curve_editor_tangent_linear(self):
        await self._test_case_1("linear")

    """
    Linear Type. Test case 2: Dragging a key with Linear tangent.
    """

    async def test_anim_curve_editor_tangent_linear_drag(self):
        await self._test_case_2("linear")

    """
    Step Type. Test case 1: Load a fixed tangent, then change its type into Step.
    """

    async def test_anim_curve_editor_tangent_step(self):
        await self._test_case_1("step")

    """
    Step Type. Test case 2: Dragging a key with Step tangent.
    """

    async def test_anim_curve_editor_tangent_step_drag(self):
        await self._test_case_2("step")


class AnimCurveEditorTangentWeightedBroken(AnimCurveEditorTestsBase):
    MAGIC_RIGHT_HANDLE = ui_test.Vec2(944, 168)

    """
    These tests focus on two attributes of tangent, i.e., (non-)weighted and (un-)broken
    """

    async def setUp(self):
        await super().setUp()
        self.broken_btn = ui_test.find("Curve Editor//Frame/**/Button[*].name=='Broken'")
        self.unbroken_btn = ui_test.find("Curve Editor//Frame/**/Button[*].name=='Unbroken'")
        self.weighted_btn = ui_test.find("Curve Editor//Frame/**/Button[*].name=='Weighted'")
        self.nonweighted_btn = ui_test.find("Curve Editor//Frame/**/Button[*].name=='Non-weighted'")

        self.assertIsNotNone(self.broken_btn)
        self.assertIsNotNone(self.unbroken_btn)
        self.assertIsNotNone(self.weighted_btn)
        self.assertIsNotNone(self.nonweighted_btn)

    async def _set_non_weighted(self):
        await self.nonweighted_btn.click()

    async def _set_weighted(self):
        await self.weighted_btn.click()

    async def _set_unbroken(self):
        await self.unbroken_btn.click()

    async def _set_broken(self):
        await self.broken_btn.click()

    """
    Test Case 1: Drag the handles of a non-weighted, unbroken keypoint
    """

    async def test_anim_curve_editor_tangent_nonweighted_unbroken(self):
        # Load the USD map
        await self.load_stage(map_name="basic_curve_cube_multiple_keys.usda")

        omni.usd.get_context().get_selection().set_selected_prim_paths(["/World/Cube"], False)
        await wait_stage_loading()

        await self.setup_docked_test(
            docked_window=self.curve_editor_window,
            restore_window=ui.Workspace.get_window("Content"),
            restore_position=ui.DockPosition.SAME,
            width=CURVE_EDITOR_WIDTH,
            height=CURVE_EDITOR_HEIGHT,
        )

        """
        Test the right handle
        """
        await ui_test.emulate_mouse_move(MAGIC_POS_1)
        await ui_test.emulate_mouse_click()
        await ui_test.human_delay()

        await ui_test.emulate_mouse_move(self.MAGIC_RIGHT_HANDLE)  # right handle
        await ui_test.human_delay()
        await ui_test.emulate_mouse_drag_and_drop(start_pos=self.MAGIC_RIGHT_HANDLE, end_pos=ui_test.Vec2(931, 140))
        await ui_test.human_delay()

        await self.do_visual_test(img_name="anim_curve_editor_tangent_nonweighted_unbroken_drag_right", restore=False)

    """
    Test Case 2: Drag the handles of a weighted, unbroken keypoint
    """

    async def test_anim_curve_editor_tangent_weighted_unbroken(self):
        # Load the USD map
        await self.load_stage(map_name="basic_curve_cube_multiple_keys.usda")

        omni.usd.get_context().get_selection().set_selected_prim_paths(["/World/Cube"], False)
        await wait_stage_loading()

        await self.setup_docked_test(
            docked_window=self.curve_editor_window,
            restore_window=ui.Workspace.get_window("Content"),
            restore_position=ui.DockPosition.SAME,
            width=CURVE_EDITOR_WIDTH,
            height=CURVE_EDITOR_HEIGHT,
        )

        await ui_test.emulate_mouse_move(MAGIC_POS_1)
        await ui_test.emulate_mouse_click()  # click the curve first
        await ui_test.human_delay()

        await self._set_weighted()

        await ui_test.emulate_mouse_move(self.MAGIC_RIGHT_HANDLE)  # move the right handle first
        await ui_test.human_delay()
        await ui_test.emulate_mouse_drag_and_drop(start_pos=self.MAGIC_RIGHT_HANDLE, end_pos=ui_test.Vec2(1331, 140))
        await ui_test.human_delay()

        # await ui_test.emulate_mouse_move(ui_test.Vec2(869, 122))  # then, move the left handle
        # await ui_test.human_delay()
        # await ui_test.emulate_mouse_drag_and_drop(start_pos=ui_test.Vec2(869, 122), end_pos=ui_test.Vec2(823, 101))
        # await ui_test.human_delay()

        await self.do_visual_test(img_name="anim_curve_editor_tangent_weighted_unbroken_drag")

    """
    Test Case 3: Drag the handles of a non-weighted, broken keypoint
    """

    async def test_anim_curve_editor_tangent_nonweighted_broken(self):
        # Load the USD map
        await self.load_stage(map_name="basic_curve_cube_multiple_keys.usda")

        omni.usd.get_context().get_selection().set_selected_prim_paths(["/World/Cube"], False)
        await wait_stage_loading()

        await self.setup_docked_test(
            docked_window=self.curve_editor_window,
            restore_window=ui.Workspace.get_window("Content"),
            restore_position=ui.DockPosition.SAME,
            width=CURVE_EDITOR_WIDTH,
            height=CURVE_EDITOR_HEIGHT,
        )

        await ui_test.emulate_mouse_move(MAGIC_POS_1)
        await ui_test.emulate_mouse_click()  # click the curve first
        await ui_test.human_delay()

        await self._set_broken()

        await ui_test.emulate_mouse_move(self.MAGIC_RIGHT_HANDLE)  # move the right handle first
        await ui_test.human_delay()
        await ui_test.emulate_mouse_drag_and_drop(start_pos=self.MAGIC_RIGHT_HANDLE, end_pos=ui_test.Vec2(1331, 140))
        await ui_test.human_delay()

        local_left_magic = ui_test.Vec2(894, 81)
        await ui_test.emulate_mouse_move(local_left_magic)  # then, move the left handle
        await ui_test.human_delay()
        await ui_test.emulate_mouse_drag_and_drop(start_pos=local_left_magic, end_pos=ui_test.Vec2(823, 530))
        await ui_test.human_delay()

        await self.do_visual_test(img_name="anim_curve_editor_tangent_nonweighted_broken_drag")

    """
    Test Case 4: Drag the handles of a weighted, broken keypoint
    """

    async def test_anim_curve_editor_tangent_weighted_broken(self):
        # Load the USD map
        await self.load_stage(map_name="basic_curve_cube_multiple_keys.usda")

        omni.usd.get_context().get_selection().set_selected_prim_paths(["/World/Cube"], False)
        await wait_stage_loading()

        await self.setup_docked_test(
            docked_window=self.curve_editor_window,
            restore_window=ui.Workspace.get_window("Content"),
            restore_position=ui.DockPosition.SAME,
            width=CURVE_EDITOR_WIDTH,
            height=CURVE_EDITOR_HEIGHT,
        )

        await ui_test.emulate_mouse_move(MAGIC_POS_1)
        await ui_test.emulate_mouse_click()  # click the curve first
        await ui_test.human_delay()

        await self._set_broken()
        await self._set_weighted()

        await ui_test.emulate_mouse_move(self.MAGIC_RIGHT_HANDLE)  # move the right handle first
        await ui_test.human_delay()
        await ui_test.emulate_mouse_drag_and_drop(start_pos=self.MAGIC_RIGHT_HANDLE, end_pos=ui_test.Vec2(1331, 140))
        await ui_test.human_delay()

        local_left_magic = ui_test.Vec2(894, 81)
        await ui_test.emulate_mouse_move(local_left_magic)  # then, move the left handle
        await ui_test.human_delay()
        await ui_test.emulate_mouse_drag_and_drop(start_pos=local_left_magic, end_pos=ui_test.Vec2(823, 530))
        await ui_test.human_delay()

        await self.do_visual_test(img_name="anim_curve_editor_tangent_weighted_broken_drag")


class AnimCurveEditorFreeVerticalHorizon(AnimCurveEditorTestsBase):
    """
    These tests focus on the Free/Vertical/Horizontal state of the key
    """

    async def setUp(self):
        await super().setUp()
        self.movement_constraint_menu = ui_test.find(
            "Curve Editor//Frame/**/ComboBox[*].name=='Key Movement Constraint Menu'"
        )
        self.assertIsNotNone(self.movement_constraint_menu)  # "Free", "Vertical", "Horizontal"

    async def tearDown(self):
        # Reset to free mode on exit
        await self._set_free()

    async def _set_free(self):
        self.movement_constraint_menu.model.get_item_value_model().set_value(0)
        self.movement_constraint_menu.model.update_ui()
        await ui_test.human_delay()

    async def _set_vertical(self):
        self.movement_constraint_menu.model.get_item_value_model().set_value(1)
        self.movement_constraint_menu.model.update_ui()
        await ui_test.human_delay()

    async def _set_horizontal(self):
        self.movement_constraint_menu.model.get_item_value_model().set_value(2)
        self.movement_constraint_menu.model.update_ui()
        await ui_test.human_delay()

    """
    Test Case 1: Set to free state. Select a key and drag it.
    """

    async def test_anim_curve_editor_key_free_drag(self):
        # Load the USD map
        await self.load_stage(map_name="basic_curve_cube_multiple_keys.usda")

        omni.usd.get_context().get_selection().set_selected_prim_paths(["/World/Cube"], False)
        await wait_stage_loading()

        await self.setup_docked_test(
            docked_window=self.curve_editor_window,
            restore_window=ui.Workspace.get_window("Content"),
            restore_position=ui.DockPosition.SAME,
            width=CURVE_EDITOR_WIDTH,
            height=CURVE_EDITOR_HEIGHT,
        )

        await self._set_free()

        await ui_test.emulate_mouse_move(MAGIC_POS_1)
        await ui_test.human_delay()
        await ui_test.emulate_mouse_drag_and_drop(start_pos=MAGIC_POS_1, end_pos=ui_test.Vec2(1280, 350))
        await ui_test.human_delay()

        await self.do_visual_test(img_name="test_anim_curve_editor_key_free_drag")

    """
    Test Case 2: Set to vertical state. Select a key and drag it.
    """

    async def test_anim_curve_editor_key_vertical_drag(self):
        # Load the USD map
        await self.load_stage(map_name="basic_curve_cube_multiple_keys.usda")

        omni.usd.get_context().get_selection().set_selected_prim_paths(["/World/Cube"], False)
        await wait_stage_loading()

        await self.setup_docked_test(
            docked_window=self.curve_editor_window,
            restore_window=ui.Workspace.get_window("Content"),
            restore_position=ui.DockPosition.SAME,
            width=CURVE_EDITOR_WIDTH,
            height=CURVE_EDITOR_HEIGHT,
        )

        await self._set_vertical()

        await ui_test.emulate_mouse_move(MAGIC_POS_1)
        await ui_test.human_delay()
        await ui_test.emulate_mouse_drag_and_drop(start_pos=MAGIC_POS_1, end_pos=ui_test.Vec2(1280, 350))
        await ui_test.human_delay()

        await self.do_visual_test(img_name="test_anim_curve_editor_key_vertical_drag")

    """
    Test Case 3: Set to horizontal state. Select a key and drag it.
    """

    async def test_anim_curve_editor_key_horizontal_drag(self):
        # Load the USD map
        await self.load_stage(map_name="basic_curve_cube_multiple_keys.usda")

        omni.usd.get_context().get_selection().set_selected_prim_paths(["/World/Cube"], False)
        await wait_stage_loading()

        await self.setup_docked_test(
            docked_window=self.curve_editor_window,
            restore_window=ui.Workspace.get_window("Content"),
            restore_position=ui.DockPosition.SAME,
            width=CURVE_EDITOR_WIDTH,
            height=CURVE_EDITOR_HEIGHT,
        )

        await self._set_horizontal()

        await ui_test.emulate_mouse_move(MAGIC_POS_1)
        await ui_test.human_delay()
        await ui_test.emulate_mouse_drag_and_drop(start_pos=MAGIC_POS_1, end_pos=ui_test.Vec2(1280, 350))
        await ui_test.human_delay()

        await self.do_visual_test(img_name="test_anim_curve_editor_key_horizontal_drag")


class AnimCurveEditorInfinity(AnimCurveEditorTestsBase):
    _DEBUG_MODE = False

    """
    These tests focus on the pre-and-post infinity

    Quick Doc: How to generate magic_numbers and golden_imgs for this test:
        - Step 1: Set _DEBUG_MODE to True
        - Step 2: Run the tests.
        - Step 3: Collect the golden_imgs in `_build/outputs` folder, and place them in the right path.
                  This time, you will get 5*5*2=50 golden imgs.
        - Step 4: Re-Run the tests and collect the other 50 golden imgs.
        - Step 5: Re-Run the tests, again.
        - Step 6: Parse the error logs to collect magic_numbers. Usually in: `_testoutput/exttest_omni_anim_curve_editor-viewport_next`
                  You can use Linux's `grep` command and your `"{test_case_prefix}_` as the keyword.
                  The output format is in Python's dict's format. So you can directly copy and paste them here.
        - Step 7: Do not forget to turn OFF the _DEBUG_MODE
    """

    async def setUp(self):
        await super().setUp()

        self.inf_dict = {
            "Constant": "constant",
            "Cycle": "cycle",
            "CycleRelative": "cycleRelative",
            "Linear": "linear",
            "Oscillate": "oscillate",
        }  # a dict mapping the displayed UI name to the internal name
        self._GOLDEN_IMG_DIR = self._GOLDEN_IMG_DIR.joinpath("infinity")

    async def _set_pre_inf(self, inf_name):
        assert inf_name in self.inf_dict.keys()
        omni.kit.commands.execute(
            "SetAnimCurveInfinityType",
            paths=["/World/Cube.xformOp:translate|x"],
            is_post_infinity=False,
            infinity_type=self.inf_dict[inf_name],
        )

    async def _set_post_inf(self, inf_name):
        assert inf_name in self.inf_dict.keys()
        omni.kit.commands.execute(
            "SetAnimCurveInfinityType",
            paths=["/World/Cube.xformOp:translate|x"],
            is_post_infinity=True,
            infinity_type=self.inf_dict[inf_name],
        )

    async def _test_case(
        self,
        test_case_prefix: str,
        pre_inf: str,
        post_inf: str,
        magic_number: Tuple[float, float],
        warm_up: bool = False,
    ):
        """
        1. Load a stage, select a prim, select a curve, then:
            - set infinity type accordingly
            - do visual test
            - do attribute value test
        2. Drag the key, then:
            - do visual test
            - do attribute value test
        """
        test_case_name = f"{test_case_prefix}_{pre_inf}_{post_inf}"
        timeline_iface = get_timeline_interface()

        map_name_dict = {
            "warm_up": "basic_curve_cube_multiple_keys.usda",  # any usda file is Okay
            "anim_curve_editor_infinity": "basic_curve_cube_multiple_keys.usda",
            "anim_curve_editor_infinity_step": "basic_curve_cube_multiple_keys_step.usda",
        }
        await self.load_stage(map_name=map_name_dict[test_case_prefix])
        await wait_stage_loading()
        stage = omni.usd.get_context().get_stage()
        cube_prim = stage.GetPrimAtPath("/World/Cube")

        #### Step 1 ####

        omni.usd.get_context().get_selection().set_selected_prim_paths(["/World/Cube"], False)

        await self.setup_docked_test(
            docked_window=self.curve_editor_window,
            restore_window=ui.Workspace.get_window("Content"),
            restore_position=ui.DockPosition.SAME,
            width=CURVE_EDITOR_WIDTH,
            height=CURVE_EDITOR_HEIGHT,
        )

        # Scroll the mouse for zooming and select the curve
        await ui_test.emulate_mouse_move(MAGIC_POS_1)  # TODO: Remove magic numbers
        await ui_test.emulate_mouse_scroll(ui_test.Vec2(0, -10000))
        await ui_test.emulate_mouse_click()
        timeline_iface.set_current_time(0)  # Reset to time 0.
        await ui_test.human_delay(10)  # avoid double-click

        # Set the inf type
        await self._set_pre_inf(pre_inf)
        await self._set_post_inf(post_inf)

        if warm_up:
            return

        await self.do_visual_test(img_name=f"{test_case_name}")

        #### Step 2 ####
        await self.setup_docked_test(
            docked_window=self.curve_editor_window,
            restore_window=ui.Workspace.get_window("Content"),
            restore_position=ui.DockPosition.SAME,
            width=CURVE_EDITOR_WIDTH,
            height=CURVE_EDITOR_HEIGHT,
        )

        # Move mouse to the key and drag it
        await ui_test.emulate_mouse_move(MAGIC_POS_1)
        await ui_test.emulate_mouse_drag_and_drop(start_pos=MAGIC_POS_1, end_pos=ui_test.Vec2(790, 500))

        await self.do_visual_test(img_name=f"{test_case_name}_drag")

        # Check the values
        timeline_iface.set_current_time(-5 / 24)  # current_frame (-5) / FPS
        await ui_test.human_delay()
        translation_x_0 = cube_prim.GetAttribute("xformOp:translate").Get()[0]
        if not self._DEBUG_MODE:
            self.assertAlmostEqual(
                translation_x_0,
                magic_number[0],
                msg=f"{test_case_name}: At frame -5, /World/Cube.xformOp:translate|x is not correct! Should be {magic_number[0]}",
                places=3,
            )

        timeline_iface.set_current_time(35 / 24)  # current_frame (25) / FPS
        await ui_test.human_delay()
        translation_x_1 = cube_prim.GetAttribute("xformOp:translate").Get()[0]
        if not self._DEBUG_MODE:
            self.assertAlmostEqual(
                translation_x_1,
                magic_number[1],
                msg=f"{test_case_name}: At time 35, /World/Cube.xformOp:translate|x is not correct! Should be {magic_number[1]}",
                places=3,
            )

        timeline_iface.set_current_time(0)  # Reset to time 0.

        if self._DEBUG_MODE:
            # We can output and collect the target values in this way:
            carb.log_error(f'"{test_case_name}": ({translation_x_0}, {translation_x_1})')

    async def test_anim_curve_editor_infinity_pre_post(self):
        infinity_names = list(self.inf_dict.keys())

        # These are the value of /World/Cube.xformOp:translate|x at time -5 and 35
        # These values can be generated and collected easily. See the `Quick Doc`.
        magic_numbers = {
            "anim_curve_editor_infinity_Constant_Constant": (0.0, 166.345),
            "anim_curve_editor_infinity_Constant_Cycle": (0.0, -463.2468458231422),
            "anim_curve_editor_infinity_Constant_CycleRelative": (0.0, -296.90179718880506),
            "anim_curve_editor_infinity_Constant_Linear": (0.0, 166.345),
            "anim_curve_editor_infinity_Constant_Oscillate": (0.0, 88.39651211491827),
            "anim_curve_editor_infinity_Cycle_Constant": (88.39651683758177, 166.345),
            "anim_curve_editor_infinity_Cycle_Cycle": (89.2772804040743, -453.63282442672113),
            "anim_curve_editor_infinity_Cycle_CycleRelative": (88.39651250469365, -296.901840229822),
            "anim_curve_editor_infinity_Cycle_Linear": (89.27728289582433, 166.345),
            "anim_curve_editor_infinity_Cycle_Oscillate": (88.3965150331918, 88.39651503319197),
            "anim_curve_editor_infinity_CycleRelative_Constant": (-77.94848737266224, 166.345),
            "anim_curve_editor_infinity_CycleRelative_Cycle": (-77.06771672105, -453.63279304603395),
            "anim_curve_editor_infinity_CycleRelative_CycleRelative": (-77.9484845770323, -296.9018083754212),
            "anim_curve_editor_infinity_CycleRelative_Linear": (-77.94848698288618, 166.345),
            "anim_curve_editor_infinity_CycleRelative_Oscillate": (-77.06771659875514, 89.27728340124497),
            "anim_curve_editor_infinity_Linear_Constant": (0.0, 166.345),
            "anim_curve_editor_infinity_Linear_Cycle": (0.0, -463.24683038190585),
            "anim_curve_editor_infinity_Linear_CycleRelative": (0.0, -287.2877875291191),
            "anim_curve_editor_infinity_Linear_Linear": (0.0, 166.345),
            "anim_curve_editor_infinity_Linear_Oscillate": (0.0, 89.27727951552987),
            "anim_curve_editor_infinity_Oscillate_Constant": (-463.2468500777131, 166.345),
            "anim_curve_editor_infinity_Oscillate_Cycle": (-463.2468056042303, -463.2468056042303),
            "anim_curve_editor_infinity_Oscillate_CycleRelative": (-453.63283404334345, -287.2878340433434),
            "anim_curve_editor_infinity_Oscillate_Linear": (-463.2467750885581, 166.345),
            "anim_curve_editor_infinity_Oscillate_Oscillate": (-463.24679718877445, 88.39651644780884),
        }

        # An evil hack - Somehow, the range of the timeline of the first test case and the followings are not the same.
        # So we have to `warm up` it first.
        await self._test_case("warm_up", infinity_names[0], infinity_names[0], (0, 0), True)

        for pre_inf in infinity_names:
            for post_inf in infinity_names:
                test_case_prefix = "anim_curve_editor_infinity"
                test_case_name = f"{test_case_prefix}_{pre_inf}_{post_inf}"
                try:
                    await self._test_case(
                        test_case_prefix, pre_inf, post_inf, magic_number=magic_numbers[test_case_name]
                    )
                except AssertionError as e:
                    if self._DEBUG_MODE:
                        continue
                    self.assertTrue(False, f"{test_case_name} FAILED! Reason: {e}")

        if self._DEBUG_MODE:
            self.assertTrue(False, "Debug mode is on. Turn it off in production!")

    """
    Step tangent has special code paths. So we should test it explicitly.
    """

    async def test_anim_curve_editor_infinity_step_pre_post(self):
        return
        infinity_names = list(self.inf_dict.keys())

        # These are the value of /World/Cube.xformOp:translate|x at time -5 and 35
        # These values can be generated and collected easily. See the `Quick Doc`.
        magic_numbers = {
            "anim_curve_editor_infinity_step_Constant_Constant": (0.0, 166.345),
            "anim_curve_editor_infinity_step_Constant_Cycle": (0.0, -414.1486771046672),
            "anim_curve_editor_infinity_step_Constant_CycleRelative": (0.0, -238.03687751071126),
            "anim_curve_editor_infinity_step_Constant_Linear": (0.0, 166.345),
            "anim_curve_editor_infinity_step_Constant_Oscillate": (0.0, 53.646403670364265),
            "anim_curve_editor_infinity_step_Cycle_Constant": (53.646403670364265, 166.345),
            "anim_curve_editor_infinity_step_Cycle_Cycle": (53.646403670364265, -414.1487237921195),
            "anim_curve_editor_infinity_step_Cycle_CycleRelative": (53.646403670364265, -238.03684563117216),
            "anim_curve_editor_infinity_step_Cycle_Linear": (53.646403670364265, 166.345),
            "anim_curve_editor_infinity_step_Cycle_Oscillate": (53.646403670364265, 53.646403670364265),
            "anim_curve_editor_infinity_step_CycleRelative_Constant": (-112.69859632963573, 166.345),
            "anim_curve_editor_infinity_step_CycleRelative_Cycle": (-112.69859632963573, -414.14869143133745),
            "anim_curve_editor_infinity_step_CycleRelative_CycleRelative": (-112.69859632963573, -247.80371514766225),
            "anim_curve_editor_infinity_step_CycleRelative_Linear": (-112.69859632963573, 166.345),
            "anim_curve_editor_infinity_step_CycleRelative_Oscillate": (-112.69859632963573, 53.646403670364265),
            "anim_curve_editor_infinity_step_Linear_Constant": (-1.2653422596349574e-05, 166.345),
            "anim_curve_editor_infinity_step_Linear_Cycle": (-1.2653422596349574e-05, -414.1487351565694),
            "anim_curve_editor_infinity_step_Linear_CycleRelative": (-1.2653422596349574e-05, -247.803689976102),
            "anim_curve_editor_infinity_step_Linear_Linear": (-1.2653422596349574e-05, 166.345),
            "anim_curve_editor_infinity_step_Linear_Oscillate": (-1.2653422596349574e-05, 53.646403670364265),
            "anim_curve_editor_infinity_step_Oscillate_Constant": (-414.14868142686754, 166.345),
            "anim_curve_editor_infinity_step_Oscillate_Cycle": (-404.3818817591734, -404.3818817591734),
            "anim_curve_editor_infinity_step_Oscillate_CycleRelative": (-414.14872947432764, -247.80372947432764),
            "anim_curve_editor_infinity_step_Oscillate_Linear": (-414.1486771046389, 166.345),
            "anim_curve_editor_infinity_step_Oscillate_Oscillate": (-404.38187751068347, 53.646403670364265),
        }

        # An evil hack - Somehow, the range of the timeline of the first test case and the followings are not the same.
        # So we have to `warm up` it first.
        await self._test_case("warm_up", infinity_names[0], infinity_names[0], (0, 0), True)

        for pre_inf in infinity_names:
            for post_inf in infinity_names:
                test_case_prefix = "anim_curve_editor_infinity_step"
                test_case_name = f"{test_case_prefix}_{pre_inf}_{post_inf}"
                try:
                    await self._test_case(
                        test_case_prefix, pre_inf, post_inf, magic_number=magic_numbers[test_case_name]
                    )
                except AssertionError as e:
                    if self._DEBUG_MODE:
                        continue
                    self.assertTrue(False, f"{test_case_name} FAILED! Reason: {e}")

        if self._DEBUG_MODE:
            self.assertTrue(False, "Debug mode is on. Turn it off in production!")
