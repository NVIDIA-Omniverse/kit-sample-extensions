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
import omni.kit.test
from omni.kit.test_suite.helpers import wait_stage_loading
from omni.kit.waypoint.core import get_instance
from omni.kit.waypoint.core.common import WAYPOINT_ROOT_PRIM_PATH
from omni.kit.waypoint.core.playlist_card_waypoint import WaypointCard

CURRENT_PATH = Path(__file__).parent
TEST_DATA_PATH = CURRENT_PATH.parent.parent.parent.parent.parent.joinpath("data").joinpath("tests")


class TestWaypointPlaylistCard(omni.kit.test.AsyncTestCase):
    # Before running each test
    async def setUp(self):
        self._ext = get_instance()
        self._context = omni.usd.get_context()
        await self._context.new_stage_async()

    # After running each test
    async def tearDown(self):
        pass

    async def test_1_accept(self):
        # NOTE: is_waypoint_prim() does not check for existence, just that it's a valid-looking path.
        self.assertTrue(WaypointCard.accept(WAYPOINT_ROOT_PRIM_PATH + "/Waypoint_00"))
        self.assertFalse(WaypointCard.accept("Gar\\bage"))

    async def test_2_card(self):
        await self._context.open_stage_async(f"{TEST_DATA_PATH}/stage/cubes_with_waypoints.usda")
        await wait_stage_loading()

        waypoint = self._ext.get_waypoint("Waypoint_2")
        card = WaypointCard.create(WaypointCard.PLAYLIST_CARD_TYPE_WAYPOINT, path=waypoint.path)

        self.assertEqual(card.menu_text, "Waypoints")
        self.assertEqual(card.camera_prim, waypoint.camera_prim)
        self.assertEqual(card.icon[-3:], "svg")

        self.assertIsNone(self._ext.current_waypoint)
        card.active()
        self.assertEqual(self._ext.current_waypoint, waypoint)
        card.clean()

        # NOTE: The clean function just calls active. This may not be correct behavior.
        self.assertEqual(self._ext.current_waypoint, waypoint)

    async def test_3_invalid_card(self):
        invalid_card = WaypointCard(WaypointCard.PLAYLIST_CARD_TYPE_WAYPOINT, path="/Not/a/Prim")
        invalid_card.active()  # This will trigger an error in the carb log
        self.assertIsNone(invalid_card.camera_prim)
