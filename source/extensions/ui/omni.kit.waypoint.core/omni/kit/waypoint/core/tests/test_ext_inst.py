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

import omni.kit.app
import omni.kit.test
import omni.usd
from omni.kit.test_suite.helpers import wait_stage_loading
from omni.kit.waypoint.core import get_instance
from omni.kit.waypoint.core.common import IGNORE_PRIM_ATTR_NAME, WAYPOINT_ROOT_PRIM_PATH
from pxr import Sdf, Usd

from ..settings.general import WAYPOINT_ATTR_COMMENT

CURRENT_PATH = Path(__file__).parent
TEST_DATA_PATH = CURRENT_PATH.parent.parent.parent.parent.parent.joinpath("data").joinpath("tests")
CAMERA_PRIM_PATH = "/OmniverseKit_Persp"
ENVIRONMENT_PATH = "/Environment"


class TestExtInst(omni.kit.test.AsyncTestCase):
    async def setUp(self):
        self._context = omni.usd.get_context()
        await self._context.new_stage_async()
        self._ext = get_instance()

    async def tearDown(self):
        pass

    async def test_1_create_async(self):
        self.assertEqual(len(self._ext.get_waypoints()), 0)

        # Create a new waypoint.
        await self._ext.create_waypoint_async()
        self.assertEqual(len(self._ext.get_waypoints()), 1)
        self.assertIsNotNone(self._ext.get_waypoint("Waypoint_00"))
        self.assertIsNotNone(self._ext.get_waypoint_from_prim_path(WAYPOINT_ROOT_PRIM_PATH + "/Waypoint_00"))

        # Attempt to create a duplicate waypoint.
        await self._ext.create_waypoint_async()
        self.assertEqual(len(self._ext.get_waypoints()), 1)
        self.assertIsNone(self._ext.get_waypoint("Waypoint_01"))
        self.assertIsNone(self._ext.get_waypoint_from_prim_path(WAYPOINT_ROOT_PRIM_PATH + "/Waypoint_01"))

    async def test_2_objects_changed(self):
        await self._ext.create_waypoint_async()
        waypoint = self._ext.get_waypoint("Waypoint_00")
        self.assertIsNotNone(waypoint)
        usd_prim = waypoint.usd_prim
        self.assertIsNotNone(usd_prim)
        self.assertEqual(waypoint.comment, "")
        usd_prim.CreateAttribute(WAYPOINT_ATTR_COMMENT, Sdf.ValueTypeNames.String).Set("Test OMFP-3306")
        # Note: When an attribute changes, the Waypoint is updated on the _next_ update.  So, check the value of the
        # comment on the update after that.
        await omni.kit.app.get_app().next_update_async()
        await omni.kit.app.get_app().next_update_async()
        self.assertEqual(waypoint.comment, "Test OMFP-3306")

    async def test_3_rename(self):
        await self._context.open_stage_async(f"{TEST_DATA_PATH}/stage/cubes_with_waypoints.usda")
        await wait_stage_loading()

        waypoint = self._ext.get_waypoint("Waypoint_1")

        # Successful rename
        ret = self._ext.rename_waypoint(waypoint, "Test")

        await omni.kit.app.get_app().next_update_async()
        await omni.kit.app.get_app().next_update_async()

        self.assertTrue(ret)
        self.assertEqual(waypoint.name, "Test")
        self.assertEqual(waypoint, self._ext.get_waypoint("Test"))

        # Rename to the same name
        ret = self._ext.rename_waypoint(waypoint, "Test")
        self.assertTrue(ret)

        # Rename to an existing name
        ret = self._ext.rename_waypoint(waypoint, "Waypoint_2")
        self.assertFalse(ret)

        # Rename to an invalid name
        ret = self._ext.rename_waypoint(waypoint, "Invalid\\Path")
        self.assertFalse(ret)

        await omni.kit.app.get_app().next_update_async()
        await omni.kit.app.get_app().next_update_async()

    async def test_4_recall(self):
        await self._context.open_stage_async(f"{TEST_DATA_PATH}/stage/cubes_with_waypoints.usda")
        await wait_stage_loading()

        waypoint_1 = self._ext.get_waypoint("Waypoint_1")
        waypoint_2 = self._ext.get_waypoint("Waypoint_2")

        stage = self._context.get_stage()
        camera_prim = stage.GetPrimAtPath(CAMERA_PRIM_PATH)
        initial_has_ignore_prim = camera_prim.HasAttribute(IGNORE_PRIM_ATTR_NAME)
        initial_ignore_prim_value = (
            camera_prim.GetAttribute(IGNORE_PRIM_ATTR_NAME).Get() if initial_has_ignore_prim else None
        )

        # default settings
        self._ext.recall_waypoint(waypoint_1)
        self.assertEqual(self._ext.current_waypoint, waypoint_1)
        purpose = camera_prim.GetAttribute("purpose").Get()
        self.assertEqual(purpose, "Waypoint_1")
        self.assertEqual(camera_prim.HasAttribute(IGNORE_PRIM_ATTR_NAME), initial_has_ignore_prim)
        if initial_has_ignore_prim:
            self.assertEqual(camera_prim.GetAttribute(IGNORE_PRIM_ATTR_NAME).Get(), initial_ignore_prim_value)
        await omni.kit.app.get_app().next_update_async()
        await omni.kit.app.get_app().next_update_async()
        self.assertEqual(self._ext.current_waypoint, waypoint_1)

        # without camera
        self._ext.recall_waypoint(waypoint_2, without_camera=True)
        self.assertEqual(self._ext.current_waypoint, waypoint_2)
        purpose = camera_prim.GetAttribute("purpose").Get()
        self.assertEqual(purpose, "Waypoint_1")

        # as the camera doesn't match, it won't be considered current after some updates.
        await omni.kit.app.get_app().next_update_async()
        await omni.kit.app.get_app().next_update_async()
        self.assertIsNone(self._ext.current_waypoint)

        # recall again (no force)
        self._ext.recall_waypoint(waypoint_2, without_camera=True)
        self._ext.recall_waypoint(waypoint_2)
        self.assertEqual(self._ext.current_waypoint, waypoint_2)
        purpose = camera_prim.GetAttribute("purpose").Get()
        self.assertEqual(purpose, "Waypoint_1")  # Since recall isn't forced, this value should not yet change.

        # recall again (force)
        self._ext.recall_waypoint(waypoint_2, force=True)
        self.assertEqual(self._ext.current_waypoint, waypoint_2)
        purpose = camera_prim.GetAttribute("purpose").Get()
        self.assertEqual(purpose, "Waypoint_2")  # Recall was forced (with camera enabled), so this should update.

        await omni.kit.app.get_app().next_update_async()
        await omni.kit.app.get_app().next_update_async()
        self.assertEqual(self._ext.current_waypoint, waypoint_2)

        # disable/enable settings
        env_prim = stage.GetPrimAtPath(ENVIRONMENT_PATH)

        # change the sunstudy values, so we can tell it hasn't been recalled.
        edit_context = Usd.EditContext(stage, Usd.EditTarget(stage.GetSessionLayer()))
        with edit_context:
            env_prim.GetAttribute("date").Set("2023-01-01")
        self._ext.recall_waypoint(waypoint_1, enable_settings=["Prim Visibility"], disable_settings=["Sunstudy"])
        self.assertEqual(self._ext.current_waypoint, waypoint_1)
        self.assertEqual(env_prim.GetAttribute("date").Get(), "2023-01-01")

        # NOTE: Prim Visibility is currently not stored in the waypoint. As a result, when enabling it, it is still
        # invalid, and the recall function returns immediately.

        # recall None
        self._ext.recall_waypoint(None)
        self.assertIsNone(self._ext.current_waypoint)

    async def test_5_hide_prims(self):
        # This is a test for OMFP-2500

        await self._ext.create_waypoint_async()

        waypoint_root_prim = self._context.get_stage().GetPrimAtPath("/Viewport_Waypoints")
        hidden = waypoint_root_prim.GetMetadata("hide_in_stage_window")
        self.assertTrue(hidden)

    async def test_6_icon_click(self):
        await self._context.open_stage_async(f"{TEST_DATA_PATH}/stage/cubes_with_waypoints.usda")
        await wait_stage_loading()

        # Use the prim_icon click function (as would be triggered by clicking the waypoint in the viewport)
        path = WAYPOINT_ROOT_PRIM_PATH + "/Waypoint_2"
        click_fn = self._ext._prim_icon.model.get_on_click(path)
        click_fn(path)
        await omni.kit.app.get_app().next_update_async()
        await omni.kit.app.get_app().next_update_async()
        self.assertEqual(self._ext.current_waypoint.name, "Waypoint_2")

    async def test_7_edit_target_override(self):
        await self._context.open_stage_async(f"{TEST_DATA_PATH}/stage/cubes_with_waypoints.usda")
        await wait_stage_loading()

        stage = self._context.get_stage()
        root_layer = stage.GetRootLayer()
        original_edit_target = stage.GetEditTarget()

        # Create a temp layer and set it as the WaypointExtension.edit_target override
        temp_layer = Sdf.Layer.CreateAnonymous("temporary_layer")
        root_layer.subLayerPaths.append(temp_layer.identifier)
        self._ext.edit_target = temp_layer

        # Assert the WaypointExtension.edit_context results in the temporary layer edit target
        with self._ext.edit_context:
            self.assertEqual(stage.GetEditTarget(), temp_layer)

        # Assert that the edit target is the same without the custom edit context
        self.assertEqual(stage.GetEditTarget(), original_edit_target)

        # Reset the WaypointExtension.edit_target and remove the temp layer
        self._ext.edit_target = None
        root_layer.subLayerPaths.remove(temp_layer.identifier)
