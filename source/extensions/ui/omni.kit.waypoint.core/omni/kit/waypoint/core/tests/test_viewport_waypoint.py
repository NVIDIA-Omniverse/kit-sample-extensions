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
import omni.kit.commands
import omni.kit.test
from omni.kit.test_suite.helpers import wait_stage_loading
from omni.kit.waypoint.core import get_instance
from omni.kit.waypoint.core.common import WAYPOINT_ROOT_PRIM_PATH, create_data_only_prim
from omni.kit.waypoint.core.viewport_waypoint import ViewportWaypoint

CURRENT_PATH = Path(__file__).parent
TEST_DATA_PATH = CURRENT_PATH.parent.parent.parent.parent.parent.joinpath("data").joinpath("tests")


class TestViewportWaypoint(omni.kit.test.AsyncTestCase):
    # Before running each test
    async def setUp(self):
        self._ext = get_instance()
        self._context = omni.usd.get_context()
        await self._context.new_stage_async()

    # After running each test
    async def tearDown(self):
        # There are async functions that require a delay.
        await omni.kit.app.get_app().next_update_async()
        await omni.kit.app.get_app().next_update_async()
        pass

    async def test_1_properties(self):
        waypoint = ViewportWaypoint("Test_Waypoint")
        self.assertEqual(waypoint.name, "Test_Waypoint")
        self.assertEqual(str(waypoint), '"Test_Waypoint"')
        self.assertEqual(repr(waypoint), '"Test_Waypoint"')
        self.assertEqual(waypoint.path, "/Viewport_Waypoints/Test_Waypoint")
        self.assertIsNone(waypoint.thumbnail)
        self.assertIsNone(waypoint.thumbnail_data)
        self.assertIsNone(waypoint.create_time)
        self.assertIsNone(waypoint.created_by)
        self.assertEqual(waypoint.comment, "")

        # This will fail (and give a warning because of missing prim), but should otherwise cause no issue.
        waypoint.recall()

        # NOTE: Using the setter on the name doesn't check the prim or anything, just updates the name and resulting path.
        waypoint.name = "Setter_Name_Waypoint"
        self.assertEqual(str(waypoint), '"Setter_Name_Waypoint"')
        self.assertEqual(waypoint.path, "/Viewport_Waypoints/Setter_Name_Waypoint")

        # Invalid name.
        ret = waypoint.rename("Gar\\bage")
        self.assertFalse(ret)

        # Valid name (but the prim doesn't exist)
        ret = waypoint.rename("Renamed_Waypoint")
        self.assertFalse(ret)

    async def test_create_from_prim_succeeds_without_thumbnail(self):
        """OMPE-77101: create_from_prim should succeed when the prim has a valid
        name even if thumbnail data is not yet available.  Previously the method
        returned ``bool(self.thumbnail_data)`` which caused a spurious warning
        when the thumbnail had not been captured yet (asynchronous operation)."""
        stage = self._context.get_stage()

        # Ensure the waypoint root exists.
        root = stage.GetPrimAtPath(WAYPOINT_ROOT_PRIM_PATH)
        if not root:
            create_data_only_prim(stage, WAYPOINT_ROOT_PRIM_PATH)

        # Create a bare prim with no thumbnail data – this mirrors the state
        # immediately after a waypoint is first defined via create_waypoint()
        # but before the async thumbnail capture completes.
        test_path = f"{WAYPOINT_ROOT_PRIM_PATH}/No_Thumbnail_Waypoint"
        create_data_only_prim(stage, test_path)
        prim = stage.GetPrimAtPath(test_path)
        self.assertTrue(prim.IsValid())

        waypoint = ViewportWaypoint("", hide_in_stage_window_disabled=True)
        result = waypoint.create_from_prim(prim)

        # The waypoint should report success because the name was loaded.
        self.assertTrue(result, "create_from_prim should return True for a valid prim even without thumbnail data")
        self.assertEqual(waypoint.name, "No_Thumbnail_Waypoint")
        self.assertEqual(waypoint.path, f"{WAYPOINT_ROOT_PRIM_PATH}/No_Thumbnail_Waypoint")

        # Thumbnail data may legitimately be None at this point.
        # That must NOT prevent the waypoint from being considered valid.
        # (It was None in the original bug, causing the spurious warning.)

        # Clean up.
        omni.kit.commands.execute("DeletePrimsCommand", paths=[test_path], destructive=False)

    async def test_create_from_prim_fails_for_root_prim(self):
        """create_from_prim should return False when the prim path yields an
        empty waypoint name (e.g. the root '/' prim)."""
        stage = self._context.get_stage()

        # Use the root prim which has an empty name component after the last '/'.
        root_prim = stage.GetPseudoRoot()
        waypoint = ViewportWaypoint("", hide_in_stage_window_disabled=True)
        result = waypoint.create_from_prim(root_prim)

        self.assertFalse(result, "create_from_prim should return False when the prim name is empty")

    async def test_create_from_prim_no_spurious_warning_on_stage_change(self):
        """OMPE-77101: Creating a waypoint via the extension API and then
        allowing the ObjectsChanged notification to fire should NOT produce a
        'Failed to create any viewport waypoint' warning.

        We verify this end-to-end by creating a waypoint asynchronously and
        checking that the waypoint is properly tracked without errors."""
        ext = get_instance()

        # Create a waypoint asynchronously (as the real user flow does).
        await ext.create_waypoint_async()

        # Allow a couple of updates for ObjectsChanged to propagate.
        for _ in range(4):
            await omni.kit.app.get_app().next_update_async()

        # The waypoint must be in the tracked list.
        waypoints = list(ext.get_waypoints())
        self.assertGreaterEqual(len(waypoints), 1, "At least one waypoint should exist after creation")
        wp = ext.get_waypoint("Waypoint_00")
        self.assertIsNotNone(wp, "Waypoint_00 should be tracked by the extension")

        # Clean up.
        ext.delete_waypoint(wp)
        await omni.kit.app.get_app().next_update_async()
