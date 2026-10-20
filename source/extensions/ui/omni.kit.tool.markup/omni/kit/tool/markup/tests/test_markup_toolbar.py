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
from omni.kit.markup.core import get_instance as get_markup_instance
from omni.kit.viewport.utility import get_active_viewport, get_active_viewport_window, next_viewport_frame_async
from omni.ui.tests.test_base import OmniUiTest

from ..ui.constant import CURRENT_TOOL_PATH, EXTENSION_NAME, MARKUP_BLOCK_GESTURES, TOOL_NAME
from ..ui.markup_scene import MARKUP_TOOL_CURRENT, SETTINGS_MARKUP_ACTIVE, SETTINGS_MARKUP_EDITING
from ..ui.markup_state import MarkupState, get_markup_state

CURRENT_PATH = Path(__file__).parent
TEST_DATA_PATH = CURRENT_PATH.parent.parent.parent.parent.parent.joinpath("data").joinpath("tests")
VISIBILITY_PATH = "/persistent/app/viewport/displayOptions"

from omni.ui_query.query import OmniUIQuery

from ..ui.constant import MARKUP_TOOL_HIDE


class TestMarkupToolBar(OmniUiTest):

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
        self._markup = list(get_markup_instance().get_markups())[0]
        await ui_test.human_delay()
        await self._dock_viewport(width=1280, height=720)
        self._setting.set_string(MARKUP_TOOL_CURRENT, "")

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

    async def test_toolbar_hide_tool(self):

        toolbar_frame = ui_test.find("Viewport//Frame/**/_markup_toolbar_frame_childframe")

        self._setting.set(MARKUP_TOOL_HIDE, True)
        await ui_test.human_delay(20)
        self.assertEqual(toolbar_frame.widget.visible, False)

        self._setting.set(MARKUP_TOOL_HIDE, False)
        await ui_test.human_delay(20)
        self.assertEqual(toolbar_frame.widget.visible, True)

    async def test_toolbar_apply_unlock_exit(self):

        await ui_test.human_delay(20)

        buttons = {
            w.widget.identifier: w
            for w in ui_test.find_all("Viewport//Frame/**")
            if "toolbar_btn" in w.widget.identifier
        }

        markup = list(get_markup_instance().get_markups())[0]
        self.assertEqual(get_markup_instance().current_markup, markup)
        self.assertEqual(get_markup_instance().editing_markup, markup)

        await buttons["toolbar_btn_markup_apply"].click()
        await next_viewport_frame_async(get_active_viewport())
        await ui_test.human_delay(20)
        self.assertEqual(get_markup_state(), MarkupState.DEACTIVATED)
        self._setting.set(CURRENT_TOOL_PATH, EXTENSION_NAME)
        self.assertEqual(get_markup_state(), MarkupState.READY)
        self.assertEqual(get_markup_instance().current_markup, None)
        self.assertEqual(get_markup_instance().editing_markup, None)

        get_markup_instance().open_markup(markup.name)
        await next_viewport_frame_async(get_active_viewport())
        await ui_test.human_delay(20)
        self.assertEqual(get_markup_state(), MarkupState.READY)
        self.assertEqual(get_markup_instance().current_markup, markup)
        self.assertEqual(get_markup_instance().editing_markup, None)

        await buttons["toolbar_btn_markup_unlock"].click()
        await next_viewport_frame_async(get_active_viewport())
        await ui_test.human_delay(20)
        self.assertEqual(get_markup_state(), MarkupState.READY)
        self.assertEqual(get_markup_instance().current_markup, markup)
        self.assertEqual(get_markup_instance().editing_markup, markup)

        await buttons["toolbar_btn_markup_cancel"].click()
        await next_viewport_frame_async(get_active_viewport())
        await ui_test.human_delay(20)
        self.assertEqual(get_markup_state(), MarkupState.DEACTIVATED)
        self.assertEqual(get_markup_instance().current_markup, None)
        self.assertEqual(get_markup_instance().editing_markup, None)

        get_markup_instance().open_markup(markup.name)
        await next_viewport_frame_async(get_active_viewport())
        await ui_test.human_delay(40)
        self.assertEqual(get_markup_state(), MarkupState.READY)

        await buttons["toolbar_btn_markup_exit"].click()
        await next_viewport_frame_async(get_active_viewport())
        await ui_test.human_delay(20)
        self.assertEqual(get_markup_state(), MarkupState.DEACTIVATED)

    async def test_toolbar_edit_rect(self):

        # click on the shapes button:
        buttons = {
            w.widget.identifier: w
            for w in ui_test.find_all("Viewport//Frame/**")
            if "toolbar_btn" in w.widget.identifier
        }

        await buttons["toolbar_btn_shapes"].click()
        await ui_test.human_delay(20)
        self.assertEqual(get_markup_state(), MarkupState.READY)
        self.assertEqual(self._setting.get_as_string(MARKUP_TOOL_CURRENT), TOOL_NAME.SHAPES)

        # draw a rectangle and select it:
        start = ui_test.Vec2(200, 200)
        end = ui_test.Vec2(400, 500)

        await ui_test.emulate_mouse_move(start)
        await ui_test.input.emulate_mouse(MouseEventType.LEFT_BUTTON_DOWN)
        await ui_test.human_delay(4)
        self.assertEqual(get_markup_state(), MarkupState.SHAPE)
        await ui_test.input.emulate_mouse_slow_move(start, end, human_delay_speed=4)
        await ui_test.human_delay(4)
        self.assertEqual(get_markup_state(), MarkupState.SHAPE)
        await ui_test.input.emulate_mouse(MouseEventType.LEFT_BUTTON_UP)
        await ui_test.human_delay(4)
        self.assertEqual(get_markup_state(), MarkupState.READY)

        # clicking on the element should select it and set the state to EDIT:
        await ui_test.emulate_mouse_move_and_click(ui_test.Vec2(201, 201))
        await ui_test.human_delay(40)
        self.assertEqual(get_markup_state(), MarkupState.EDIT)

        # check we created our element:
        inst = get_markup_instance()
        self.assertEqual(len(inst.get_markup_elements()), 1)
        elem = inst.get_markup_elements()[0]
        self.assertEqual(inst.get_element_attr(elem.GetName(), "type", ""), "Shape")
        self.assertEqual(inst.get_element_attr(elem.GetName(), "shape_type", ""), "Rectangle")

        # tweak the transform via the placers:
        placers = {
            w.widget.identifier: w
            for w in ui_test.find_all("Viewport//Frame/**")
            if "transform_placer_" in w.widget.identifier
        }
        control_stack = ui_test.find("Viewport//Frame/**/transform_control_stack")

        await ui_test.human_delay(20)

        prev_rect = inst.get_element_attr(elem.GetName(), "rect", "")
        for pl in placers.values():
            x = (
                pl.widget.offset_x.value * control_stack.widget.computed_width / 100.0
                + control_stack.widget.screen_position_x
            )
            y = (
                pl.widget.offset_y.value * control_stack.widget.computed_height / 100.0
                + control_stack.widget.screen_position_y
            )
            x += pl.widget.width / 2.0
            y += pl.widget.height / 2.0

            start = ui_test.Vec2(x, y)
            end = start + ui_test.Vec2(20, 20)
            await ui_test.emulate_mouse_move(start)
            await ui_test.input.emulate_mouse(MouseEventType.LEFT_BUTTON_DOWN)
            await ui_test.human_delay(4)
            self.assertEqual(get_markup_state(), MarkupState.EDIT)
            await ui_test.input.emulate_mouse_slow_move(start, end, human_delay_speed=4)
            await ui_test.human_delay(4)
            self.assertEqual(get_markup_state(), MarkupState.EDIT)
            await ui_test.input.emulate_mouse(MouseEventType.LEFT_BUTTON_UP)
            await ui_test.human_delay(4)
            self.assertEqual(get_markup_state(), MarkupState.EDIT)
            await ui_test.human_delay()
            rect = inst.get_element_attr(elem.GetName(), "rect", "")
            self.assertNotEqual(rect, prev_rect)
            prev_rect = rect

        transform_drag_box = ui_test.find("Viewport//Frame/**/transform_drag_box")
        start = transform_drag_box.position
        end = start + ui_test.Vec2(20, 20)
        await ui_test.emulate_mouse_move(start)
        await ui_test.input.emulate_mouse(MouseEventType.LEFT_BUTTON_DOWN)
        await ui_test.human_delay(4)
        self.assertEqual(get_markup_state(), MarkupState.EDIT)
        await ui_test.input.emulate_mouse_slow_move(start, end, human_delay_speed=4)
        await ui_test.human_delay(4)
        self.assertEqual(get_markup_state(), MarkupState.EDIT)
        await ui_test.input.emulate_mouse(MouseEventType.LEFT_BUTTON_UP)
        await ui_test.human_delay(4)
        self.assertEqual(get_markup_state(), MarkupState.EDIT)
        await ui_test.human_delay(20)
        rect = inst.get_element_attr(elem.GetName(), "rect", "")
        self.assertNotEqual(rect, prev_rect)

        # Switching tools clears the selection, which takes the element's transform controls down with
        # it. The handle positions then belong to the newly active drawing tool, rather than staying
        # behind as dead input that neither draws nor resizes.
        placer = next(iter(placers.values()))
        x = (
            placer.widget.offset_x.value * control_stack.widget.computed_width / 100.0
            + control_stack.widget.screen_position_x
            + placer.widget.width / 2.0
        )
        y = (
            placer.widget.offset_y.value * control_stack.widget.computed_height / 100.0
            + control_stack.widget.screen_position_y
            + placer.widget.height / 2.0
        )

        await buttons["toolbar_btn_draw"].click()
        await ui_test.human_delay(20)
        self.assertEqual(get_markup_state(), MarkupState.READY)
        self.assertEqual(self._setting.get_as_string(MARKUP_TOOL_CURRENT), TOOL_NAME.DRAW)

        start = ui_test.Vec2(x, y)
        end = start + ui_test.Vec2(60, 60)
        await ui_test.emulate_mouse_move(start)
        await ui_test.human_delay(4)

        # Hovering where a transform handle used to sit no longer blocks anything: switching tools
        # dropped the selection, so the controls came down and released their gesture blocks.
        self.assertEqual(self._setting.get_as_int(MARKUP_BLOCK_GESTURES), 0)

        await ui_test.input.emulate_mouse(MouseEventType.LEFT_BUTTON_DOWN)
        try:
            await ui_test.input.emulate_mouse_slow_move(start, end, human_delay_speed=4)

            self.assertEqual(self._setting.get_as_int(MARKUP_BLOCK_GESTURES), 0)
            self.assertEqual(get_markup_state(), MarkupState.DRAW)
        finally:
            await ui_test.input.emulate_mouse(MouseEventType.LEFT_BUTTON_UP)

        await ui_test.human_delay(20)
        self.assertEqual(get_markup_state(), MarkupState.READY)
        self.assertEqual(len(inst.get_markup_elements()), 2)

    async def test_toolbar_shapes(self):

        # click on the shapes button:
        buttons = {
            w.widget.identifier: w
            for w in ui_test.find_all("Viewport//Frame/**")
            if "toolbar_btn" in w.widget.identifier
        }

        await buttons["toolbar_btn_shapes"].click()
        await ui_test.human_delay(20)
        self.assertEqual(get_markup_state(), MarkupState.READY)
        self.assertEqual(self._setting.get_as_string(MARKUP_TOOL_CURRENT), TOOL_NAME.SHAPES)

        # draw a rectangle and select it:
        start = ui_test.Vec2(750, 200)
        end = ui_test.Vec2(850, 500)

        await ui_test.emulate_mouse_move(start)
        await ui_test.input.emulate_mouse(MouseEventType.LEFT_BUTTON_DOWN)
        await ui_test.human_delay(4)
        self.assertEqual(get_markup_state(), MarkupState.SHAPE)
        await ui_test.input.emulate_mouse_slow_move(start, end, human_delay_speed=4)
        await ui_test.human_delay(4)
        self.assertEqual(get_markup_state(), MarkupState.SHAPE)
        await ui_test.input.emulate_mouse(MouseEventType.LEFT_BUTTON_UP)
        await ui_test.human_delay(4)
        self.assertEqual(get_markup_state(), MarkupState.READY)

        # clicking on the element should select it and set the state to EDIT:
        await ui_test.emulate_mouse_move_and_click(ui_test.Vec2(751, 201))
        await ui_test.human_delay(40)
        self.assertEqual(get_markup_state(), MarkupState.EDIT)

        # clicking off the element should dselect and set the state to READY:
        await ui_test.emulate_mouse_move_and_click(ui_test.Vec2(101, 101))
        await ui_test.human_delay(40)
        self.assertEqual(get_markup_state(), MarkupState.READY)

        await ui_test.emulate_mouse_move_and_click(ui_test.Vec2(751, 201))
        await ui_test.human_delay(40)

        # check we created our element:
        inst = get_markup_instance()
        self.assertEqual(len(inst.get_markup_elements()), 1)
        elem = inst.get_markup_elements()[0]
        self.assertEqual(inst.get_element_attr(elem.GetName(), "type", ""), "Shape")
        self.assertEqual(inst.get_element_attr(elem.GetName(), "shape_type", ""), "Rectangle")

        buttons = {
            w.widget.identifier: w
            for w in ui_test.find_all("Viewport//Frame/**")
            if "elementbar_btn_" in w.widget.identifier
        }

        # change the shape type:
        await buttons["elementbar_btn_rectangle"].click()
        await ui_test.human_delay(20)
        # should end up in edit mode, otherwise we can't interact with the shape anymore:
        self.assertEqual(get_markup_state(), MarkupState.EDIT)
        self.assertEqual(inst.get_element_attr(elem.GetName(), "shape_type", ""), "Rectangle")

        await buttons["elementbar_btn_circle"].click()
        await ui_test.human_delay(20)
        self.assertEqual(get_markup_state(), MarkupState.EDIT)
        self.assertEqual(inst.get_element_attr(elem.GetName(), "shape_type", ""), "Circle")

        # change the stroke width:
        borderWidths = []
        await buttons["elementbar_btn_stroke_s"].click()
        await ui_test.human_delay(20)
        self.assertEqual(get_markup_state(), MarkupState.EDIT)
        style = eval(inst.get_element_attr(elem.GetName(), "style", "{}"))
        borderWidths.append(list(style.values())[0]["border_width"])

        await buttons["elementbar_btn_stroke_m"].click()
        await ui_test.human_delay(20)
        self.assertEqual(get_markup_state(), MarkupState.EDIT)
        style = eval(inst.get_element_attr(elem.GetName(), "style", "{}"))
        borderWidths.append(list(style.values())[0]["border_width"])

        await buttons["elementbar_btn_stroke_l"].click()
        await ui_test.human_delay(20)
        self.assertEqual(get_markup_state(), MarkupState.EDIT)
        style = eval(inst.get_element_attr(elem.GetName(), "style", "{}"))
        borderWidths.append(list(style.values())[0]["border_width"])

        await buttons["elementbar_btn_stroke_xl"].click()
        await ui_test.human_delay(20)
        self.assertEqual(get_markup_state(), MarkupState.EDIT)
        style = eval(inst.get_element_attr(elem.GetName(), "style", "{}"))
        borderWidths.append(list(style.values())[0]["border_width"])

        # unique border widths:
        self.assertEqual(len(set(borderWidths)), len(borderWidths))

        # ...in order of increasing size:
        self.assertEqual(sorted(borderWidths), borderWidths)

        # pick a new color:
        await buttons["elementbar_btn_color"].click()
        await ui_test.human_delay(20)
        colorclickpos = buttons["elementbar_btn_color"].position + ui_test.Vec2(70, 70)
        await ui_test.emulate_mouse_move_and_click(colorclickpos)
        await ui_test.human_delay(20)
        self.assertEqual(get_markup_state(), MarkupState.COLOR_PICKER)

        # have to click off the widget for the prim to be updated:
        await ui_test.emulate_mouse_move_and_click(buttons["elementbar_btn_color"].position + ui_test.Vec2(0, -30))
        await ui_test.human_delay(20)

        old_color = list(style.values())[0]["border_color"]
        style = eval(inst.get_element_attr(elem.GetName(), "style", "{}"))
        self.assertTrue(all(v["border_color"] != old_color for v in style.values()))

        # click off the element:
        await ui_test.emulate_mouse_move_and_click(ui_test.Vec2(100, 100))
        await ui_test.human_delay(20)

        # click back on again
        await ui_test.emulate_mouse_move_and_click(ui_test.Vec2(850, 200))
        await ui_test.human_delay(20)

        # remove the element:
        await buttons["elementbar_btn_remove"].click()
        await ui_test.human_delay(20)
        self.assertEqual(get_markup_state(), MarkupState.READY)
        self.assertEqual(len(inst.get_markup_elements()), 0)

    async def test_toolbar_arrow1(self):

        # click on the arrow button:
        buttons = {
            w.widget.identifier: w
            for w in ui_test.find_all("Viewport//Frame/**")
            if "toolbar_btn" in w.widget.identifier
        }

        await buttons["toolbar_btn_arrow"].click()
        await ui_test.human_delay(20)
        self.assertEqual(get_markup_state(), MarkupState.READY)
        self.assertEqual(self._setting.get_as_string(MARKUP_TOOL_CURRENT), TOOL_NAME.ARROW)

        # draw an arrow and select it:
        await ui_test.human_delay(20)
        await ui_test.human_delay(20)
        start = ui_test.Vec2(400, 200)
        end = ui_test.Vec2(600, 500)
        await ui_test.emulate_mouse_move(start)
        await ui_test.emulate_mouse_drag_and_drop(start, end)
        await ui_test.human_delay()

        # Should be in READY mode so we can select stuff etc:
        self.assertEqual(get_markup_state(), MarkupState.READY)

        await ui_test.emulate_mouse_move_and_click(ui_test.Vec2(401, 201))
        await ui_test.human_delay(40)

        # Should be in EDIT mode:
        self.assertEqual(get_markup_state(), MarkupState.EDIT)
        buttons = {
            w.widget.identifier: w
            for w in ui_test.find_all("Viewport//Frame/**")
            if "elementbar_btn_" in w.widget.identifier
        }

        inst = get_markup_instance()
        elem = inst.get_markup_elements()[0]
        self.assertEqual(inst.get_element_attr(elem.GetName(), "type", ""), "Arrow")

        await buttons["elementbar_btn_arrow_start"].click()
        await ui_test.human_delay(20)
        self.assertEqual(get_markup_state(), MarkupState.EDIT)

        await buttons["elementbar_btn_arrow_end"].click()
        await ui_test.human_delay(20)
        self.assertEqual(get_markup_state(), MarkupState.EDIT)
        style = eval(inst.get_element_attr(elem.GetName(), "style", "{}"))
        self.assertEqual(style["ArrowDirection"], 1)

        await buttons["elementbar_btn_arrow_double"].click()
        await ui_test.human_delay(20)
        self.assertEqual(get_markup_state(), MarkupState.EDIT)
        style = eval(inst.get_element_attr(elem.GetName(), "style", "{}"))
        self.assertEqual(style["ArrowDirection"], 2)

        borderWidths = []
        await buttons["elementbar_btn_stroke_s"].click()
        await ui_test.human_delay(20)
        self.assertEqual(get_markup_state(), MarkupState.EDIT)
        style = eval(inst.get_element_attr(elem.GetName(), "style", "{}"))
        borderWidths.append(list(style.values())[0]["border_width"])

        await buttons["elementbar_btn_stroke_m"].click()
        await ui_test.human_delay(20)
        self.assertEqual(get_markup_state(), MarkupState.EDIT)
        style = eval(inst.get_element_attr(elem.GetName(), "style", "{}"))
        borderWidths.append(list(style.values())[0]["border_width"])

        await buttons["elementbar_btn_stroke_l"].click()
        await ui_test.human_delay(20)
        self.assertEqual(get_markup_state(), MarkupState.EDIT)
        style = eval(inst.get_element_attr(elem.GetName(), "style", "{}"))
        borderWidths.append(list(style.values())[0]["border_width"])

        await buttons["elementbar_btn_stroke_xl"].click()
        await ui_test.human_delay(20)
        self.assertEqual(get_markup_state(), MarkupState.EDIT)
        style = eval(inst.get_element_attr(elem.GetName(), "style", "{}"))
        borderWidths.append(list(style.values())[0]["border_width"])

        # unique border widths:
        self.assertEqual(len(set(borderWidths)), len(borderWidths))

        # ...in order of increasing size:
        self.assertEqual(sorted(borderWidths), borderWidths)

        await buttons["elementbar_btn_color"].click()
        await ui_test.human_delay(20)
        self.assertEqual(get_markup_state(), MarkupState.COLOR_PICKER)
        await ui_test.emulate_mouse_move_and_click(buttons["elementbar_btn_color"].position + ui_test.Vec2(40, 0))
        await ui_test.human_delay(20)
        self.assertEqual(get_markup_state(), MarkupState.COLOR_PICKER)

        # have to click off the widget for the prim to be updated:
        await ui_test.emulate_mouse_move_and_click(buttons["elementbar_btn_color"].position + ui_test.Vec2(0, -30))
        await ui_test.human_delay(20)

        old_color = list(style.values())[0]["color"]
        style = eval(inst.get_element_attr(elem.GetName(), "style", "{}"))
        self.assertNotEqual(list(style.values())[0]["color"], old_color)

        # click back on and select:
        await ui_test.emulate_mouse_move_and_click(ui_test.Vec2(400, 200))
        await ui_test.human_delay(20)

        # remove the element:
        elementbar_buttons = {
            w.widget.identifier: w
            for w in ui_test.find_all("Viewport//Frame/**")
            if "elementbar_btn_" in w.widget.identifier
        }
        await elementbar_buttons["elementbar_btn_remove"].click()
        await ui_test.human_delay(20)
        self.assertEqual(get_markup_state(), MarkupState.READY)
        self.assertEqual(len(inst.get_markup_elements()), 0)

    async def test_toolbar_arrow2(self):
        tool_buttons = {
            w.widget.identifier: w
            for w in ui_test.find_all("Viewport//Frame/**")
            if "toolbar_btn" in w.widget.identifier
        }

        # click on the arrow button:
        await tool_buttons["toolbar_btn_arrow"].click()
        await ui_test.human_delay(20)

        buttons = {
            w.widget.identifier: w
            for w in ui_test.find_all("Viewport//Frame/**")
            if "elementtool_btn_" in w.widget.identifier
        }
        await buttons["elementtool_btn_arrow_start"].click()
        await ui_test.human_delay(20)

        # draw an arrow and select it:
        await ui_test.human_delay(20)
        await ui_test.human_delay(20)
        start = ui_test.Vec2(400, 200)
        end = ui_test.Vec2(600, 500)
        await ui_test.emulate_mouse_move(start)
        await ui_test.emulate_mouse_drag_and_drop(start, end)
        await ui_test.human_delay()

        # Should be in READY mode so we can select stuff etc:
        self.assertEqual(get_markup_state(), MarkupState.READY)

        await ui_test.emulate_mouse_move_and_click(ui_test.Vec2(401, 201))
        await ui_test.human_delay(40)

        # Should be in EDIT mode:
        self.assertEqual(get_markup_state(), MarkupState.EDIT)
        buttons = {
            w.widget.identifier: w
            for w in ui_test.find_all("Viewport//Frame/**")
            if "elementbar_btn_" in w.widget.identifier
        }

        inst = get_markup_instance()
        elem = inst.get_markup_elements()[0]
        self.assertEqual(inst.get_element_attr(elem.GetName(), "type", ""), "Arrow")

        await buttons["elementbar_btn_arrow_start"].click()
        await ui_test.human_delay(20)
        self.assertEqual(get_markup_state(), MarkupState.EDIT)

        await buttons["elementbar_btn_arrow_end"].click()
        await ui_test.human_delay(20)
        self.assertEqual(get_markup_state(), MarkupState.EDIT)
        style = eval(inst.get_element_attr(elem.GetName(), "style", "{}"))
        self.assertEqual(style["ArrowDirection"], 1)

        await buttons["elementbar_btn_arrow_double"].click()
        await ui_test.human_delay(20)
        self.assertEqual(get_markup_state(), MarkupState.EDIT)
        style = eval(inst.get_element_attr(elem.GetName(), "style", "{}"))
        self.assertEqual(style["ArrowDirection"], 2)

        borderWidths = []
        await buttons["elementbar_btn_stroke_s"].click()
        await ui_test.human_delay(20)
        self.assertEqual(get_markup_state(), MarkupState.EDIT)
        style = eval(inst.get_element_attr(elem.GetName(), "style", "{}"))
        borderWidths.append(list(style.values())[0]["border_width"])

        await buttons["elementbar_btn_stroke_m"].click()
        await ui_test.human_delay(20)
        self.assertEqual(get_markup_state(), MarkupState.EDIT)
        style = eval(inst.get_element_attr(elem.GetName(), "style", "{}"))
        borderWidths.append(list(style.values())[0]["border_width"])

        await buttons["elementbar_btn_stroke_l"].click()
        await ui_test.human_delay(20)
        self.assertEqual(get_markup_state(), MarkupState.EDIT)
        style = eval(inst.get_element_attr(elem.GetName(), "style", "{}"))
        borderWidths.append(list(style.values())[0]["border_width"])

        await buttons["elementbar_btn_stroke_xl"].click()
        await ui_test.human_delay(20)
        self.assertEqual(get_markup_state(), MarkupState.EDIT)
        style = eval(inst.get_element_attr(elem.GetName(), "style", "{}"))
        borderWidths.append(list(style.values())[0]["border_width"])

        # unique border widths:
        self.assertEqual(len(set(borderWidths)), len(borderWidths))

        # ...in order of increasing size:
        self.assertEqual(sorted(borderWidths), borderWidths)

        await buttons["elementbar_btn_color"].click()
        await ui_test.human_delay(20)
        self.assertEqual(get_markup_state(), MarkupState.COLOR_PICKER)
        await ui_test.emulate_mouse_move_and_click(buttons["elementbar_btn_color"].position + ui_test.Vec2(40, 0))
        await ui_test.human_delay(20)
        self.assertEqual(get_markup_state(), MarkupState.COLOR_PICKER)

        # have to click off the widget for the prim to be updated:
        await ui_test.emulate_mouse_move_and_click(buttons["elementbar_btn_color"].position + ui_test.Vec2(0, -30))
        await ui_test.human_delay(20)

        old_color = list(style.values())[0]["color"]
        style = eval(inst.get_element_attr(elem.GetName(), "style", "{}"))
        self.assertNotEqual(list(style.values())[0]["color"], old_color)

        # click back on and select:
        await ui_test.emulate_mouse_move_and_click(ui_test.Vec2(400, 200))
        await ui_test.human_delay(20)

        # remove the element:
        elementbar_buttons = {
            w.widget.identifier: w
            for w in ui_test.find_all("Viewport//Frame/**")
            if "elementbar_btn_" in w.widget.identifier
        }
        await elementbar_buttons["elementbar_btn_remove"].click()
        await ui_test.human_delay(20)
        self.assertEqual(get_markup_state(), MarkupState.READY)
        self.assertEqual(len(inst.get_markup_elements()), 0)

    async def test_toolbar_arrow3(self):
        tool_buttons = {
            w.widget.identifier: w
            for w in ui_test.find_all("Viewport//Frame/**")
            if "toolbar_btn" in w.widget.identifier
        }

        # click on the arrow button:
        await tool_buttons["toolbar_btn_arrow"].click()
        await ui_test.human_delay(20)

        buttons = {
            w.widget.identifier: w
            for w in ui_test.find_all("Viewport//Frame/**")
            if "elementtool_btn_" in w.widget.identifier
        }
        await buttons["elementtool_btn_arrow_end"].click()
        await ui_test.human_delay(20)

        # draw an arrow and select it:
        await ui_test.human_delay(20)
        await ui_test.human_delay(20)
        start = ui_test.Vec2(400, 200)
        end = ui_test.Vec2(600, 500)
        await ui_test.emulate_mouse_move(start)
        await ui_test.emulate_mouse_drag_and_drop(start, end)
        await ui_test.human_delay()

        # Should be in READY mode so we can select stuff etc:
        self.assertEqual(get_markup_state(), MarkupState.READY)

        await ui_test.emulate_mouse_move_and_click(ui_test.Vec2(401, 201))
        await ui_test.human_delay(40)

        # Should be in EDIT mode:
        self.assertEqual(get_markup_state(), MarkupState.EDIT)
        buttons = {
            w.widget.identifier: w
            for w in ui_test.find_all("Viewport//Frame/**")
            if "elementbar_btn_" in w.widget.identifier
        }

        inst = get_markup_instance()
        elem = inst.get_markup_elements()[0]
        self.assertEqual(inst.get_element_attr(elem.GetName(), "type", ""), "Arrow")

        await buttons["elementbar_btn_arrow_start"].click()
        await ui_test.human_delay(20)
        self.assertEqual(get_markup_state(), MarkupState.EDIT)

        await buttons["elementbar_btn_arrow_end"].click()
        await ui_test.human_delay(20)
        self.assertEqual(get_markup_state(), MarkupState.EDIT)
        style = eval(inst.get_element_attr(elem.GetName(), "style", "{}"))
        self.assertEqual(style["ArrowDirection"], 1)

        await buttons["elementbar_btn_arrow_double"].click()
        await ui_test.human_delay(20)
        self.assertEqual(get_markup_state(), MarkupState.EDIT)
        style = eval(inst.get_element_attr(elem.GetName(), "style", "{}"))
        self.assertEqual(style["ArrowDirection"], 2)

        borderWidths = []
        await buttons["elementbar_btn_stroke_s"].click()
        await ui_test.human_delay(20)
        self.assertEqual(get_markup_state(), MarkupState.EDIT)
        style = eval(inst.get_element_attr(elem.GetName(), "style", "{}"))
        borderWidths.append(list(style.values())[0]["border_width"])

        await buttons["elementbar_btn_stroke_m"].click()
        await ui_test.human_delay(20)
        self.assertEqual(get_markup_state(), MarkupState.EDIT)
        style = eval(inst.get_element_attr(elem.GetName(), "style", "{}"))
        borderWidths.append(list(style.values())[0]["border_width"])

        await buttons["elementbar_btn_stroke_l"].click()
        await ui_test.human_delay(20)
        self.assertEqual(get_markup_state(), MarkupState.EDIT)
        style = eval(inst.get_element_attr(elem.GetName(), "style", "{}"))
        borderWidths.append(list(style.values())[0]["border_width"])

        await buttons["elementbar_btn_stroke_xl"].click()
        await ui_test.human_delay(20)
        self.assertEqual(get_markup_state(), MarkupState.EDIT)
        style = eval(inst.get_element_attr(elem.GetName(), "style", "{}"))
        borderWidths.append(list(style.values())[0]["border_width"])

        # unique border widths:
        self.assertEqual(len(set(borderWidths)), len(borderWidths))

        # ...in order of increasing size:
        self.assertEqual(sorted(borderWidths), borderWidths)

        await buttons["elementbar_btn_color"].click()
        await ui_test.human_delay(20)
        self.assertEqual(get_markup_state(), MarkupState.COLOR_PICKER)
        await ui_test.emulate_mouse_move_and_click(buttons["elementbar_btn_color"].position + ui_test.Vec2(40, 0))
        await ui_test.human_delay(20)
        self.assertEqual(get_markup_state(), MarkupState.COLOR_PICKER)

        # have to click off the widget for the prim to be updated:
        await ui_test.emulate_mouse_move_and_click(buttons["elementbar_btn_color"].position + ui_test.Vec2(0, -30))
        await ui_test.human_delay(20)

        old_color = list(style.values())[0]["color"]
        style = eval(inst.get_element_attr(elem.GetName(), "style", "{}"))
        self.assertNotEqual(list(style.values())[0]["color"], old_color)

        # click back on and select:
        await ui_test.emulate_mouse_move_and_click(ui_test.Vec2(400, 200))
        await ui_test.human_delay(20)

        # remove the element:
        elementbar_buttons = {
            w.widget.identifier: w
            for w in ui_test.find_all("Viewport//Frame/**")
            if "elementbar_btn_" in w.widget.identifier
        }
        await elementbar_buttons["elementbar_btn_remove"].click()
        await ui_test.human_delay(20)
        self.assertEqual(get_markup_state(), MarkupState.READY)
        self.assertEqual(len(inst.get_markup_elements()), 0)

    async def test_toolbar_line(self):

        # click on the line button:
        buttons = {
            w.widget.identifier: w
            for w in ui_test.find_all("Viewport//Frame/**")
            if "toolbar_btn" in w.widget.identifier
        }

        await buttons["toolbar_btn_line"].click()
        await ui_test.human_delay(20)
        self.assertEqual(get_markup_state(), MarkupState.READY)
        self.assertEqual(self._setting.get_as_string(MARKUP_TOOL_CURRENT), TOOL_NAME.LINE)

        # draw a line and select it:
        await ui_test.human_delay(20)
        start = ui_test.Vec2(400, 200)
        end = ui_test.Vec2(600, 500)
        await ui_test.emulate_mouse_move(start)
        await ui_test.emulate_mouse_drag_and_drop(start, end)
        await ui_test.human_delay()

        # Should be in READY mode so we can select stuff etc:
        self.assertEqual(get_markup_state(), MarkupState.READY)

        # click off...
        await ui_test.emulate_mouse_move_and_click(ui_test.Vec2(101, 201))
        await ui_test.human_delay(40)

        await ui_test.emulate_mouse_move_and_click(ui_test.Vec2(401, 201))
        await ui_test.human_delay(40)

        # Should be in EDIT mode:
        self.assertEqual(get_markup_state(), MarkupState.EDIT)
        buttons = {
            w.widget.identifier: w
            for w in ui_test.find_all("Viewport//Frame/**")
            if "elementbar_btn_" in w.widget.identifier
        }

        inst = get_markup_instance()
        elem = inst.get_markup_elements()[0]
        self.assertEqual(inst.get_element_attr(elem.GetName(), "type", ""), "LineSegment")

        borderWidths = []
        await buttons["elementbar_btn_stroke_s"].click()
        await ui_test.human_delay(20)
        self.assertEqual(get_markup_state(), MarkupState.EDIT)
        style = eval(inst.get_element_attr(elem.GetName(), "style", "{}"))
        borderWidths.append(list(style.values())[0]["border_width"])

        await buttons["elementbar_btn_stroke_m"].click()
        await ui_test.human_delay(20)
        self.assertEqual(get_markup_state(), MarkupState.EDIT)
        style = eval(inst.get_element_attr(elem.GetName(), "style", "{}"))
        borderWidths.append(list(style.values())[0]["border_width"])

        await buttons["elementbar_btn_stroke_l"].click()
        await ui_test.human_delay(20)
        self.assertEqual(get_markup_state(), MarkupState.EDIT)
        style = eval(inst.get_element_attr(elem.GetName(), "style", "{}"))
        borderWidths.append(list(style.values())[0]["border_width"])

        await buttons["elementbar_btn_stroke_xl"].click()
        await ui_test.human_delay(20)
        self.assertEqual(get_markup_state(), MarkupState.EDIT)
        style = eval(inst.get_element_attr(elem.GetName(), "style", "{}"))
        borderWidths.append(list(style.values())[0]["border_width"])

        # unique border widths:
        self.assertEqual(len(set(borderWidths)), len(borderWidths))

        # ...in order of increasing size:
        self.assertEqual(sorted(borderWidths), borderWidths)

        await buttons["elementbar_btn_color"].click()
        await ui_test.human_delay(20)
        self.assertEqual(get_markup_state(), MarkupState.COLOR_PICKER)
        await ui_test.emulate_mouse_move_and_click(buttons["elementbar_btn_color"].position + ui_test.Vec2(40, 0))
        await ui_test.human_delay(20)
        self.assertEqual(get_markup_state(), MarkupState.COLOR_PICKER)

        # have to click off the widget for the prim to be updated:
        await ui_test.emulate_mouse_move_and_click(buttons["elementbar_btn_color"].position + ui_test.Vec2(0, -30))
        await ui_test.human_delay(20)

        old_color = list(style.values())[0]["color"]
        style = eval(inst.get_element_attr(elem.GetName(), "style", "{}"))
        self.assertNotEqual(list(style.values())[0]["color"], old_color)

        # click back on and select:
        await ui_test.emulate_mouse_move_and_click(ui_test.Vec2(400, 200))
        await ui_test.human_delay(20)

        # remove the element:
        await buttons["elementbar_btn_remove"].click()
        await ui_test.human_delay(20)
        self.assertEqual(get_markup_state(), MarkupState.READY)
        self.assertEqual(len(inst.get_markup_elements()), 0)

    async def test_toolbar_draw(self):

        # click on the line button:
        buttons = {
            w.widget.identifier: w
            for w in ui_test.find_all("Viewport//Frame/**")
            if "toolbar_btn" in w.widget.identifier
        }

        await buttons["toolbar_btn_draw"].click()
        await ui_test.human_delay(20)
        self.assertEqual(get_markup_state(), MarkupState.READY)
        self.assertEqual(self._setting.get_as_string(MARKUP_TOOL_CURRENT), TOOL_NAME.DRAW)

        inst = get_markup_instance()

        # draw a line that's too small:
        start = ui_test.Vec2(205, 205)
        end = ui_test.Vec2(206, 206)
        await ui_test.emulate_mouse_move(start)
        await ui_test.input.emulate_mouse(MouseEventType.LEFT_BUTTON_DOWN)
        await ui_test.human_delay()
        await ui_test.emulate_mouse_move(end)

        await ui_test.human_delay()
        await ui_test.input.emulate_mouse(MouseEventType.LEFT_BUTTON_UP)
        await ui_test.human_delay()
        await ui_test.human_delay()

        self.assertEqual(len(inst.get_markup_elements()), 0)

        # draw a line and select it:
        start = ui_test.Vec2(200, 200)
        await ui_test.emulate_mouse_move(start)
        points = [
            ui_test.Vec2(205, 205),
            ui_test.Vec2(210, 215),
            ui_test.Vec2(220, 225),
            ui_test.Vec2(300, 150),
        ]
        await ui_test.input.emulate_mouse(MouseEventType.LEFT_BUTTON_DOWN)
        await ui_test.human_delay()
        for point in points:
            await ui_test.emulate_mouse_move(point)
            await ui_test.human_delay()
        await ui_test.human_delay()
        await ui_test.input.emulate_mouse(MouseEventType.LEFT_BUTTON_UP)
        await ui_test.human_delay()
        await ui_test.human_delay()

        # Should be in READY mode so we can select stuff etc:
        self.assertEqual(get_markup_state(), MarkupState.READY)

        # click off it:
        await ui_test.emulate_mouse_move_and_click(ui_test.Vec2(100, 100))
        await ui_test.human_delay(40)

        # click on it:
        await ui_test.emulate_mouse_move_and_click(ui_test.Vec2(200, 200))
        await ui_test.human_delay(40)

        # Should be in EDIT mode:
        self.assertEqual(get_markup_state(), MarkupState.EDIT)
        buttons = {
            w.widget.identifier: w
            for w in ui_test.find_all("Viewport//Frame/**")
            if "elementbar_btn_" in w.widget.identifier
        }

        elem = inst.get_markup_elements()[0]
        self.assertEqual(inst.get_element_attr(elem.GetName(), "type", ""), "Line")

        borderWidths = []
        await buttons["elementbar_btn_stroke_s"].click()
        await ui_test.human_delay(20)
        self.assertEqual(get_markup_state(), MarkupState.EDIT)
        style = eval(inst.get_element_attr(elem.GetName(), "style", "{}"))
        borderWidths.append(list(style.values())[0]["border_width"])

        await buttons["elementbar_btn_stroke_m"].click()
        await ui_test.human_delay(20)
        self.assertEqual(get_markup_state(), MarkupState.EDIT)
        style = eval(inst.get_element_attr(elem.GetName(), "style", "{}"))
        borderWidths.append(list(style.values())[0]["border_width"])

        await buttons["elementbar_btn_stroke_l"].click()
        await ui_test.human_delay(20)
        self.assertEqual(get_markup_state(), MarkupState.EDIT)
        style = eval(inst.get_element_attr(elem.GetName(), "style", "{}"))
        borderWidths.append(list(style.values())[0]["border_width"])

        await buttons["elementbar_btn_stroke_xl"].click()
        await ui_test.human_delay(20)
        self.assertEqual(get_markup_state(), MarkupState.EDIT)
        style = eval(inst.get_element_attr(elem.GetName(), "style", "{}"))
        borderWidths.append(list(style.values())[0]["border_width"])

        # unique border widths:
        self.assertEqual(len(set(borderWidths)), len(borderWidths))

        # ...in order of increasing size:
        self.assertEqual(sorted(borderWidths), borderWidths)

        style = eval(inst.get_element_attr(elem.GetName(), "style", "{}"))

        await buttons["elementbar_btn_color"].click()
        await ui_test.human_delay(20)
        self.assertEqual(get_markup_state(), MarkupState.COLOR_PICKER)
        await ui_test.emulate_mouse_move_and_click(buttons["elementbar_btn_color"].position + ui_test.Vec2(40, 40))
        await ui_test.human_delay(20)
        self.assertEqual(get_markup_state(), MarkupState.COLOR_PICKER)

        style = eval(inst.get_element_attr(elem.GetName(), "style", "{}"))

        # have to click off the widget for the prim to be updated:
        await ui_test.emulate_mouse_move_and_click(ui_test.Vec2(100, 100))
        await ui_test.human_delay(100)

        old_color = list(style.values())[0]["color"]
        style = eval(inst.get_element_attr(elem.GetName(), "style", "{}"))
        self.assertNotEqual(list(style.values())[0]["color"], old_color)

        # click back on and select:
        await ui_test.emulate_mouse_move_and_click(ui_test.Vec2(200, 200))
        await ui_test.human_delay(20)

        # remove the element:
        await buttons["elementbar_btn_remove"].click()
        await ui_test.human_delay(20)
        self.assertEqual(get_markup_state(), MarkupState.READY)
        self.assertEqual(len(inst.get_markup_elements()), 0)

    async def test_toolbar_comment(self):

        # click on the comment button:
        buttons = {
            w.widget.identifier: w
            for w in ui_test.find_all("Viewport//Frame/**")
            if "toolbar_btn" in w.widget.identifier
        }

        await buttons["toolbar_btn_comment"].click()
        await ui_test.human_delay(20)
        self.assertEqual(get_markup_state(), MarkupState.READY)
        self.assertEqual(self._setting.get_as_string(MARKUP_TOOL_CURRENT), TOOL_NAME.COMMENT)

        # create a comment:
        await ui_test.emulate_mouse_move(ui_test.Vec2(200, 200))
        await ui_test.human_delay(40)
        await ui_test.emulate_mouse_click()
        await ui_test.human_delay(40)

        inst = get_markup_instance()
        self.assertEqual(len(inst.get_markup_elements()), 1)
        elem = inst.get_markup_elements()[0]
        self.assertEqual(inst.get_element_attr(elem.GetName(), "type", ""), "Label")

        # find the text input:
        text_input_field = ui_test.find("Viewport//Frame/**/text_input_field")
        await text_input_field.input("testytest", clear_before_input=True)
        await ui_test.human_delay(40)

        # click off it and update the prim:
        await ui_test.emulate_mouse_move_and_click(ui_test.Vec2(100, 100))
        await ui_test.human_delay(40)
        self.assertEqual(inst.get_element_attr(elem.GetName(), "text", "").strip(), "testytest")

        # select again:
        await ui_test.emulate_mouse_move_and_click(ui_test.Vec2(200, 200))
        await ui_test.human_delay(40)

        # Should be in EDIT_COMMENT mode:
        self.assertEqual(get_markup_state(), MarkupState.EDIT_COMMENT)
        buttons = {
            w.widget.identifier: w
            for w in ui_test.find_all("Viewport//Frame/**")
            if "elementbar_btn_" in w.widget.identifier
        }

        fontSizes = []
        await buttons["elementbar_btn_text_s"].click()
        await ui_test.human_delay(20)
        self.assertEqual(get_markup_state(), MarkupState.EDIT_COMMENT)
        style = eval(inst.get_element_attr(elem.GetName(), "style", "{}"))
        fontSizes.append(list(style.values())[0]["font_size"])

        await buttons["elementbar_btn_text_m"].click()
        await ui_test.human_delay(20)
        self.assertEqual(get_markup_state(), MarkupState.EDIT_COMMENT)
        style = eval(inst.get_element_attr(elem.GetName(), "style", "{}"))
        fontSizes.append(list(style.values())[0]["font_size"])

        await buttons["elementbar_btn_text_l"].click()
        await ui_test.human_delay(20)
        self.assertEqual(get_markup_state(), MarkupState.EDIT_COMMENT)
        style = eval(inst.get_element_attr(elem.GetName(), "style", "{}"))
        fontSizes.append(list(style.values())[0]["font_size"])

        await buttons["elementbar_btn_text_xl"].click()
        await ui_test.human_delay(20)
        self.assertEqual(get_markup_state(), MarkupState.EDIT_COMMENT)
        style = eval(inst.get_element_attr(elem.GetName(), "style", "{}"))
        fontSizes.append(list(style.values())[0]["font_size"])

        # unique border widths:
        self.assertEqual(len(set(fontSizes)), len(fontSizes))

        # ...in order of increasing size:
        self.assertEqual(sorted(fontSizes), fontSizes)

        await buttons["elementbar_btn_color"].click()
        await ui_test.human_delay(20)
        self.assertEqual(get_markup_state(), MarkupState.COLOR_PICKER)
        await ui_test.emulate_mouse_move_and_click(buttons["elementbar_btn_color"].position + ui_test.Vec2(40, 40))
        await ui_test.human_delay(20)
        self.assertEqual(get_markup_state(), MarkupState.COLOR_PICKER)

        # have to click off the widget for the prim to be updated:
        await ui_test.emulate_mouse_move_and_click(ui_test.Vec2(100, 100))
        await ui_test.human_delay(100)

        old_color = list(style.values())[0]["color"]
        style = eval(inst.get_element_attr(elem.GetName(), "style", "{}"))
        self.assertNotEqual(list(style.values())[0]["color"], old_color)

        # click back on and select:
        await ui_test.emulate_mouse_move_and_click(ui_test.Vec2(200, 200))
        await ui_test.human_delay(20)

        # remove the element:
        await buttons["elementbar_btn_remove"].click()
        await ui_test.human_delay(20)
        self.assertEqual(get_markup_state(), MarkupState.READY)
        self.assertEqual(len(inst.get_markup_elements()), 0)

    async def test_toolbar_style_modes(self):

        tool_buttons = {
            w.widget.identifier: w
            for w in ui_test.find_all("Viewport//Frame/**")
            if "toolbar_btn" in w.widget.identifier
        }

        # click on the arrow button:
        await tool_buttons["toolbar_btn_arrow"].click()
        await ui_test.human_delay(20)
        self.assertEqual(get_markup_state(), MarkupState.READY)
        self.assertEqual(self._setting.get_as_string(MARKUP_TOOL_CURRENT), TOOL_NAME.ARROW)

        await ui_test.human_delay(20)
        buttons = {
            w.widget.identifier: w
            for w in ui_test.find_all("Viewport//Frame/**")
            if "elementtool_btn_" in w.widget.identifier
        }

        await buttons["elementtool_btn_arrow_start"].click()
        await ui_test.human_delay(20)
        self.assertEqual(get_markup_state(), MarkupState.READY)

        await buttons["elementtool_btn_arrow_end"].click()
        await ui_test.human_delay(20)
        self.assertEqual(get_markup_state(), MarkupState.READY)

        await buttons["elementtool_btn_arrow_double"].click()
        await ui_test.human_delay(20)
        self.assertEqual(get_markup_state(), MarkupState.READY)

        await buttons["elementtool_btn_color"].click()
        await ui_test.human_delay(20)
        self.assertEqual(get_markup_state(), MarkupState.COLOR_PICKER)

        await buttons["elementtool_btn_stroke_s"].click()
        await ui_test.human_delay(20)
        self.assertEqual(get_markup_state(), MarkupState.READY)

        await buttons["elementtool_btn_stroke_m"].click()
        await ui_test.human_delay(20)
        self.assertEqual(get_markup_state(), MarkupState.READY)

        await buttons["elementtool_btn_stroke_l"].click()
        await ui_test.human_delay(20)
        self.assertEqual(get_markup_state(), MarkupState.READY)

        await buttons["elementtool_btn_stroke_xl"].click()
        await ui_test.human_delay(20)
        self.assertEqual(get_markup_state(), MarkupState.READY)

        # click on the line button:
        await tool_buttons["toolbar_btn_line"].click()
        await ui_test.human_delay(100)
        self.assertEqual(get_markup_state(), MarkupState.READY)
        self.assertEqual(self._setting.get_as_string(MARKUP_TOOL_CURRENT), TOOL_NAME.LINE)

        await ui_test.human_delay(20)
        buttons = {
            w.widget.identifier: w
            for w in ui_test.find_all("Viewport//Frame/**")
            if "elementtool_btn_" in w.widget.identifier
        }

        await buttons["elementtool_btn_color"].click()
        await ui_test.human_delay(20)
        self.assertEqual(get_markup_state(), MarkupState.COLOR_PICKER)

        await buttons["elementtool_btn_stroke_s"].click()
        await ui_test.human_delay(20)
        self.assertEqual(get_markup_state(), MarkupState.READY)

        await buttons["elementtool_btn_stroke_m"].click()
        await ui_test.human_delay(20)
        self.assertEqual(get_markup_state(), MarkupState.READY)

        await buttons["elementtool_btn_stroke_l"].click()
        await ui_test.human_delay(20)
        self.assertEqual(get_markup_state(), MarkupState.READY)

        await buttons["elementtool_btn_stroke_xl"].click()
        await ui_test.human_delay(20)
        self.assertEqual(get_markup_state(), MarkupState.READY)

        # click on the line button:
        await tool_buttons["toolbar_btn_draw"].click()
        await ui_test.human_delay(20)
        self.assertEqual(get_markup_state(), MarkupState.READY)
        self.assertEqual(self._setting.get_as_string(MARKUP_TOOL_CURRENT), TOOL_NAME.DRAW)

        await ui_test.human_delay(20)
        buttons = {
            w.widget.identifier: w
            for w in ui_test.find_all("Viewport//Frame/**")
            if "elementtool_btn_" in w.widget.identifier
        }

        await buttons["elementtool_btn_color"].click()
        await ui_test.human_delay(20)
        self.assertEqual(get_markup_state(), MarkupState.COLOR_PICKER)

        await buttons["elementtool_btn_stroke_s"].click()
        await ui_test.human_delay(20)
        self.assertEqual(get_markup_state(), MarkupState.READY)

        await buttons["elementtool_btn_stroke_m"].click()
        await ui_test.human_delay(20)
        self.assertEqual(get_markup_state(), MarkupState.READY)

        await buttons["elementtool_btn_stroke_l"].click()
        await ui_test.human_delay(20)
        self.assertEqual(get_markup_state(), MarkupState.READY)

        await buttons["elementtool_btn_stroke_xl"].click()
        await ui_test.human_delay(20)
        self.assertEqual(get_markup_state(), MarkupState.READY)

        # click on the shapes button:
        await tool_buttons["toolbar_btn_shapes"].click()
        await ui_test.human_delay(100)
        self.assertEqual(get_markup_state(), MarkupState.READY)
        self.assertEqual(self._setting.get_as_string(MARKUP_TOOL_CURRENT), TOOL_NAME.SHAPES)

        await ui_test.human_delay(20)
        buttons = {
            w.widget.identifier: w
            for w in ui_test.find_all("Viewport//Frame/**")
            if "elementtool_btn_" in w.widget.identifier
        }

        await buttons["elementtool_btn_rectangle"].click()
        await ui_test.human_delay(20)
        self.assertEqual(get_markup_state(), MarkupState.READY)

        await buttons["elementtool_btn_circle"].click()
        await ui_test.human_delay(20)
        self.assertEqual(get_markup_state(), MarkupState.READY)

        await buttons["elementtool_btn_color"].click()
        await ui_test.human_delay(20)
        self.assertEqual(get_markup_state(), MarkupState.COLOR_PICKER)

        await buttons["elementtool_btn_stroke_s"].click()
        await ui_test.human_delay(20)
        self.assertEqual(get_markup_state(), MarkupState.READY)

        await buttons["elementtool_btn_stroke_m"].click()
        await ui_test.human_delay(20)
        self.assertEqual(get_markup_state(), MarkupState.READY)

        await buttons["elementtool_btn_stroke_l"].click()
        await ui_test.human_delay(20)
        self.assertEqual(get_markup_state(), MarkupState.READY)

        await buttons["elementtool_btn_stroke_xl"].click()
        await ui_test.human_delay(20)
        self.assertEqual(get_markup_state(), MarkupState.READY)

        # click on the comment button:
        await tool_buttons["toolbar_btn_comment"].click()
        await ui_test.human_delay(100)
        self.assertEqual(get_markup_state(), MarkupState.READY)
        self.assertEqual(self._setting.get_as_string(MARKUP_TOOL_CURRENT), TOOL_NAME.COMMENT)

        await ui_test.human_delay(20)
        buttons = {
            w.widget.identifier: w
            for w in ui_test.find_all("Viewport//Frame/**")
            if "elementtool_btn_" in w.widget.identifier
        }

        await buttons["elementtool_btn_text_m"].click()
        await ui_test.human_delay(100)
        self.assertEqual(get_markup_state(), MarkupState.READY)

        await buttons["elementtool_btn_text_l"].click()
        await ui_test.human_delay(100)
        self.assertEqual(get_markup_state(), MarkupState.READY)

        await buttons["elementtool_btn_text_xl"].click()
        await ui_test.human_delay(50)
        self.assertEqual(get_markup_state(), MarkupState.READY)

        await buttons["elementtool_btn_text_s"].click()
        await ui_test.human_delay(100)
        self.assertEqual(get_markup_state(), MarkupState.READY)

        await buttons["elementtool_btn_color"].click()
        await ui_test.human_delay(100)
        self.assertEqual(get_markup_state(), MarkupState.COLOR_PICKER)

    async def test_wide_window(self):
        # resize the viewport
        # XXX no idea why I need to resize the viewport twice, then click one of the toolbar buttons,
        # before the toolbar appears correctly...
        for _ in range(2):
            await self._dock_viewport(width=1280, height=150)
            self._setting.set_string(MARKUP_TOOL_CURRENT, "")

        buttons = {
            w.widget.identifier: w
            for w in ui_test.find_all("Viewport//Frame/**")
            if "toolbar_btn" in w.widget.identifier
        }
        self.assertTrue("toolbar_btn_draw" in buttons)
        await buttons["toolbar_btn_draw"].click()
        await ui_test.human_delay(20)
        buttons = {
            w.widget.identifier: w
            for w in ui_test.find_all("Viewport//Frame/**")
            if "elementtool_btn_" in w.widget.identifier
        }
        self.assertTrue("elementtool_btn_stroke_s" in buttons)
        await buttons["elementtool_btn_stroke_s"].click()
        await ui_test.human_delay(20)

        await self.finalize_test(golden_img_dir=self._golden_img_dir, golden_img_name="toolbar_wide_window.png")

    async def test_toolbar_cancel_undo(self):

        await ui_test.human_delay(20)

        buttons = {
            w.widget.identifier: w
            for w in ui_test.find_all("Viewport//Frame/**")
            if "toolbar_btn" in w.widget.identifier
        }

        markup = list(get_markup_instance().get_markups())[0]
        self.assertEqual(get_markup_instance().current_markup, markup)
        self.assertEqual(get_markup_instance().editing_markup, markup)

        self.assertTrue("toolbar_btn_markup_cancel" in buttons)
        await buttons["toolbar_btn_markup_cancel"].click()
        await next_viewport_frame_async(get_active_viewport())
        await ui_test.human_delay(20)

        omni.kit.undo.undo()

        # if undo doesn't log a carb error, this test has passed.

    async def test_toolbar_hotkeys(self):
        buttons = {
            w.widget.identifier: w
            for w in ui_test.find_all("Viewport//Frame/**")
            if "toolbar_btn" in w.widget.identifier
        }

        await buttons["toolbar_btn_comment"].click()
        tool_list = [
            TOOL_NAME.COMMENT,
            TOOL_NAME.DRAW,
            TOOL_NAME.ARROW,
            TOOL_NAME.LINE,
            TOOL_NAME.SHAPES,
        ]

        # Activate comment tool
        await ui_test.human_delay(20)
        self.assertEqual(get_markup_state(), MarkupState.READY)

        # Use hotkey to switch among tools
        for tool_name in tool_list:
            self.assertEqual(self._setting.get_as_string(MARKUP_TOOL_CURRENT), tool_name)
            await ui_test.emulate_key_combo("PAGE_UP")
            await ui_test.human_delay(20)

        self.assertEqual(self._setting.get_as_string(MARKUP_TOOL_CURRENT), TOOL_NAME.COMMENT)

        for tool_name in reversed(tool_list):
            await ui_test.emulate_key_combo("PAGE_DOWN")
            await ui_test.human_delay(20)
            self.assertEqual(self._setting.get_as_string(MARKUP_TOOL_CURRENT), tool_name)
