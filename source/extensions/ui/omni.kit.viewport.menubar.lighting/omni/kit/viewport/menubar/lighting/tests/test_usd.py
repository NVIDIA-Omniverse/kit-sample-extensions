# Copyright (c) 2021-2022, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

from pathlib import Path

import carb
import omni.kit
import omni.usd
from omni.kit.test import AsyncTestCase
from omni.kit.viewport.menubar.lighting.utility import (
    RefCountedUsdContextSub,
    _make_light_mode_setting_key,
    stage_has_api_type,
)
from pxr import Gf, Usd, UsdGeom, UsdLux

EXT_TEST_PATH = Path(carb.tokens.get_tokens_interface().resolve("${omni.kit.viewport.menubar.lighting}")).absolute()
TEST_USD_PATH = EXT_TEST_PATH.joinpath("data", "tests", "scenes")


class TestLightingMenuUsd(AsyncTestCase):
    async def setUp(self):
        super().setUp()
        self.__usd_context = omni.usd.get_context()

    async def tearDown(self):
        super().tearDown()

    async def __wait_frames(self, n_frames: int = 5):
        app = omni.kit.app.get_app()
        for _ in range(n_frames):
            await app.next_update_async()

    async def test_light_discovery(self):
        """Test light discovery."""

        # Ned to force autoLightRig enabled off so tests of backend work
        settings = carb.settings.get_settings()
        settings.set("/persistent/exts/omni.kit.viewport.menubar.lighting/autoLightRig/enabled", False)
        light_mode_key = _make_light_mode_setting_key(self.__usd_context)
        settings.set(light_mode_key, "")

        try:
            usd_path = TEST_USD_PATH.joinpath(f"no_lights.usda")
            await self.__usd_context.open_stage_async(str(usd_path))
            self.assertFalse(
                stage_has_api_type(self.__usd_context.get_stage(), UsdLux.LightAPI),
                msg=f'stage_has_prim_type should have reported no lights found in "{str(usd_path)}"',
            )

            for scene in ("a", "b", "c", "d", "e", "f"):
                usd_path = TEST_USD_PATH.joinpath(f"{scene}.usda")
                await self.__usd_context.open_stage_async(str(usd_path))

                self.assertTrue(
                    stage_has_api_type(self.__usd_context.get_stage(), UsdLux.LightAPI),
                    msg=f'stage_has_prim_type should have reported lights found in "{str(usd_path)}"',
                )

            usd_path = TEST_USD_PATH.joinpath(f"light_outside_default_prim.usda")
            await self.__usd_context.open_stage_async(str(usd_path))

            # Traversal from defaultPrim should be false (light is outside of it)
            self.assertFalse(
                stage_has_api_type(self.__usd_context.get_stage(), UsdLux.LightAPI, True),
                msg=f'stage_has_prim_type should have reported no lights found in "{str(usd_path)}"',
            )

            # Traversal from absolute-root should be True
            self.assertTrue(
                stage_has_api_type(self.__usd_context.get_stage(), UsdLux.LightAPI, False),
                msg=f'stage_has_prim_type should have reported a light found in "{str(usd_path)}"',
            )

            usd_path = TEST_USD_PATH.joinpath(f"light_outside_default_prim_nested.usda")
            await self.__usd_context.open_stage_async(str(usd_path))

            # Traversal from defaultPrim should be false (light is outside of it)
            self.assertFalse(
                stage_has_api_type(self.__usd_context.get_stage(), UsdLux.LightAPI, True),
                msg=f'stage_has_prim_type should have reported no lights found in "{str(usd_path)}"',
            )

            # Traversal from absolute-root should be True even if nested outside defaultPrim
            self.assertTrue(
                stage_has_api_type(self.__usd_context.get_stage(), UsdLux.LightAPI, False),
                msg=f'stage_has_prim_type should have reported a light found in "{str(usd_path)}"',
            )
        finally:
            settings.set("/persistent/exts/omni.kit.viewport.menubar.lighting/autoLightRig/enabled", True)

    async def test_rig_applied(self):
        """Test proper rig was applied to stage with no lights."""

        # Ned to force autoLightRig enabled off so tests of backend work
        settings = carb.settings.get_settings()
        settings.set("/persistent/exts/omni.kit.viewport.menubar.lighting/autoLightRig/enabled", False)

        try:
            settings.set("/persistent/exts/omni.kit.viewport.menubar.lighting/autoLightRig/enabled", False)

            usd_path = TEST_USD_PATH.joinpath(f"no_lights.usda")
            await self.__usd_context.open_stage_async(str(usd_path))
            await self.__wait_frames()
            light_mode_key = _make_light_mode_setting_key(self.__usd_context)
            # Nothing should have been applied
            self.assertEqual(settings.get(light_mode_key), "")

            settings.set("/persistent/exts/omni.kit.viewport.menubar.lighting/autoLightRig/enabled", True)
            settings.set("/exts/omni.kit.viewport.menubar.lighting/preserveActiveRig", False)

            usd_path = TEST_USD_PATH.joinpath(f"no_lights.usda")
            await self.__usd_context.open_stage_async(str(usd_path))
            await self.__wait_frames()
            light_mode_key = _make_light_mode_setting_key(self.__usd_context)
            # Default rig should have been applied
            self.assertEqual(settings.get(light_mode_key), "Default")

            settings.set(light_mode_key, "Colored Lights")
            settings.set("/exts/omni.kit.viewport.menubar.lighting/preserveActiveRig", True)
            await self.__usd_context.open_stage_async(str(usd_path))
            await self.__wait_frames()
            light_mode_key = _make_light_mode_setting_key(self.__usd_context)
            # Should have preserved currently active rig
            self.assertEqual(settings.get(light_mode_key), "Colored Lights")

            settings.set("/exts/omni.kit.viewport.menubar.lighting/preserveActiveRig", False)

            usd_path = TEST_USD_PATH.joinpath(f"no_lights.usda")
            await self.__usd_context.open_stage_async(str(usd_path))
            await self.__wait_frames()
            light_mode_key = _make_light_mode_setting_key(self.__usd_context)
            # Default rig should have been applied
            self.assertEqual(settings.get(light_mode_key), "Default")

        finally:
            settings.set("/persistent/exts/omni.kit.viewport.menubar.lighting/autoLightRig/enabled", True)
            settings.set("/exts/omni.kit.viewport.menubar.lighting/preserveActiveRig", True)

    async def test_ref_counted_context_sub(self):
        """Test RefCountedUsdContextSub gets called once for multiple registration on a UsdContext name"""
        usd_context_name = "test_ref_counted_context_sub"
        usd_context = omni.usd.create_context(usd_context_name)
        try:
            counter = 0

            def callback(usd_context, *args, **kwargs):
                self.assertIsNotNone(usd_context)
                nonlocal counter
                counter = counter + 1

            subs = [RefCountedUsdContextSub(usd_context_name, callback) for _ in range(10)]

            usd_path = TEST_USD_PATH.joinpath("no_lights.usda")
            await usd_context.open_stage_async(str(usd_path))
            self.assertEqual(counter, 1)

            # Test implicit destruction of all subscribtions
            del subs
            await usd_context.open_stage_async(str(usd_path))
            # Should stay at 1, no more callbacks
            self.assertEqual(counter, 1)

            subs = [RefCountedUsdContextSub(usd_context_name, callback) for _ in range(10)]
            # Should get incremented to 2, stage is open already
            self.assertEqual(counter, 2)
            # Test explicit destruction of all subscribtions
            for sub in subs:
                sub.destroy()
            del subs

            await usd_context.open_stage_async(str(usd_path))
            # Should stay at 2, no more callbacks
            self.assertEqual(counter, 2)

        finally:
            omni.usd.destroy_context(usd_context_name)

    async def test_ambient_reset(self):
        """Test RTX ambient factor is reset to 0"""
        settings = carb.settings.get_settings()
        ambadjust_key = "/exts/omni.kit.viewport.menubar.lighting/ambientAdjust"
        rtx_amb_key = "/rtx/sceneDb/ambientLightIntensity"

        try:
            settings.set(rtx_amb_key, 1)
            await self.__wait_frames()
            await omni.usd.get_context().new_stage_async()
            self.assertEqual(settings.get(rtx_amb_key), 1)
            await self.__wait_frames()

            settings.set(ambadjust_key, "newscene")
            await self.__wait_frames()
            await omni.usd.get_context().new_stage_async()
            await self.__wait_frames()
            self.assertEqual(settings.get(rtx_amb_key), 0)

            # no lights, and no meta-data should be newscene too
            settings.set(rtx_amb_key, 1)
            await self.__wait_frames()
            usd_path = TEST_USD_PATH.joinpath("ambient_adjust", "no_light.usda")
            await self.__usd_context.open_stage_async(str(usd_path))
            await self.__wait_frames()
            self.assertEqual(settings.get(rtx_amb_key), 0)

            # no lights with metadata, not a newscene
            settings.set(rtx_amb_key, 10)
            await self.__wait_frames()
            usd_path = TEST_USD_PATH.joinpath("ambient_adjust", "no_light_with_amb.usda")
            await self.__usd_context.open_stage_async(str(usd_path))
            # Test the Usd.Stage render-settings meta-data hasn't been touched
            stage_md = self.__usd_context.get_stage().GetMetadataByDictKey("customLayerData", "renderSettings")
            self.assertEqual(stage_md.get("rtx:sceneDb:ambientLightIntensity"), 2)
            # Test the carb-setting hasn't been touched either
            self.assertEqual(settings.get(rtx_amb_key), 10)

            settings.set(rtx_amb_key, 1)
            settings.set(ambadjust_key, "nolights")
            await self.__wait_frames()
            usd_path = TEST_USD_PATH.joinpath("ambient_adjust", "no_light_with_amb.usda")
            await self.__usd_context.open_stage_async(str(usd_path))
            await self.__wait_frames()
            self.assertEqual(settings.get(rtx_amb_key), 0)

            settings.set(rtx_amb_key, 20)
            await self.__wait_frames()
            usd_path = TEST_USD_PATH.joinpath("ambient_adjust", "one_light_with_amb.usda")
            await self.__usd_context.open_stage_async(str(usd_path))
            await self.__wait_frames()
            # Test the Usd.Stage render-settings meta-data hasn't been touched
            stage_md = self.__usd_context.get_stage().GetMetadataByDictKey("customLayerData", "renderSettings")
            self.assertEqual(stage_md.get("rtx:sceneDb:ambientLightIntensity"), 4)
            # Test the carb-setting hasn't been touched either
            self.assertEqual(settings.get(rtx_amb_key), 20)

            settings.set(rtx_amb_key, 1)
            settings.set(ambadjust_key, "rigapplied")
            await self.__wait_frames()
            usd_path = TEST_USD_PATH.joinpath("ambient_adjust", "no_light_with_amb.usda")
            await self.__usd_context.open_stage_async(str(usd_path))
            await self.__wait_frames()
            self.assertEqual(settings.get(rtx_amb_key), 0)

        finally:
            settings.set(rtx_amb_key, None)
            settings.set(ambadjust_key, "")

    async def __test_back_to_stage_light(self, cmd_name: str, light_type: str):
        """Test adding a light will revert back to stage lighting"""

        settings = carb.settings.get_settings()
        usd_context = self.__usd_context
        usd_path = TEST_USD_PATH.joinpath("no_lights.usda")
        await usd_context.open_stage_async(str(usd_path))
        await self.__wait_frames()

        light_mode_key = _make_light_mode_setting_key(self.__usd_context)

        # Should have a rig applied
        self.assertEqual(settings.get(light_mode_key), "Default")

        omni.kit.commands.execute(cmd_name, prim_path="/World/Light", prim_type=light_type)
        await self.__wait_frames()

        # Should be back to stage lights
        self.assertEqual(settings.get(light_mode_key), "")

    async def test_back_to_stage_light_create_prim(self):
        """Test adding a light will revert back to stage lighting from CreatePrim command"""
        await self.__test_back_to_stage_light("CreatePrim", "DistantLight")

    async def test_back_to_stage_light_create_prim_with_default_xform(self):
        """Test adding a light will revert back to stage lighting from CreatePrimWithDefaultXform command"""
        await self.__test_back_to_stage_light("CreatePrimWithDefaultXform", "SphereLight")

    async def __run_stage_rig_up_test(self, stage_up, set_lighting_mode_rig):
        await self.__usd_context.new_stage_async()
        stage = self.__usd_context.get_stage()
        UsdGeom.SetStageUpAxis(stage, stage_up)
        rig_prim_path = "/OmniKit_Viewport_LightRig"

        y_order, z_order = [], ["xformOp:transform"]
        if stage_up == UsdGeom.Tokens.z:
            y_order, z_order = z_order, y_order

        set_lighting_mode_rig.execute("Y Up Rig")
        light_rig_prim = stage.GetPrimAtPath(rig_prim_path)
        self.assertTrue(light_rig_prim.IsValid())

        xformable = UsdGeom.Xformable(light_rig_prim)
        op_order = xformable.GetXformOpOrderAttr().Get()
        self.assertEqual(op_order, y_order)

        set_lighting_mode_rig.execute("Z Up Rig")
        light_rig_prim = stage.GetPrimAtPath(rig_prim_path)
        self.assertTrue(light_rig_prim.IsValid())

        xformable = UsdGeom.Xformable(light_rig_prim)
        op_order = xformable.GetXformOpOrderAttr().Get()
        self.assertEqual(op_order, z_order)

    async def test_stage_rig_up_axis_application(self):
        """Test adding rigs with different up-axis than stage"""
        settings = carb.settings.get_settings()
        rigs_key = "/exts/omni.kit.viewport.menubar.lighting/rigs"
        dflt_value = settings.get(rigs_key)
        settings.set(rigs_key, "${omni.kit.viewport.menubar.lighting}/data/tests/scenes/up_axis_rigs")
        await self.__wait_frames()

        ar = omni.kit.actions.core.get_action_registry()
        set_lighting_mode_rig = ar.get_action("omni.kit.viewport.menubar.lighting", "set_lighting_mode_rig")

        try:
            await self.__run_stage_rig_up_test(UsdGeom.Tokens.y, set_lighting_mode_rig)
            await self.__run_stage_rig_up_test(UsdGeom.Tokens.z, set_lighting_mode_rig)
        finally:
            # Restore to default light-rig path for rest of tests
            settings.set(rigs_key, dflt_value)
            await self.__wait_frames()
            set_lighting_mode_rig.execute(-1)
