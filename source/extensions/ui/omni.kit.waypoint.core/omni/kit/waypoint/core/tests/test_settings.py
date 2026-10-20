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
import shutil
import tempfile
from pathlib import Path

import omni.kit.app
import omni.kit.test
import omni.usd
from omni.kit.test_suite.helpers import wait_stage_loading
from omni.kit.viewport.utility import get_active_viewport
from omni.kit.waypoint.core import get_instance
from omni.kit.waypoint.core.common import SETTINGS_WAYPOINT_ROOT
from omni.kit.waypoint.core.pereference import (
    SETTINGS_WAYPOINT_CAPTURE_DISABLED,
    SETTINGS_WAYPOINT_RECALL_DISABLED,
    WaypointPereference,
)
from pxr import Gf, Sdf, Usd, UsdGeom

from ..settings.sunstudy import ENVIRONMENT_PRIM_ROOT, WAYPOINT_ATTR_SUNSTUDY, EnvironmentProperties

CURRENT_PATH = Path(__file__).parent
TEST_DATA_PATH = CURRENT_PATH.parent.parent.parent.parent.parent.joinpath("data").joinpath("tests")


class TestSettings(omni.kit.test.AsyncTestCase):
    async def setUp(self):
        self._context = omni.usd.get_context()
        await self._context.new_stage_async()
        self._ext = get_instance()

        # record the original resoltion of the viewport to restore it when complete
        viewport_api = get_active_viewport()
        self._orig_resolution = viewport_api.resolution

    async def tearDown(self):
        WaypointPereference._restore_defaults("Cameras")
        WaypointPereference._restore_defaults("Render Settings")
        WaypointPereference._restore_defaults("Sunstudy Settings")
        WaypointPereference._restore_defaults("Prim Visibility")

        viewport_api = get_active_viewport()
        viewport_api.resolution = self._orig_resolution

        # Some tests have ensure_future calls that must complete (or throw an error)
        await omni.kit.app.get_app().next_update_async()
        await omni.kit.app.get_app().next_update_async()

        pass

    async def test_1_info(self):
        await self._context.open_stage_async(f"{TEST_DATA_PATH}/stage/cubes_no_waypoints.usda")
        await wait_stage_loading()

        await self._ext.create_waypoint_async()
        self.assertEqual(len(self._ext.get_waypoints()), 1)

        wp = self._ext.get_waypoint("Waypoint_00")
        info = wp.info
        self.assertEqual(len(info), 4)

    async def test_2_get_settings(self):
        capture_disabled = WaypointPereference._get_settings(SETTINGS_WAYPOINT_CAPTURE_DISABLED)
        self.assertEqual(len(capture_disabled), 1)
        self.assertEqual(capture_disabled[0], "Prim Visibility")

        garbage_setting = WaypointPereference._get_settings(SETTINGS_WAYPOINT_ROOT + "/garbage")
        self.assertEqual(len(garbage_setting), 0)

    async def test_3_prim_visibility(self):
        await self._context.open_stage_async(f"{TEST_DATA_PATH}/stage/cubes_no_waypoints.usda")
        await wait_stage_loading()

        WaypointPereference._set_setting_with_key(SETTINGS_WAYPOINT_CAPTURE_DISABLED, "Prim Visibility", True)
        WaypointPereference._set_setting_with_key(SETTINGS_WAYPOINT_RECALL_DISABLED, "Prim Visibility", True)

        # Create a waypoint with prim visibility enabled.
        await self._ext.create_waypoint_async()
        self.assertEqual(len(self._ext.get_waypoints()), 1)

        # Test changing visibility on an existing prim.
        wp = self._ext.get_waypoint("Waypoint_00")
        self._ext.begin_edit_waypoint(wp)
        self.assertFalse(wp.is_dirty)

        stage = self._context.get_stage()
        prim = stage.GetPrimAtPath("/World/Cube")
        imageable = UsdGeom.Imageable(prim)
        if imageable:
            imageable.MakeInvisible()

        await omni.kit.app.get_app().next_update_async()

        self.assertTrue(wp.is_dirty)
        self._ext.end_edit_waypoint(wp, False)

        # Test creating a prim
        self._ext.begin_edit_waypoint(wp)
        self.assertFalse(wp.is_dirty)

        stage = self._context.get_stage()
        edit_context = Usd.EditContext(stage, Usd.EditTarget(None))
        with edit_context:
            omni.kit.commands.execute(
                "CreatePrimCommand", prim_path="/World/Test_Xform", prim_type="Xform", select_new_prim=False
            )
        await omni.kit.app.get_app().next_update_async()

        self.assertTrue(wp.is_dirty)
        self._ext.end_edit_waypoint(wp, False)

        await omni.kit.app.get_app().next_update_async()

    # OMFP-3471 trigger sunstudy dirty
    async def test_4_sunstudy_dirty(self):
        await self._context.open_stage_async(f"{TEST_DATA_PATH}/stage/cubes_with_waypoints.usda")
        await wait_stage_loading()

        # Wait for waypoint loaded
        for i in range(4):
            await omni.kit.app.get_app().next_update_async()

        WaypointPereference._set_setting_with_key(SETTINGS_WAYPOINT_CAPTURE_DISABLED, "Sunstudy Settings", True)
        WaypointPereference._set_setting_with_key(SETTINGS_WAYPOINT_RECALL_DISABLED, "Sunstudy Settings", True)

        stage = self._context.get_stage()

        # case 1: Change the Sunstudy date attribute value under the Environment prim to trigger dirty
        wp = self._ext.get_waypoint("Waypoint_1")
        self._ext.begin_edit_waypoint(wp)
        # Now the waypoint data is in sync with the stage data
        self.assertFalse(wp.is_dirty)

        date_attr = stage.GetPropertyAtPath(EnvironmentProperties.DATE)
        if date_attr and date_attr.Get():
            date = date_attr.Get()
            date = date[:-1] + "x"  # illegal data
            date_attr.Set(date)
        await omni.kit.app.get_app().next_update_async()

        # Now the waypoint data should be dirty, i.e. out of sync with the stage data
        self.assertTrue(wp.is_dirty)
        self._ext.end_edit_waypoint(wp, False)

        # case 2: remove the time:current attribute to trigger the is_dirty
        wp = self._ext.get_waypoint("Waypoint_1")
        self._ext.begin_edit_waypoint(wp)

        time_attr = stage.GetPropertyAtPath(EnvironmentProperties.TIME_CURRENT)
        env_prim = time_attr.GetPrim()
        env_prim.RemoveProperty(time_attr.GetName())

        await omni.kit.app.get_app().next_update_async()
        self.assertTrue(wp.is_dirty)

        self._ext.end_edit_waypoint(wp, False)

        # case 3: change the time:current attribute value to trigger the is_dirty
        wp = self._ext.get_waypoint("Waypoint_1")
        self._ext.begin_edit_waypoint(wp)

        # Now the waypoint data is in sync with the stage data
        self.assertFalse(wp.is_dirty)

        time_attr = stage.GetPropertyAtPath(EnvironmentProperties.TIME_CURRENT)
        if time_attr:
            time_attr.Set(time_attr.Get() + 1.0)
            await omni.kit.app.get_app().next_update_async()
            self.assertTrue(wp.is_dirty)

        self._ext.end_edit_waypoint(wp, False)

        # case 4: change the location(location:longitude) attribute value to trigger the is_dirty
        wp = self._ext.get_waypoint("Waypoint_1")
        self._ext.begin_edit_waypoint(wp)

        # Now the waypoint data is in sync with the stage data
        self.assertFalse(wp.is_dirty)

        lngtd_attr = stage.GetPropertyAtPath(EnvironmentProperties.LONGITUDE)
        if lngtd_attr:
            lngtd_attr.Set(lngtd_attr.Get() + 1.0)
            await omni.kit.app.get_app().next_update_async()
            self.assertTrue(wp.is_dirty)

        self._ext.end_edit_waypoint(wp, False)

        # case 5: create an invalid waypoint
        wp_prim = stage.GetPrimAtPath("/Viewport_Waypoints/Waypoint_1")
        wp_prim.RemoveProperty(WAYPOINT_ATTR_SUNSTUDY)

        # creating the waypoint (read from USD to buffer) but the sunstudy attribute is removed
        self._ext._refresh_waypoints()

        wp = self._ext.get_waypoint("Waypoint_1")
        self._ext.begin_edit_waypoint(wp)

        # It's an invalid waypoint, so it should be false
        self.assertFalse(wp.is_dirty)

        # for an invalid waypoint, sunstudy setting's info is []
        sunstudy_setting = wp._waypoint_settings[3]
        self.assertEqual(sunstudy_setting.info, [])

        self._ext.end_edit_waypoint(wp, False)

    # OMFP-3471 trigger sunstudy dirty
    async def test_5_sunstudy_dirty_2(self):
        await self._context.open_stage_async(f"{TEST_DATA_PATH}/stage/cubes_no_waypoints.usda")
        await wait_stage_loading()

        # Wait for waypoint loaded
        for i in range(4):
            await omni.kit.app.get_app().next_update_async()

        WaypointPereference._set_setting_with_key(SETTINGS_WAYPOINT_CAPTURE_DISABLED, "Sunstudy Settings", True)
        WaypointPereference._set_setting_with_key(SETTINGS_WAYPOINT_RECALL_DISABLED, "Sunstudy Settings", True)

        stage = self._context.get_stage()

        # case 6: create a waypoint without sunstudy time then insert a time:current attribute under the Environment prim
        time_attr = stage.GetPropertyAtPath(EnvironmentProperties.TIME_CURRENT)
        env_prim = time_attr.GetPrim()
        env_prim.RemoveProperty(time_attr.GetName())

        await omni.kit.app.get_app().next_update_async()

        await self._ext.create_waypoint_async()
        self.assertEqual(len(self._ext.get_waypoints()), 1)

        # Test adding a time:current on the Environment prim to trigger dirty.
        wp = self._ext.get_waypoint("Waypoint_00")
        self._ext.begin_edit_waypoint(wp)
        self.assertFalse(wp.is_dirty)

        env_prim = stage.GetPrimAtPath(ENVIRONMENT_PRIM_ROOT)
        env_prim.CreateAttribute("time:current", Sdf.ValueTypeNames.Double, False).Set(160000.0)

        # It's an invalid waypoint, so it should be false
        self.assertTrue(wp.is_dirty)

        self._ext.end_edit_waypoint(wp, False)

    # OMFP-3472 Delete a prim and then recall the waypoint to create the prim back and set the attributes
    async def test_6_sunstudy_recall(self):
        await self._context.open_stage_async(f"{TEST_DATA_PATH}/stage/cubes_with_waypoints.usda")
        await wait_stage_loading()

        # Wait for waypoint loaded
        for i in range(4):
            await omni.kit.app.get_app().next_update_async()

        WaypointPereference._set_setting_with_key(SETTINGS_WAYPOINT_CAPTURE_DISABLED, "Sunstudy Settings", True)
        WaypointPereference._set_setting_with_key(SETTINGS_WAYPOINT_RECALL_DISABLED, "Sunstudy Settings", True)

        wp = self._ext.get_waypoint("Waypoint_1")

        stage = self._context.get_stage()
        stage.RemovePrim(ENVIRONMENT_PRIM_ROOT)
        await omni.kit.app.get_app().next_update_async()

        wp.recall()
        await omni.kit.app.get_app().next_update_async()

        env_prim = stage.GetPrimAtPath(ENVIRONMENT_PRIM_ROOT)
        self.assertTrue(env_prim.IsValid())

    async def test_7_equal_data(self):
        from omni.kit.waypoint.core.settings import AbstractWaypointSetting

        self.assertFalse(AbstractWaypointSetting.equal_data(1, 2))
        self.assertFalse(AbstractWaypointSetting.equal_data(1, "1"))
        self.assertFalse(AbstractWaypointSetting.equal_data([1, 2], [1, 2, 3]))
        self.assertFalse(AbstractWaypointSetting.equal_data([1, 2], [1, 3]))
        self.assertTrue(AbstractWaypointSetting.equal_data([1, 2, 3], [1, 2, 3]))
        self.assertTrue(AbstractWaypointSetting.equal_data((1, 2, 3), (1, 2, 3)))

    async def test_8_thumbnail_aspect(self):
        from omni.kit.waypoint.core.settings import ThumbnailSetting
        from omni.kit.waypoint.core.settings.thumbnail import THUMBNAIL_SIZE

        setting = ThumbnailSetting()
        thumbnail_aspect = float(THUMBNAIL_SIZE[0]) / THUMBNAIL_SIZE[1]
        viewport_api = get_active_viewport()

        # cover codepath ThumbnailSetting._on_viewport_captured() with a larger aspect ratio
        res_x = 180
        res_y = 90
        viewport_api.resolution = res_x, res_y
        self.assertGreater(float(res_x) / res_y, thumbnail_aspect)
        await setting.get_raw_data_async()

        # cover codepath ThumbnailSetting._on_viewport_captured() with a smaller aspect ratio
        res_x = 160
        res_y = 100
        viewport_api.resolution = res_x, res_y
        self.assertLess(float(res_x) / res_y, thumbnail_aspect)
        await setting.get_raw_data_async()

    async def _create_test_usd(self):
        await omni.usd.get_context().new_stage_async()
        return omni.usd.get_context().get_stage()

    async def _create_camera(self, camera_path):
        omni.kit.commands.execute("CreatePrimWithDefaultXform", prim_type="Camera", prim_path=camera_path)
        stage = omni.usd.get_context().get_stage()
        self.assertIsNotNone(stage.GetPrimAtPath(camera_path))
        return stage.GetPrimAtPath(camera_path)

    def _get_active_camera(self):
        viewport_api = get_active_viewport()
        stage = omni.usd.get_context().get_stage()
        return stage.GetPrimAtPath(viewport_api.camera_path)

    def _get_attr(self, prim, name):
        self.assertIsNotNone(prim)
        for attr in prim.GetAttributes():
            if name == attr.GetName():
                return attr
        return None

    async def test_9_delete_active_camera(self):
        stage = await self._create_test_usd()
        self.assertIsNotNone(stage)
        await omni.usd.get_context().attach_stage_async(stage)

        # create a new camera and set it as active camera
        camera_path = "/camera"
        await self._create_camera(camera_path)
        viewport_api = get_active_viewport()
        viewport_api.camera_path = camera_path
        active_camera = self._get_active_camera()

        # create waypoint
        await self._ext.create_waypoint_async()
        self.assertEqual(len(self._ext.get_waypoints()), 1)
        self._ext.current_waypoint = None

        # the waypoint's camera should have the same name as camera we created
        wp = self._ext.get_waypoint("Waypoint_00")
        self.assertIsNotNone(wp)
        self.assertEqual("/Viewport_Waypoints/Waypoint_00/camera", wp.camera_prim.GetPath())

        # delete the camera, set `OmniverseKit_Persp` as active one
        viewport_api.camera_path = "/OmniverseKit_Persp"
        omni.kit.commands.execute("DeletePrims", paths=[camera_path])
        self.assertFalse(stage.GetPrimAtPath(camera_path).IsValid())

        # recall the waypoint
        self._ext.recall_waypoint(wp)
        self._ext.current_waypoint = None

        # find one attribute
        BACKUP_ATTR_NAME = "clippingRange"
        backup_attr_value = None
        active_camera = self._get_active_camera()
        edit_context = Usd.EditContext(stage, Usd.EditTarget(stage.GetSessionLayer()))
        with edit_context:
            # backup value, then alter it
            attr = self._get_attr(active_camera, BACKUP_ATTR_NAME)
            self.assertIsNotNone(attr)
            backup_attr_value = attr.Get()
            new_attr_value = backup_attr_value + Gf.Vec2f(123, 456)
            attr.Set(new_attr_value)
        self.assertIsNotNone(backup_attr_value)

        # delete waypoint's camera, it's unlikely bot possible
        omni.kit.commands.execute("DeletePrims", paths=[wp.camera_prim.GetPath()])
        self.assertFalse(stage.GetPrimAtPath(wp.camera_prim.GetPath()).IsValid())

        # recall waypoint
        self._ext.recall_waypoint(wp)
        self._ext.current_waypoint = None

        # if camera of waypoint was deleted, recall waypoint should not update Perp camera attr
        attr = self._get_attr(active_camera, BACKUP_ATTR_NAME)
        self.assertIsNotNone(attr)
        self.assertEqual(new_attr_value, attr.Get())

        await omni.usd.get_context().close_stage_async()

    async def test_10_add_and_delete_camera_attr(self):
        stage = await self._create_test_usd()
        self.assertIsNotNone(stage)
        await omni.usd.get_context().attach_stage_async(stage)

        # create waypoint
        await self._ext.create_waypoint_async()
        self.assertEqual(len(self._ext.get_waypoints()), 1)
        self._ext.current_waypoint = None

        wp = self._ext.get_waypoint("Waypoint_00")
        self.assertIsNotNone(wp)
        self.assertEqual("/Viewport_Waypoints/Waypoint_00/OmniverseKit_Persp", wp.camera_prim.GetPath())

        # add new attribute to waypoint's camera setting
        ATTR_NAME = "test_attr"
        attr = wp.camera_prim.CreateAttribute(ATTR_NAME, Sdf.ValueTypeNames.Bool)
        attr.Set(True)

        # make sure the attribute we created dosen't exist in active camera
        active_camera = self._get_active_camera()
        attr = self._get_attr(active_camera, ATTR_NAME)
        self.assertIsNone(attr)

        # recall the waypoint
        self._ext.recall_waypoint(wp)
        self._ext.current_waypoint = None

        edit_context = Usd.EditContext(stage, Usd.EditTarget(stage.GetSessionLayer()))
        with edit_context:
            # after recalling, we can the attribute in active camera;
            # now we set it to false
            attr = self._get_attr(active_camera, ATTR_NAME)
            self.assertIsNotNone(attr)
            attr.Set(False)

        # remove the attribute of waypoint's camera
        self.assertTrue(wp.camera_prim.RemoveProperty(ATTR_NAME))
        self.assertFalse(wp.camera_prim.HasAttribute(ATTR_NAME))

        self._ext.recall_waypoint(wp)
        self._ext.current_waypoint = None

        attr = self._get_attr(active_camera, ATTR_NAME)
        self.assertIsNotNone(attr)
        # after we once again recall it, the attribute of active
        # camera should remain the same
        self.assertFalse(attr.Get())

        await omni.usd.get_context().close_stage_async()

    async def test_11_rename_camera_attr(self):
        stage = await self._create_test_usd()
        self.assertIsNotNone(stage)
        await omni.usd.get_context().attach_stage_async(stage)

        # create waypoint
        await self._ext.create_waypoint_async()
        self.assertEqual(len(self._ext.get_waypoints()), 1)
        self._ext.current_waypoint = None

        wp = self._ext.get_waypoint("Waypoint_00")
        self.assertIsNotNone(wp)
        self.assertEqual("/Viewport_Waypoints/Waypoint_00/OmniverseKit_Persp", wp.camera_prim.GetPath())

        OLD_ATTR_NAME = "old_test_attr"
        NEW_ATTR_NAME = "new_test_attr"
        # add an attr to camera setting
        attr = wp.camera_prim.CreateAttribute(OLD_ATTR_NAME, Sdf.ValueTypeNames.Bool)
        attr.Set(True)
        old_value = attr.Get()
        active_camera = self._get_active_camera()
        attr = self._get_attr(active_camera, OLD_ATTR_NAME)
        self.assertIsNone(attr)

        # recall the waypoint
        self._ext.recall_waypoint(wp)
        self._ext.current_waypoint = None

        # the attribute we added should be in active camera also
        attr = self._get_attr(active_camera, OLD_ATTR_NAME)
        self.assertIsNotNone(attr)

        # then rename(delete->create) the attribute
        self.assertTrue(wp.camera_prim.RemoveProperty(OLD_ATTR_NAME))
        attr = wp.camera_prim.CreateAttribute(NEW_ATTR_NAME, Sdf.ValueTypeNames.Bool)
        attr.Set(old_value)

        self._ext.recall_waypoint(wp)
        self._ext.current_waypoint = None

        # both attributes should exist after recall after recalling
        attr = self._get_attr(active_camera, NEW_ATTR_NAME)
        self.assertIsNotNone(attr)
        self.assertIsNotNone(self._get_attr(active_camera, OLD_ATTR_NAME))
        self.assertTrue(attr.Get())

        await omni.usd.get_context().close_stage_async()

    async def test_12_locked_active_camera(self):
        LOCK_CAMERA_ATTR = "omni:kit:cameraLock"
        stage = await self._create_test_usd()
        self.assertIsNotNone(stage)
        await omni.usd.get_context().attach_stage_async(stage)

        # lock active camera
        active_camera = self._get_active_camera()
        if active_camera.HasAttribute(LOCK_CAMERA_ATTR):
            attr = self._get_attr(active_camera, LOCK_CAMERA_ATTR)
        else:
            attr = active_camera.CreateAttribute(LOCK_CAMERA_ATTR, Sdf.ValueTypeNames.Bool)
        attr.Set(True)
        self.assertTrue(attr.Get())

        # create waypoint
        await self._ext.create_waypoint_async()
        self.assertEqual(len(self._ext.get_waypoints()), 1)
        self._ext.current_waypoint = None

        wp = self._ext.get_waypoint("Waypoint_00")
        self.assertIsNotNone(wp)
        self.assertEqual("/Viewport_Waypoints/Waypoint_00/OmniverseKit_Persp", wp.camera_prim.GetPath())

        def assert_wp_lock_false():
            self.assertTrue(wp.camera_prim.HasAttribute(LOCK_CAMERA_ATTR))
            self.assertFalse(wp.camera_prim.GetProperty(LOCK_CAMERA_ATTR).Get())

        # we expect a waypoint camera setting is not locked
        assert_wp_lock_false()

        self._ext.recall_waypoint(wp)
        self._ext.current_waypoint = None
        assert_wp_lock_false()

        edit_context = Usd.EditContext(stage, Usd.EditTarget(stage.GetSessionLayer()))
        with edit_context:
            # if we recall the waypoint, active camera is not locked either
            self.assertFalse(attr.Get())
            attr.Set(True)
            self.assertTrue(attr.Get())

        await omni.usd.get_context().close_stage_async()

    async def test_13_thumbnail_path(self):
        stage = await self._create_test_usd()
        self.assertIsNotNone(stage)
        await omni.usd.get_context().attach_stage_async(stage)

        temp_dir = tempfile.mkdtemp()
        self._ext.waypoint_thumbnail_path = temp_dir

        # create waypoint
        await self._ext.create_waypoint_async()
        waypoint = self._ext.get_waypoint("Waypoint_00")
        self.assertIsNotNone(waypoint.thumbnail_data)
        if waypoint.thumbnail:
            self.assertTrue(os.path.exists(waypoint.thumbnail))

        shutil.rmtree(temp_dir)

    async def test_14_skip_camera_exposure_attrs(self):
        stage = await self._create_test_usd()
        self.assertIsNotNone(stage)
        await omni.usd.get_context().attach_stage_async(stage)

        active_camera = self._get_active_camera()
        self.assertIsNotNone(active_camera)
        f_stop_attr = self._get_attr(active_camera, "fStop")
        self.assertIsNotNone(f_stop_attr)
        original_f_stop = f_stop_attr.Get()
        exposure_attr_name = "exposure:fStop"

        edit_context = Usd.EditContext(stage, Usd.EditTarget(stage.GetSessionLayer()))
        with edit_context:
            exposure_attr = active_camera.CreateAttribute(exposure_attr_name, Sdf.ValueTypeNames.Float)
            exposure_attr.Set(123.0)

        await self._ext.create_waypoint_async()
        self.assertEqual(len(self._ext.get_waypoints()), 1)
        self._ext.current_waypoint = None

        wp = self._ext.get_waypoint("Waypoint_00")
        self.assertIsNotNone(wp)
        self.assertFalse(wp.camera_prim.HasAttribute("fStop"))
        self.assertFalse(wp.camera_prim.HasAttribute(exposure_attr_name))

        current_f_stop = original_f_stop + 2.0
        current_exposure_f_stop = 321.0
        with edit_context:
            f_stop_attr.Set(current_f_stop)
            active_camera.CreateAttribute(exposure_attr_name, Sdf.ValueTypeNames.Float).Set(current_exposure_f_stop)
            wp.camera_prim.CreateAttribute("fStop", Sdf.ValueTypeNames.Float).Set(original_f_stop + 10.0)
            wp.camera_prim.CreateAttribute(exposure_attr_name, Sdf.ValueTypeNames.Float).Set(456.0)

        self._ext.recall_waypoint(wp)
        self._ext.current_waypoint = None

        self.assertEqual(self._get_attr(active_camera, "fStop").Get(), current_f_stop)
        self.assertEqual(active_camera.GetAttribute(exposure_attr_name).Get(), current_exposure_f_stop)

        await omni.usd.get_context().close_stage_async()
