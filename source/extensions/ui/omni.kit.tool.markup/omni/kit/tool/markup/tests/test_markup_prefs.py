# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
import glob
import os
import sys
import unittest
from pathlib import Path

import carb.settings
import omni.kit.app
import omni.usd
from carb.input import KeyboardInput, MouseEventType
from omni import ui
from omni.kit import ui_test
from omni.kit.markup.core import SETTING_MARKUP_EXPORT_LOCAL_FOLDER
from omni.kit.markup.core import get_instance as get_markup_instance
from omni.kit.tool.markup.common.settings import MarkupPreferences
from omni.kit.viewport.utility import get_active_viewport, get_active_viewport_window, next_viewport_frame_async
from omni.ui.tests.test_base import OmniUiTest
from omni.ui_query.query import OmniUIQuery

from ..ui.constant import TOOL_NAME
from ..ui.markup_scene import MARKUP_TOOL_CURRENT, SETTINGS_MARKUP_ACTIVE, SETTINGS_MARKUP_EDITING

CURRENT_PATH = Path(__file__).parent
TEST_DATA_PATH = CURRENT_PATH.parent.parent.parent.parent.parent.joinpath("data").joinpath("tests")
VISIBILITY_PATH = "/persistent/app/viewport/displayOptions"


class MarkupPrefsWindow(ui.Window):
    """
    Represent a window to show and edit markups.
    """

    def __init__(self):

        super().__init__("Markup Widget Test", width=500, height=600)
        self._widget = None

        self.frame.set_build_fn(self._build_ui)

    def destroy(self) -> None:
        if self._widget:
            self._widget.destroy()

        self.visible = False

    def _build_ui(self):
        with self.frame:
            self._widget = MarkupPreferences()
            self._widget.build()


class TestMarkupPrefs(OmniUiTest):

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
        get_markup_instance().end_edit_markup(list(get_markup_instance().get_markups())[0], save=True)
        await ui_test.human_delay()
        self._setting.set_string(MARKUP_TOOL_CURRENT, "select")
        self._setting.set_string(SETTING_MARKUP_EXPORT_LOCAL_FOLDER, omni.kit.test.get_test_output_path())

    # After running each test
    async def tearDown(self):
        self._setting.set(VISIBILITY_PATH, self._visibility_value)
        await super().tearDown()
        self._setting.set_string(MARKUP_TOOL_CURRENT, "")
        self._setting.set_string(SETTINGS_MARKUP_EDITING, "")
        self._setting.set_string(SETTINGS_MARKUP_ACTIVE, "")

    async def test_prefs_widget(self):

        window = MarkupPrefsWindow()
        window.visible = True

        window.selected_index = 1

        await omni.kit.app.get_app().next_update_async()
        await self.docked_test_window(window=window, width=1280, height=720, block_devices=False)

        await ui_test.human_delay(2)

        labels = [
            w
            for w in ui_test.find_all(f"{window.title}//Frame/**")
            if w.widget.style_type_name_override == "Setting.Label"
        ]
        self.assertEqual([l.widget.text for l in labels], ["Selection Tolerance"])

        window.destroy()
