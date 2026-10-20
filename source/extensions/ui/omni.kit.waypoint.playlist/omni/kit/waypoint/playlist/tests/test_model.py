# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

# NOTE:
#   omni.kit.test - std python's unittest module with additional wrapping to add suport for async/await tests
#   For most things refer to unittest docs: https://docs.python.org/3/library/unittest.html
from pathlib import Path
from unittest.mock import patch

import carb.eventdispatcher
import omni.kit.app
import omni.kit.test
from omni.kit import ui_test
from omni.kit.test_suite.helpers import wait_stage_loading
from omni.kit.waypoint.core import WaypointCard
from omni.kit.waypoint.core import get_instance as get_waypoint_instance
from omni.kit.waypoint.playlist import get_instance
from omni.ui.tests.test_base import OmniUiTest

CURRENT_PATH = Path(__file__).parent
TEST_DATA_PATH = CURRENT_PATH.parent.parent.parent.parent.parent.joinpath("data").joinpath("tests")

# Import extension python module we are testing with absolute import path, as if we are external user (other extension)
import omni.kit.waypoint.playlist


class TestExtension(OmniUiTest):
    async def test_extension(self):
        manager = omni.kit.app.get_app().get_extension_manager()
        ext_id = "omni.kit.waypoint.playlist"
        self.assertTrue(ext_id)
        self.assertTrue(manager.is_extension_enabled(ext_id))
        manager.set_extension_enabled(ext_id, False)
        await ui_test.human_delay()
        self.assertTrue(not manager.is_extension_enabled(ext_id))
        manager.set_extension_enabled(ext_id, True)
        await ui_test.human_delay()
        self.assertTrue(manager.is_extension_enabled(ext_id))


class TestPlaylistModel(omni.kit.test.AsyncTestCase):
    async def setUp(self):
        pass

    # After running each test
    async def tearDown(self):
        pass

    async def test_general(self):
        self._model = omni.kit.waypoint.playlist.AllWaypointPlaylistModel()
        self.assertTrue(self._model.system)
        self.assertTrue(self._model.name, "All Waypoints")
        self.assertEqual(len(self._model.items), 0)


class TestCoverage(omni.kit.test.AsyncTestCase):
    async def setUp(self):
        pass

    # After running each test
    async def tearDown(self):
        pass

    async def test_general_coverage(self):
        await omni.usd.get_context().open_stage_async(f"{TEST_DATA_PATH}/stage/only_waypoints.usda")
        await wait_stage_loading()

        # Wait for waypoint loaded
        for i in range(4):
            await omni.kit.app.get_app().next_update_async()

        # there is only on waypoint in the usda file
        waypoints = get_waypoint_instance().get_waypoints()
        self.assertEqual(len(waypoints), 1)

        # Test navigate
        with patch("omni.kit.playlist.core.PlayManager.navigate") as mock_navigate:
            get_instance().navigate(list(waypoints)[0], transition_time=0.5)
            mock_navigate.assert_called_once()

        # there is only one playlist which has type AllWaypointPlaylistModel
        from omni.kit.tool.camera_playlist import PlaylistManager

        all_waypoint_playlist_model = PlaylistManager.get_instance().get_playlist(0)
        # do it to create WaypointCard internally
        all_waypoint_playlist_model.check_update()

        index = all_waypoint_playlist_model.next_index
        self.assertEqual(index, 0)
        waypoint_card = all_waypoint_playlist_model.items[index].data
        expected_prim_str = "/Viewport_Waypoints/Waypoint_00/OmniverseKit_Persp"
        # cover camera_prim
        self.assertEqual(str(waypoint_card.camera_prim.GetPath()), expected_prim_str)
        # cover accept
        self.assertTrue(WaypointCard.accept(expected_prim_str))
        # cover menu_text
        self.assertEqual(waypoint_card.menu_text, "Waypoints")
        # cover icon
        self.assertEqual(waypoint_card.icon[-3:], "svg")
        # cover clean(), and interally active()
        waypoint_card.clean()

        # cover PlayControl
        dispatcher = carb.eventdispatcher.get_eventdispatcher()
        dispatcher.dispatch_event(omni.kit.waypoint.playlist.play_control.WAYPOIONT_PLAY_PLAY_EVENT, None)
        await omni.kit.app.get_app().next_update_async()
        dispatcher.dispatch_event(omni.kit.waypoint.playlist.play_control.WAYPOIONT_PLAY_STOP_EVENT, None)
        await omni.kit.app.get_app().next_update_async()
        dispatcher.dispatch_event(omni.kit.waypoint.playlist.play_control.WAYPOIONT_PLAY_NEXT_EVENT, None)
        await omni.kit.app.get_app().next_update_async()
        dispatcher.dispatch_event(omni.kit.waypoint.playlist.play_control.WAYPOIONT_PLAY_PREVIOUS_EVENT, None)
        await omni.kit.app.get_app().next_update_async()

        # cover AllWaypointPlaylistModel._on_waypoint_changed()
        get_waypoint_instance().delete_waypoint(list(waypoints)[0])
        self.assertEqual(len(waypoints), 0)

        # it might cause ViewportWaypoint._hide_waypoint_root_prim()'s omni.usd.get_context().get_stage() to get None
        # await omni.usd.get_context().close_stage_async()
