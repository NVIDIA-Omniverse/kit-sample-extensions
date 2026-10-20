# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
import os
import sys
import unittest
from pathlib import Path

import carb.settings
import omni.kit.app
import omni.kit.undo
import omni.usd
from carb.input import KeyboardInput, MouseEventType
from omni import ui
from omni.kit import ui_test
from omni.kit.markup.core import MARKUP_ROOT_PRIM_PATH
from omni.kit.markup.core import get_instance as get_markup_instance
from omni.kit.viewport.utility import get_active_viewport, get_active_viewport_window, next_viewport_frame_async
from omni.ui.tests.test_base import OmniUiTest
from pxr import Sdf, Usd, UsdGeom

from ..ui.constant import MARKUP_LETTERBOX_COLOR, TOOL_NAME
from ..ui.markup_scene import MARKUP_TOOL_CURRENT, SETTINGS_MARKUP_ACTIVE, SETTINGS_MARKUP_EDITING

CURRENT_PATH = Path(__file__).parent
TEST_DATA_PATH = CURRENT_PATH.parent.parent.parent.parent.parent.joinpath("data").joinpath("tests")
VISIBILITY_PATH = "/persistent/app/viewport/displayOptions"


class TestMarkupToolExtension(OmniUiTest):
    async def test_extension(self):
        manager = omni.kit.app.get_app().get_extension_manager()
        ext_id = "omni.kit.tool.markup"
        self.assertTrue(ext_id)
        self.assertTrue(manager.is_extension_enabled(ext_id))
        manager.set_extension_enabled(ext_id, False)
        await ui_test.human_delay()
        self.assertTrue(not manager.is_extension_enabled(ext_id))
        manager.set_extension_enabled(ext_id, True)
        await ui_test.human_delay()
        self.assertTrue(manager.is_extension_enabled(ext_id))


class TestMarkupShapeTool(OmniUiTest):

    # Before running each test
    async def setUp(self):
        await super().setUp()
        self._setting = carb.settings.get_settings()
        self._golden_img_dir = TEST_DATA_PATH.absolute().joinpath("golden_img").absolute()
        self._visibility_value = self._setting.get(VISIBILITY_PATH)
        self._setting.set(VISIBILITY_PATH, 0)

        await omni.usd.get_context().new_stage_async()  # type: ignore
        await ui_test.human_delay(10)

        get_markup_instance().create_markup()  # type: ignore
        await ui_test.human_delay()
        await self._dock_viewport(width=1280, height=720)
        self._setting.set_string(MARKUP_TOOL_CURRENT, TOOL_NAME.SHAPES)

    async def _wait_for_viewport(self):
        await next_viewport_frame_async(get_active_viewport())
        for _ in range(3):
            await omni.kit.app.get_app().next_update_async()

    async def _dock_viewport(self, width=1200, height=900, block_device=True):
        """Utility function to dock viewport window and focus on turntable panel."""
        for window in ui.Workspace.get_windows():
            ui.Workspace.show_window(window.title, False)

        viewport = get_active_viewport_window()
        viewport.width = width  # type: ignore
        viewport.height = height  # type: ignore
        viewport.visible = True
        await self._wait_for_viewport()

    # After running each test
    async def tearDown(self):
        self._setting.set(VISIBILITY_PATH, self._visibility_value)
        self._setting.set_string(MARKUP_TOOL_CURRENT, "")
        self._setting.set_string(SETTINGS_MARKUP_EDITING, "")
        self._setting.set_string(SETTINGS_MARKUP_ACTIVE, "")
        await super().tearDown()

    async def test_shape_tool_01(self):
        start = ui_test.Vec2(200, 200)
        end = ui_test.Vec2(400, 500)
        await ui_test.emulate_mouse_move(start)
        await ui_test.emulate_mouse_drag_and_drop(start, end)
        await ui_test.human_delay()
        await self.finalize_test(golden_img_dir=self._golden_img_dir, golden_img_name="shape_tool_01.png")

    async def test_shape_tool_02(self):
        start = ui_test.Vec2(200, 200)
        end = ui_test.Vec2(400, 500)
        async with ui_test.KeyDownScope(KeyboardInput.LEFT_SHIFT):
            await ui_test.emulate_mouse_move(start)
            await ui_test.emulate_mouse_drag_and_drop(start, end)
        await ui_test.human_delay()
        await self.finalize_test(golden_img_dir=self._golden_img_dir, golden_img_name="shape_tool_02.png")

    async def test_shape_tool_03(self):
        start = ui_test.Vec2(200, 200)
        end = ui_test.Vec2(400, 500)
        async with ui_test.KeyDownScope(KeyboardInput.LEFT_CONTROL):
            await ui_test.emulate_mouse_move(start)
            await ui_test.emulate_mouse_drag_and_drop(start, end)
        await ui_test.human_delay()
        await self.finalize_test(golden_img_dir=self._golden_img_dir, golden_img_name="shape_tool_03.png")

    async def test_shape_tool_04(self):
        start = ui_test.Vec2(200, 200)
        end = ui_test.Vec2(400, 500)
        async with ui_test.KeyDownScope(KeyboardInput.LEFT_CONTROL):
            async with ui_test.KeyDownScope(KeyboardInput.LEFT_SHIFT):
                await ui_test.emulate_mouse_move(start)
                await ui_test.emulate_mouse_drag_and_drop(start, end)
        await ui_test.human_delay()
        await self.finalize_test(golden_img_dir=self._golden_img_dir, golden_img_name="shape_tool_04.png")

    async def test_shape_tool_05(self):
        start = ui_test.Vec2(200, 200)
        end = ui_test.Vec2(400, 500)
        await ui_test.emulate_mouse_move(start)
        await ui_test.emulate_mouse_drag_and_drop(start, end)
        await ui_test.human_delay()
        start = ui_test.Vec2(200, 200)
        end = ui_test.Vec2(300, 350)
        await ui_test.emulate_mouse_move(start)
        await ui_test.emulate_mouse_drag_and_drop(start, end)
        await ui_test.human_delay()
        start = ui_test.Vec2(200, 350)
        end = ui_test.Vec2(400, 650)
        await ui_test.emulate_mouse_move(start)
        await ui_test.emulate_mouse_drag_and_drop(start, end)
        await ui_test.human_delay()
        await self.finalize_test(golden_img_dir=self._golden_img_dir, golden_img_name="shape_tool_05.png")

    async def test_shape_tool_create_undo(self):

        stage = omni.usd.get_context().get_stage()
        markup_prim = stage.GetPrimAtPath(f"{MARKUP_ROOT_PRIM_PATH}/Markup_00/Rectangle_0")
        self.assertFalse(markup_prim)  # we shouldn't have any valid markup prim at first.

        start = ui_test.Vec2(200, 200)
        end = ui_test.Vec2(400, 500)
        await ui_test.emulate_mouse_move(start)
        await ui_test.emulate_mouse_drag_and_drop(start, end)
        await ui_test.human_delay()

        markup_prim = stage.GetPrimAtPath(f"{MARKUP_ROOT_PRIM_PATH}/Markup_00/Rectangle_0")
        self.assertTrue(markup_prim)  # we SHOULD have a markup now.

        omni.kit.undo.undo()

        markup_prim = stage.GetPrimAtPath(f"{MARKUP_ROOT_PRIM_PATH}/Markup_00/Rectangle_0")
        self.assertFalse(markup_prim)  # markup prim should be gone after a single undo.

        omni.kit.undo.redo()

        markup_prim = stage.GetPrimAtPath(f"{MARKUP_ROOT_PRIM_PATH}/Markup_00/Rectangle_0")
        self.assertTrue(markup_prim)  # markup prim should return.

        await self.finalize_test_no_image()

    async def test_shape_tool_letterbox(self):
        letterbox_color = self._setting.get(MARKUP_LETTERBOX_COLOR)
        self._setting.set(MARKUP_LETTERBOX_COLOR, 0xFF0000FF)
        start = ui_test.Vec2(1278, 718)
        end = ui_test.Vec2(540, 540)
        await ui_test.emulate_mouse_move(start)
        await ui_test.emulate_mouse_drag_and_drop(start, end)
        await ui_test.human_delay()
        await self.finalize_test(golden_img_dir=self._golden_img_dir, golden_img_name="test_shape_tool_letterbox.png")
        await ui_test.emulate_mouse_move(end)
        await ui_test.emulate_mouse_drag_and_drop(end, start)
        self._setting.set(MARKUP_LETTERBOX_COLOR, letterbox_color)


class TestMarkupArrowTool(OmniUiTest):

    # Before running each test
    async def setUp(self):
        await super().setUp()
        self._setting = carb.settings.get_settings()
        self._golden_img_dir = TEST_DATA_PATH.absolute().joinpath("golden_img").absolute()
        self._visibility_value = self._setting.get(VISIBILITY_PATH)
        self._setting.set(VISIBILITY_PATH, 0)
        await omni.usd.get_context().new_stage_async()  # type: ignore
        await ui_test.human_delay()
        get_markup_instance().create_markup()  # type: ignore
        await ui_test.human_delay()
        await self._dock_viewport(width=1280, height=720)
        self._setting.set_string(MARKUP_TOOL_CURRENT, TOOL_NAME.ARROW)

    async def _wait_for_viewport(self):
        await next_viewport_frame_async(get_active_viewport())
        for _ in range(3):
            await omni.kit.app.get_app().next_update_async()

    async def _dock_viewport(self, width=1200, height=900, block_device=True):
        """Utility function to dock viewport window and focus on turntable panel."""
        for window in ui.Workspace.get_windows():
            ui.Workspace.show_window(window.title, False)

        viewport = get_active_viewport_window()
        viewport.width = width  # type: ignore
        viewport.height = height  # type: ignore
        viewport.visible = True
        await self._wait_for_viewport()

    # After running each test
    async def tearDown(self):
        self._setting.set(VISIBILITY_PATH, self._visibility_value)
        await super().tearDown()
        self._setting.set_string(MARKUP_TOOL_CURRENT, "")
        self._setting.set_string(SETTINGS_MARKUP_EDITING, "")
        self._setting.set_string(SETTINGS_MARKUP_ACTIVE, "")

    async def test_arrow_tool_01(self):
        start = ui_test.Vec2(200, 200)
        end = ui_test.Vec2(400, 500)
        await ui_test.emulate_mouse_move(start)
        await ui_test.emulate_mouse_drag_and_drop(start, end)
        await ui_test.human_delay()
        await self.finalize_test(golden_img_dir=self._golden_img_dir, golden_img_name="arrow_tool_01.png")

    async def test_arrow_tool_02(self):
        start = ui_test.Vec2(200, 200)
        end = ui_test.Vec2(400, 500)
        await ui_test.emulate_mouse_move(start)
        await ui_test.emulate_mouse_drag_and_drop(start, end)
        await ui_test.human_delay()
        start = ui_test.Vec2(200, 200)
        end = ui_test.Vec2(500, 400)
        await ui_test.emulate_mouse_move(start)
        await ui_test.emulate_mouse_drag_and_drop(start, end)
        await ui_test.human_delay()
        start = ui_test.Vec2(350, 300)
        end = ui_test.Vec2(500, 200)
        await ui_test.emulate_mouse_move(start)
        await ui_test.emulate_mouse_drag_and_drop(start, end)
        await ui_test.human_delay()
        await self.finalize_test(golden_img_dir=self._golden_img_dir, golden_img_name="arrow_tool_02.png")


class TestMarkupLineTool(OmniUiTest):

    # Before running each test
    async def setUp(self):
        await super().setUp()
        self._setting = carb.settings.get_settings()
        self._golden_img_dir = TEST_DATA_PATH.absolute().joinpath("golden_img").absolute()
        self._visibility_value = self._setting.get(VISIBILITY_PATH)
        self._setting.set(VISIBILITY_PATH, 0)
        await omni.usd.get_context().new_stage_async()  # type: ignore
        await ui_test.human_delay()
        get_markup_instance().create_markup()  # type: ignore
        await ui_test.human_delay()
        await self._dock_viewport(width=1280, height=720)
        self._setting.set_string(MARKUP_TOOL_CURRENT, TOOL_NAME.LINE)

    async def _wait_for_viewport(self):
        await next_viewport_frame_async(get_active_viewport())
        for _ in range(3):
            await omni.kit.app.get_app().next_update_async()

    async def _dock_viewport(self, width=1200, height=900, block_device=True):
        """Utility function to dock viewport window and focus on turntable panel."""
        for window in ui.Workspace.get_windows():
            ui.Workspace.show_window(window.title, False)

        viewport = get_active_viewport_window()
        viewport.width = width  # type: ignore
        viewport.height = height  # type: ignore
        viewport.visible = True
        await ui_test.wait_n_updates()
        await self._wait_for_viewport()

    # After running each test
    async def tearDown(self):
        self._setting.set(VISIBILITY_PATH, self._visibility_value)
        await super().tearDown()
        self._setting.set_string(MARKUP_TOOL_CURRENT, "")
        self._setting.set_string(SETTINGS_MARKUP_EDITING, "")
        self._setting.set_string(SETTINGS_MARKUP_ACTIVE, "")

    async def test_line_tool_01(self):
        await ui_test.human_delay()
        start = ui_test.Vec2(200, 200)
        end = ui_test.Vec2(400, 500)
        await ui_test.emulate_mouse_move(start)
        await ui_test.emulate_mouse_drag_and_drop(start, end)
        await ui_test.human_delay()
        await ui_test.human_delay()
        # give a threshold to fix the flaky test failed
        await self.finalize_test(threshold=0.2, golden_img_dir=self._golden_img_dir, golden_img_name="line_tool_01.png")

    async def test_line_tool_02(self):
        start = ui_test.Vec2(200, 200)
        end = ui_test.Vec2(400, 500)
        await ui_test.emulate_mouse_move(start)
        await ui_test.emulate_mouse_drag_and_drop(start, end)
        await ui_test.human_delay()
        start = ui_test.Vec2(200, 200)
        end = ui_test.Vec2(500, 400)
        await ui_test.emulate_mouse_move(start)
        await ui_test.emulate_mouse_drag_and_drop(start, end)
        await ui_test.human_delay()
        start = ui_test.Vec2(350, 300)
        end = ui_test.Vec2(500, 200)
        await ui_test.emulate_mouse_move(start)
        await ui_test.emulate_mouse_drag_and_drop(start, end)
        await ui_test.human_delay()
        await self.finalize_test(golden_img_dir=self._golden_img_dir, golden_img_name="line_tool_02.png")


class TestMarkupCommentTool(OmniUiTest):

    # Before running each test
    async def setUp(self):
        await super().setUp()
        self._setting = carb.settings.get_settings()
        self._golden_img_dir = TEST_DATA_PATH.absolute().joinpath("golden_img").absolute()
        self._visibility_value = self._setting.get(VISIBILITY_PATH)
        self._setting.set(VISIBILITY_PATH, 0)
        await omni.usd.get_context().new_stage_async()  # type: ignore
        await ui_test.human_delay()
        get_markup_instance().create_markup()  # type: ignore
        await ui_test.human_delay()
        await self._dock_viewport(width=1280, height=720)
        self._setting.set_string(MARKUP_TOOL_CURRENT, TOOL_NAME.COMMENT)

    async def _wait_for_viewport(self):
        await next_viewport_frame_async(get_active_viewport())
        for _ in range(3):
            await omni.kit.app.get_app().next_update_async()

    async def _dock_viewport(self, width=1200, height=900, block_device=True):
        """Utility function to dock viewport window and focus on turntable panel."""
        for window in ui.Workspace.get_windows():
            ui.Workspace.show_window(window.title, False)

        viewport = get_active_viewport_window()
        viewport.width = width  # type: ignore
        viewport.height = height  # type: ignore
        viewport.visible = True
        await self._wait_for_viewport()

    # After running each test
    async def tearDown(self):
        self._setting.set(VISIBILITY_PATH, self._visibility_value)
        await super().tearDown()
        self._setting.set_string(MARKUP_TOOL_CURRENT, "")
        self._setting.set_string(SETTINGS_MARKUP_EDITING, "")
        self._setting.set_string(SETTINGS_MARKUP_ACTIVE, "")

    async def test_comment_tool_01(self):
        start = ui_test.Vec2(200, 200)
        await ui_test.emulate_mouse_move(start)
        await ui_test.emulate_mouse_click()
        await ui_test.human_delay()
        await self.finalize_test(golden_img_dir=self._golden_img_dir, golden_img_name="comment_tool_01.png")

    async def test_comment_tool_02(self):
        start = ui_test.Vec2(200, 200)
        await ui_test.emulate_mouse_move(start)
        await ui_test.emulate_mouse_click()
        await ui_test.human_delay()
        await ui_test.emulate_char_press(
            "The quick brown fox jumped over the lazy dog.  The quick brown fox jumped over the lazy dog.  The quick brown fox jumped over the lazy dog..."
        )
        await ui_test.emulate_mouse_move(ui_test.Vec2(150, 150))
        await ui_test.human_delay()
        await ui_test.emulate_mouse_click()
        await ui_test.human_delay()
        await self.finalize_test(golden_img_dir=self._golden_img_dir, golden_img_name="comment_tool_02.png")

    async def test_comment_tool_change_font_size(self):
        # regression test for OMFP-3180
        stage = omni.usd.get_context().get_stage()
        sample_text = "foobar."
        prim_path = f"{MARKUP_ROOT_PRIM_PATH}/Markup_00/Label_0"
        text_s_identifier = f"_markup_edit_{prim_path}_text_text_s_btn"
        text_m_identifier = f"_markup_edit_{prim_path}_text_text_m_btn"

        # No prims or buttons, yet.
        markup_prim = stage.GetPrimAtPath(prim_path)
        buttons = {
            w.widget.identifier: w
            for w in ui_test.find_all("Viewport//Frame/**")
            if text_s_identifier in w.widget.identifier or text_m_identifier in w.widget.identifier
        }
        self.assertFalse(markup_prim)
        self.assertTrue(len(buttons) == 0)

        # Make a Comment markup
        start = ui_test.Vec2(200, 200)
        await ui_test.emulate_mouse_move(start)
        await ui_test.emulate_mouse_click()
        await ui_test.human_delay()

        markup_prim = stage.GetPrimAtPath(prim_path)
        self.assertTrue(markup_prim)

        # add some text (but don't change focus to end edit)
        await ui_test.emulate_char_press(sample_text)

        buttons = {
            w.widget.identifier: w
            for w in ui_test.find_all("Viewport//Frame/**")
            if text_s_identifier in w.widget.identifier or text_m_identifier in w.widget.identifier
        }
        self.assertTrue(len(buttons) == 2)

        # click two things to ensure we've triggered a style update
        await buttons[text_s_identifier].click()
        await buttons[text_m_identifier].click()

        # Now make sure the sample text was correctly committed to the prim.
        markup_prim = stage.GetPrimAtPath(prim_path)
        self.assertTrue(markup_prim)

        self.assertTrue(markup_prim.HasAttribute("text"))
        self.assertTrue(markup_prim.GetAttribute("text").Get() == sample_text)

    async def test_comment_tool_at_border(self):
        # OMPE-1518: Test if markups shift when a new comment is added near the border of canvas
        async def add_comment(x, y):
            pos = ui_test.Vec2(x, y)
            await ui_test.emulate_mouse_move(pos)
            await ui_test.emulate_mouse_click()
            await ui_test.human_delay()
            await ui_test.emulate_char_press("The quick brown fox jumped over the lazy dog.")
            await ui_test.emulate_mouse_move(ui_test.Vec2(150, 150))
            await ui_test.human_delay()
            await ui_test.emulate_mouse_click()
            await ui_test.human_delay()

        await add_comment(200, 200)

        # Add comment at right border
        await add_comment(1270, 160)
        await add_comment(1260, 360)
        await add_comment(1268, 560)

        # Add comment at bottom border
        await add_comment(100, 710)
        await add_comment(900, 690)
        await add_comment(1260, 695)

        await self.finalize_test(golden_img_dir=self._golden_img_dir, golden_img_name="comment_tool_at_border.png")


class TestMarkupDrawTool(OmniUiTest):

    # Before running each test
    async def setUp(self):
        await super().setUp()
        self._setting = carb.settings.get_settings()
        self._golden_img_dir = TEST_DATA_PATH.absolute().joinpath("golden_img").absolute()
        self._visibility_value = self._setting.get(VISIBILITY_PATH)
        self._setting.set(VISIBILITY_PATH, 0)
        await omni.usd.get_context().new_stage_async()  # type: ignore
        await ui_test.human_delay()
        get_markup_instance().create_markup()  # type: ignore
        await ui_test.human_delay()
        await self._dock_viewport(width=1280, height=720)
        self._setting.set_string(MARKUP_TOOL_CURRENT, TOOL_NAME.DRAW)

    async def _wait_for_viewport(self):
        await next_viewport_frame_async(get_active_viewport())
        for _ in range(3):
            await omni.kit.app.get_app().next_update_async()

    async def _dock_viewport(self, width=1200, height=900, block_device=True):
        """Utility function to dock viewport window and focus on turntable panel."""
        for window in ui.Workspace.get_windows():
            ui.Workspace.show_window(window.title, False)

        viewport = get_active_viewport_window()
        viewport.width = width  # type: ignore
        viewport.height = height  # type: ignore
        viewport.visible = True
        await self._wait_for_viewport()

    # After running each test
    async def tearDown(self):
        self._setting.set(VISIBILITY_PATH, self._visibility_value)
        await super().tearDown()
        self._setting.set_string(MARKUP_TOOL_CURRENT, "")
        self._setting.set_string(SETTINGS_MARKUP_EDITING, "")
        self._setting.set_string(SETTINGS_MARKUP_ACTIVE, "")

    # @unittest.skip("Causes a crash in C++ 'attempted member lookup on NULL TfWeakPtr<UsdStage>'")
    async def test_draw_tool_01(self):
        async def emulate_mouse_down():
            await ui_test.input.emulate_mouse(MouseEventType.LEFT_BUTTON_DOWN)
            await ui_test.human_delay()

        async def emulate_mouse_up():
            await ui_test.input.emulate_mouse(MouseEventType.LEFT_BUTTON_UP)
            await ui_test.human_delay()

        start = ui_test.Vec2(200, 200)
        await ui_test.emulate_mouse_move(start)
        points = [
            ui_test.Vec2(205, 205),
            ui_test.Vec2(210, 215),
            ui_test.Vec2(220, 225),
            ui_test.Vec2(300, 150),
        ]
        try:
            await emulate_mouse_down()
            for point in points:
                await ui_test.emulate_mouse_move(point)
                await ui_test.human_delay()
        finally:
            await ui_test.human_delay()
            await emulate_mouse_up()
        await ui_test.human_delay()
        await self.finalize_test(golden_img_dir=self._golden_img_dir, golden_img_name="draw_tool_01.png", threshold=0.1)

    # @unittest.skip("Causes a crash in C++ 'attempted member lookup on NULL TfWeakPtr<UsdStage>'")
    @unittest.skipIf(
        sys.platform.startswith("linux"), "Drawing outside the window seems to fail hard, need to look deeper."
    )
    async def test_draw_tool_02(self):
        async def emulate_mouse_down():
            await ui_test.input.emulate_mouse(MouseEventType.LEFT_BUTTON_DOWN)
            await ui_test.human_delay()

        async def emulate_mouse_up():
            await ui_test.input.emulate_mouse(MouseEventType.LEFT_BUTTON_UP)
            await ui_test.human_delay()

        start = ui_test.Vec2(200, 200)
        await ui_test.emulate_mouse_move(start)
        points = [
            ui_test.Vec2(205, 205),
            ui_test.Vec2(10000, 205),
            ui_test.Vec2(10000, 225),
            ui_test.Vec2(205, 225),
        ]
        try:
            await emulate_mouse_down()
            for point in points:
                await ui_test.emulate_mouse_move(point)
                await ui_test.human_delay()
        finally:
            await ui_test.human_delay()
            await emulate_mouse_up()
        await ui_test.human_delay()
        await self.finalize_test(golden_img_dir=self._golden_img_dir, golden_img_name="draw_tool_02.png", threshold=0.1)

    async def test_draw_tool_03(self):
        async def emulate_mouse_down():
            await ui_test.input.emulate_mouse(MouseEventType.LEFT_BUTTON_DOWN)
            await ui_test.human_delay()

        async def emulate_mouse_up():
            await ui_test.input.emulate_mouse(MouseEventType.LEFT_BUTTON_UP)
            await ui_test.human_delay()

        start = ui_test.Vec2(200, 200)
        await ui_test.emulate_mouse_move(start)
        points1 = [
            ui_test.Vec2(200, 215),
            ui_test.Vec2(210, 215),
            ui_test.Vec2(215, 225),
            ui_test.Vec2(300, 150),
        ]
        points2 = [
            ui_test.Vec2(200, 215),
            ui_test.Vec2(210, 225),
            ui_test.Vec2(215, 245),
            ui_test.Vec2(300, 150),
        ]
        points3 = [
            ui_test.Vec2(257.5, 197.5),
            ui_test.Vec2(300, 300),
            ui_test.Vec2(400, 200),
        ]
        for points in [points1, points2, points3]:
            try:
                await ui_test.emulate_mouse_move(points[0])
                await emulate_mouse_down()
                for point in points:
                    await ui_test.emulate_mouse_move(point)
                    await ui_test.human_delay()
            finally:
                await ui_test.human_delay()
                await emulate_mouse_up()
        await ui_test.human_delay()
        await self.finalize_test(golden_img_dir=self._golden_img_dir, golden_img_name="draw_tool_03.png")


class TestMarkupSelectTool(OmniUiTest):

    # Before running each test
    async def setUp(self):
        await super().setUp()
        self._setting = carb.settings.get_settings()
        self._golden_img_dir = TEST_DATA_PATH.absolute().joinpath("golden_img").absolute()
        self._visibility_value = self._setting.get(VISIBILITY_PATH)
        self._setting.set(VISIBILITY_PATH, 0)
        await omni.usd.get_context().new_stage_async()  # type: ignore
        await ui_test.human_delay()
        get_markup_instance().create_markup()  # type: ignore
        await ui_test.human_delay()
        await self._dock_viewport(width=1280, height=720)
        self._setting.set_string(MARKUP_TOOL_CURRENT, "select")

    async def _wait_for_viewport(self):
        await next_viewport_frame_async(get_active_viewport())
        for _ in range(3):
            await omni.kit.app.get_app().next_update_async()

    async def _dock_viewport(self, width=1200, height=900, block_device=True):
        """Utility function to dock viewport window and focus on turntable panel."""
        for window in ui.Workspace.get_windows():
            ui.Workspace.show_window(window.title, False)

        viewport = get_active_viewport_window()
        viewport.width = width  # type: ignore
        viewport.height = height  # type: ignore
        viewport.visible = True
        await self._wait_for_viewport()

    # After running each test
    async def tearDown(self):
        self._setting.set(VISIBILITY_PATH, self._visibility_value)
        await super().tearDown()
        self._setting.set_string(MARKUP_TOOL_CURRENT, "")
        self._setting.set_string(SETTINGS_MARKUP_EDITING, "")
        self._setting.set_string(SETTINGS_MARKUP_ACTIVE, "")

    async def test_select_tool_01(self):
        start = ui_test.Vec2(200, 200)
        await ui_test.emulate_mouse_move(start)
        await ui_test.emulate_mouse_click()
        await ui_test.human_delay()
        await self.finalize_test(golden_img_dir=self._golden_img_dir, golden_img_name="select_tool_01.png")


class TestMarkupAspectRatio(OmniUiTest):

    # Before running each test
    async def setUp(self):
        await super().setUp()
        self._setting = carb.settings.get_settings()
        self._golden_img_dir = TEST_DATA_PATH.absolute().joinpath("golden_img").absolute()
        self._visibility_value = self._setting.get(VISIBILITY_PATH)
        self._setting.set(VISIBILITY_PATH, 0)
        await omni.usd.get_context().new_stage_async()  # type: ignore
        await ui_test.human_delay()
        get_markup_instance().create_markup()  # type: ignore
        await ui_test.human_delay()
        await self._dock_viewport(width=1280, height=720)
        self._setting.set_string(MARKUP_TOOL_CURRENT, TOOL_NAME.SHAPES)

    async def _wait_for_viewport(self):
        await next_viewport_frame_async(get_active_viewport())
        for _ in range(3):
            await omni.kit.app.get_app().next_update_async()

    async def _dock_viewport(self, width=1200, height=900, block_device=True):
        """Utility function to dock viewport window and focus on turntable panel."""
        for window in ui.Workspace.get_windows():
            ui.Workspace.show_window(window.title, False)

        viewport = get_active_viewport_window()
        viewport.width = width  # type: ignore
        viewport.height = height  # type: ignore
        viewport.visible = True
        await self._wait_for_viewport()

    # After running each test
    async def tearDown(self):
        self._setting.set(VISIBILITY_PATH, self._visibility_value)
        await super().tearDown()
        self._setting.set_string(MARKUP_TOOL_CURRENT, "")
        self._setting.set_string(SETTINGS_MARKUP_EDITING, "")
        self._setting.set_string(SETTINGS_MARKUP_ACTIVE, "")

    async def __do_test(self, golden_img_name, width, height):
        p0 = ui_test.Vec2(1278, 718)
        p1 = ui_test.Vec2(1278, 718)
        p1.x = width if width is not None else p1.x
        p1.y = height if height is not None else p1.y
        await ui_test.emulate_mouse_move(p0)
        await ui_test.emulate_mouse_drag_and_drop(p0, p1)
        await self.finalize_test(golden_img_dir=self._golden_img_dir, golden_img_name=golden_img_name)
        await ui_test.emulate_mouse_move(p1)
        await ui_test.emulate_mouse_drag_and_drop(p1, p0)

    async def test_aspect_ratio(self):
        stage = omni.usd.get_context().get_stage()
        self.assertIsNotNone(stage)
        letterbox_color = self._setting.get(MARKUP_LETTERBOX_COLOR)
        self._setting.set(MARKUP_LETTERBOX_COLOR, 0xFF0000FF)
        size = 120
        p0 = ui_test.Vec2(580, 310)
        p1 = ui_test.Vec2(p0.x + size, p0.y + size)
        await ui_test.emulate_mouse_move(p0)
        await ui_test.emulate_mouse_drag_and_drop(p0, p1)
        await self.__do_test("aspect_ratio_01.png", None, None)
        await self.__do_test("aspect_ratio_02.png", None, 360)
        await self.__do_test("aspect_ratio_03.png", 720, None)
        await self.__do_test("aspect_ratio_04.png", 360, None)
        self._setting.set(MARKUP_LETTERBOX_COLOR, letterbox_color)


class TestMarkupEditTool(OmniUiTest):

    # Before running each test
    async def setUp(self):
        await super().setUp()
        self._setting = carb.settings.get_settings()
        self._golden_img_dir = TEST_DATA_PATH.absolute().joinpath("golden_img").absolute()
        self._visibility_value = self._setting.get(VISIBILITY_PATH)
        self._setting.set(VISIBILITY_PATH, 0)

    async def _wait_for_viewport(self):
        await next_viewport_frame_async(get_active_viewport())
        for _ in range(3):
            await omni.kit.app.get_app().next_update_async()

    async def _dock_viewport(self, width=1200, height=900, block_device=True):
        """Utility function to dock viewport window and focus on turntable panel."""
        for window in ui.Workspace.get_windows():
            ui.Workspace.show_window(window.title, False)

        viewport = get_active_viewport_window()
        viewport.width = width  # type: ignore
        viewport.height = height  # type: ignore
        viewport.visible = True
        await ui_test.wait_n_updates()
        await self._wait_for_viewport()

    # After running each test
    async def tearDown(self):
        self._setting.set(VISIBILITY_PATH, self._visibility_value)
        await super().tearDown()
        self._setting.set_string(MARKUP_TOOL_CURRENT, "")
        self._setting.set_string(SETTINGS_MARKUP_EDITING, "")
        self._setting.set_string(SETTINGS_MARKUP_ACTIVE, "")

    # OMFP-3425 Edit/Delete markups on a new edit layer
    async def test_create_edit_delete_markup_new_edit_layer(self):
        await omni.usd.get_context().new_stage_async()  # type: ignore
        await ui_test.human_delay()
        stage = omni.usd.get_context().get_stage()
        root_layer = stage.GetRootLayer()
        sublayer = Sdf.Layer.CreateAnonymous()
        root_layer.subLayerPaths.append(sublayer.identifier)
        with Usd.EditContext(stage, sublayer):
            get_markup_instance().create_markup()  # type: ignore
            await ui_test.human_delay()
            await self._dock_viewport(width=1280, height=720)
            # create new markup
            markup = get_markup_instance().get_markup("Markup_00")
            self.assertIsNotNone(markup)
            # rename markup
            get_markup_instance().rename_markup(markup, "New_Markup")
            self.assertTrue(markup.name == "New_Markup")
            await ui_test.human_delay()
            # delete markup
            get_markup_instance().delete_markup(markup)
            self.assertTrue(len(get_markup_instance().get_markups()) == 0)
        await omni.usd.get_context().new_stage_async()
        await ui_test.human_delay()

    # OMFP-3424 Unit Test: Create/Edit/Delete markups on a read-only usd stage
    async def test_create_edit_delete_markup_readonly_stage(self):
        await omni.usd.get_context().new_stage_async()  # type: ignore
        await ui_test.human_delay()
        # open read-only scene
        path = str(TEST_DATA_PATH.absolute().joinpath("scenes").absolute().joinpath("read-only.usda").absolute())
        stage = Usd.Stage.Open(path)
        await ui_test.human_delay()
        # layer = stage.GetSessionLayer()
        # with Usd.EditContext(stage, layer):
        get_markup_instance().create_markup()  # type: ignore
        await ui_test.human_delay()
        await self._dock_viewport(width=1280, height=720)
        # create new markup
        markup = get_markup_instance().get_markup("Markup_00")
        self.assertIsNotNone(markup)
        # rename markup
        get_markup_instance().rename_markup(markup, "New_Markup")
        self.assertTrue(markup.name == "New_Markup")
        await ui_test.human_delay()
        # delete markup
        get_markup_instance().delete_markup(markup)
        self.assertTrue(len(get_markup_instance().get_markups()) == 0)
        await omni.usd.get_context().new_stage_async()
        await ui_test.human_delay()

    # OMFP-3423 Rename/Delete Markups
    async def test_rename_delete_markup(self):
        await omni.usd.get_context().new_stage_async()  # type: ignore
        await ui_test.human_delay()
        get_markup_instance().create_markup()  # type: ignore
        await ui_test.human_delay()
        await self._dock_viewport(width=1280, height=720)
        # create new markup
        markup = get_markup_instance().get_markup("Markup_00")
        self.assertIsNotNone(markup)
        # rename markup
        get_markup_instance().rename_markup(markup, "New_Markup")
        self.assertTrue(markup.name == "New_Markup")
        await ui_test.human_delay()
        # delete markup
        get_markup_instance().delete_markup(markup)
        self.assertTrue(len(get_markup_instance().get_markups()) == 0)
        await omni.usd.get_context().new_stage_async()
        await ui_test.human_delay()

    # OMFP-3056 load a layer with Markups
    async def test_load_a_layer_with_markups(self):
        await omni.usd.get_context().new_stage_async()  # type: ignore
        await ui_test.human_delay()
        stage = omni.usd.get_context().get_stage()
        root_layer = stage.GetRootLayer()
        path = str(TEST_DATA_PATH.absolute().joinpath("scenes").absolute().joinpath("added_new_markup.usda").absolute())
        sublayer = Sdf.Layer.FindOrOpen(path)
        root_layer.subLayerPaths.append(sublayer.identifier)
        get_markup_instance()._refresh_markups()
        markup = get_markup_instance().get_markup("Test_Markup")
        self.assertIsNotNone(markup)
        await omni.usd.get_context().new_stage_async()
        await ui_test.human_delay()
