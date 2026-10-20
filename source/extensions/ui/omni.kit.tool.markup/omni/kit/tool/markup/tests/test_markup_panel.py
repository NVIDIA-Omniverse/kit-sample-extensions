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
import copy
import os
import unittest
from pathlib import Path

import carb.settings
import omni.kit.app
import omni.ui as ui
from omni.kit import ui_test
from omni.kit.markup.core import get_instance as get_markup_instance
from omni.kit.markup.core.widgets.list_window import MarkupListWindow
from omni.kit.viewport.utility import get_active_viewport, get_active_viewport_window, next_viewport_frame_async
from omni.ui.tests.test_base import OmniUiTest

from ..ui.constant import TOOL_NAME
from ..ui.markup_scene import MARKUP_TOOL_CURRENT

CURRENT_PATH = Path(__file__).parent
TEST_DATA_PATH = CURRENT_PATH.parent.parent.parent.parent.parent.joinpath("data").joinpath("tests")
VISIBILITY_PATH = "/persistent/app/viewport/displayOptions"


class TestMarkupWindow(OmniUiTest):
    # Before running each test
    async def setUp(self):
        await super().setUp()
        self._golden_img_dir = TEST_DATA_PATH.absolute().joinpath("golden_img").absolute()
        self._setting = carb.settings.get_settings()
        self._visibility_value = self._setting.get(VISIBILITY_PATH)
        self._setting.set(VISIBILITY_PATH, 0)
        await omni.usd.get_context().new_stage_async()
        await ui_test.human_delay(10)
        get_markup_instance().create_markup()
        await ui_test.human_delay()
        await self._dock_viewport(width=1280, height=720)

    # After running each test
    async def tearDown(self):
        self._setting.set(VISIBILITY_PATH, self._visibility_value)
        await super().tearDown()

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

    @unittest.skipIf(os.getenv("ETM_ACTIVE") or os.getenv("ETM_DGXC_ACTIVE"), "skipped in ETM")
    async def test_markup_list(self):
        stroke_setting = "/persistent/exts/omni.kit.tool.markup/shapes/stroke"
        restore_settings = {
            f"{MARKUP_TOOL_CURRENT}": self._setting.get(MARKUP_TOOL_CURRENT),
            f"{stroke_setting}": self._setting.get(stroke_setting),
        }
        stage = omni.usd.get_context().get_stage()
        self.assertIsNotNone(stage)
        size = 120
        await ui_test.human_delay(5)
        self._setting.set_string(MARKUP_TOOL_CURRENT, TOOL_NAME.SHAPES)
        self._setting.set(stroke_setting, 8)
        p0 = ui_test.Vec2(580, 310)
        p1 = ui_test.Vec2(p0.x + size, p0.y + size)
        await ui_test.emulate_mouse_move(p0)
        await ui_test.emulate_mouse_drag_and_drop(p0, p1)
        await ui_test.emulate_mouse_move(ui_test.Vec2(750, 700))
        await ui_test.emulate_mouse_click()
        await ui_test.human_delay(10)
        window = MarkupListWindow()
        window.visible = True
        await ui_test.human_delay(10)
        await self.finalize_test(golden_img_dir=self._golden_img_dir, golden_img_name="test_markup_list.png")
        window.visible = False
        window.destroy()
        for setting_path in restore_settings:
            self._setting.set(setting_path, restore_settings[setting_path])
