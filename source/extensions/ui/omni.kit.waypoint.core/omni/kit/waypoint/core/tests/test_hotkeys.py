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

import carb.settings
import omni.kit.app
import omni.kit.test
import omni.kit.ui_test as ui_test
import omni.ui as ui
import omni.usd
from omni.kit.test_suite.helpers import wait_stage_loading
from omni.kit.waypoint.core import SETTINGS_WAYPOINT_ENABLE_HOTKEYS, get_instance
from omni.kit.waypoint.core.widgets.list_window import WaypointListWindow
from omni.ui.tests.test_base import OmniUiTest

CURRENT_PATH = Path(__file__).parent
TEST_DATA_PATH = CURRENT_PATH.parent.parent.parent.parent.parent.joinpath("data").joinpath("tests").absolute()


class TestHotkeys(OmniUiTest):
    async def setUp(self):
        self._context = omni.usd.get_context()
        await self._context.new_stage_async()
        self._ext = get_instance()
        self._settings = carb.settings.get_settings()

    async def tearDown(self):
        window = ui.Workspace.get_window("Waypoints")
        if window is not None:
            window.visible = False
        await super().tearDown()

    async def test_1_hotkeys_disabled(self):
        self.assertEqual(len(self._ext.get_waypoints()), 0)

        await ui_test.emulate_key_combo("ALT+W")
        await ui_test.human_delay()

        self.assertEqual(len(self._ext.get_waypoints()), 0)
        window = ui.Workspace.get_window("Waypoints")
        self.assertTrue(window is None or not window.visible)

    async def test_2_hotkeys_next_prev(self):
        window = self._get_or_create_waypoint_list_window(True)

        self.assertEqual(len(self._ext.get_waypoints()), 0)

        self._settings.set(SETTINGS_WAYPOINT_ENABLE_HOTKEYS, True)
        await ui_test.human_delay()

        # next, previous
        await self._context.open_stage_async(f"{TEST_DATA_PATH}/stage/cubes_with_waypoints.usda")
        await wait_stage_loading()
        await self._wait_for_waypoint_load()
        self.assertEqual(len(self._ext.get_waypoints()), 2)

        self.assertIsNone(window.selected_index)

        await ui_test.emulate_key_combo("RIGHT")
        await ui_test.human_delay()
        self.assertEqual(window.selected_index, 1)

        await ui_test.emulate_key_combo("LEFT")
        await ui_test.human_delay()
        self.assertEqual(window.selected_index, 0)

    async def test_3_hotkeys_create(self):
        self.assertEqual(len(self._ext.get_waypoints()), 0)
        window = ui.Workspace.get_window("Waypoints")
        self.assertTrue(window is None or not window.visible)

        self._settings.set(SETTINGS_WAYPOINT_ENABLE_HOTKEYS, True)
        await ui_test.human_delay()

        # create waypoint
        await ui_test.emulate_key_combo("ALT+W")
        await ui_test.human_delay(10)
        self.assertEqual(len(self._ext.get_waypoints()), 1)
        window = ui.Workspace.get_window("Waypoints")
        self.assertIsNotNone(window)
        self.assertTrue(window.visible)

    async def test_4_hotkeys_delete(self):
        window = self._get_or_create_waypoint_list_window(True)
        self.assertEqual(len(self._ext.get_waypoints()), 0)

        self._settings.set(SETTINGS_WAYPOINT_ENABLE_HOTKEYS, True)
        await ui_test.human_delay()

        await self._context.open_stage_async(f"{TEST_DATA_PATH}/stage/cubes_with_waypoints.usda")
        await wait_stage_loading()
        await self._wait_for_waypoint_load()

        # select a waypoint
        window.selected_index = 0
        await ui_test.human_delay(10)

        # delete waypoint (and verify it's gone)
        await ui_test.emulate_key_combo("DEL")
        await ui_test.human_delay(10)
        self.assertEqual(len(self._ext.get_waypoints()), 1)

    async def _wait_for_waypoint_load(self):
        # This is currently imprecise.
        for i in range(4):
            await omni.kit.app.get_app().next_update_async()

    def _get_or_create_waypoint_list_window(self, visible: bool):
        window = ui.Workspace.get_window("Waypoints")
        if window is None:
            window = WaypointListWindow()
        window.visible = visible
        return window
