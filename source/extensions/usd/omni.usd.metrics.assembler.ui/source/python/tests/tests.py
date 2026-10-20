# SPDX-FileCopyrightText: Copyright (c) 2022-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

import os

import carb.settings
import omni.kit.app
import omni.kit.test
import omni.kit.ui_test as ui_test
import omni.metrics.assembler.core.bindings._metricsAssembler as metricsAssembler
import omni.usd
from omni.metrics.assembler.core import get_metrics_assembler_interface
from omni.metrics.assembler.ui.constants import METRICS_ASSEMBLER_HUD_SETTING_SUFFIX
from omni.metrics.assembler.ui.settings import MetricsAssemblerMode
from omni.metrics.assembler.ui.tools import get_per_viewport_setting_path
from pxr import Gf, Plug, Sdf, Tf, Usd, UsdGeom, UsdPhysics, UsdUtils

TOLERANCE = 1e-3


class MetricsAssemblerUITests(omni.kit.test.AsyncTestCase):
    async def setUp(self):
        self._id = get_metrics_assembler_interface().register_custom_resolve_rule(
            UsdPhysics.Tokens.physicsDensity, -3, 1
        )
        pass

    async def tearDown(self):
        get_metrics_assembler_interface().unregister_custom_resolve_rule(self._id)
        pass

    def get_data_folder(self):
        data_folder = os.path.abspath(os.path.normpath(os.path.join(__file__, "../../../../../../data/tests/")))
        data_folder = data_folder.replace("\\", "/") + "/"
        return data_folder

    def setup_stage(self, stage, mpu):
        cache = UsdUtils.StageCache.Get()
        cache.Insert(stage)
        stage_id = cache.GetId(stage).ToLongInt()
        UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.y)
        UsdGeom.SetStageMetersPerUnit(stage, mpu)
        return stage_id

    async def new_stage(self):
        # Workaround for Kit event loop issues
        for _ in range(5):
            await omni.kit.app.get_app().next_update_async()
        await omni.kit.stage_templates.new_stage_async()
        for _ in range(5):
            await omni.kit.app.get_app().next_update_async()
        stage = omni.usd.get_context().get_stage()
        return stage

    def check_resolve(self, stage, ref_path, expected_scale=Gf.Vec3d(0.01), expected_density=60 * 100 * 100 * 100):
        cube_physics_cm_prim = stage.GetPrimAtPath("/World/" + ref_path)

        if expected_scale is not None:
            units_resolve_attr = cube_physics_cm_prim.GetAttribute("xformOp:scale:unitsResolve")
            self.assertTrue(units_resolve_attr)

            scale = units_resolve_attr.Get()
            self.assertTrue(Gf.IsClose(scale, expected_scale, 0.02))

        material_physics_prim = stage.GetPrimAtPath("/World/" + ref_path + "/PhysicsMaterial")
        density_attr = material_physics_prim.GetAttribute(UsdPhysics.Tokens.physicsDensity)
        self.assertTrue(density_attr)
        density = density_attr.Get()
        self.assertTrue(abs(density - expected_density) < 0.2)

    def check_metadata(self, stage, paths):
        metrics_assembler_dict = stage.GetMetadataByDictKey("customLayerData", "metricsAssembler")

        self.assertTrue(metrics_assembler_dict)
        if metrics_assembler_dict is None:
            return

        version = metrics_assembler_dict.get("version")
        self.assertTrue(version == int(1))

        self.assertTrue(len(metrics_assembler_dict) == len(paths) + 1)

        for path in paths:
            self.assertTrue(metrics_assembler_dict.get(str(path)))

    async def test_scene_resolve(self):
        stage = Usd.Stage.CreateInMemory()
        stage_id = self.setup_stage(stage, 1.0)

        data_folder = self.get_data_folder()

        xform = UsdGeom.Xform.Define(stage, "/World/" + "cube_physics_cm")
        xform.GetPrim().GetReferences().AddReference(data_folder + "cube_physics_cm" + ".usda")

        divergent_stage = get_metrics_assembler_interface().resolve_stage(stage_id)
        self.assertTrue(divergent_stage)

        self.check_resolve(stage, "cube_physics_cm")

    async def test_add_reference(self):
        await self.new_stage()
        stage = omni.usd.get_context().get_stage()
        stage_id = self.setup_stage(stage, 1.0)

        xform = UsdGeom.Xform.Define(stage, "/World/" + "cube_physics_cm")
        data_folder = self.get_data_folder()
        reference = data_folder + "cube_physics_cm" + ".usda"
        payref = Sdf.Reference(reference.replace("\\", "/"))
        omni.kit.commands.execute("AddReference", stage=stage, prim_path=xform.GetPath(), reference=payref)

        for _ in range(5):
            await omni.kit.app.get_app().next_update_async()

        self.check_resolve(stage, "cube_physics_cm")
        self.check_metadata(stage, [xform.GetPath()])
        await self.new_stage()

    async def test_add_reference_existing_childs(self):
        await self.new_stage()
        stage = omni.usd.get_context().get_stage()
        stage_id = self.setup_stage(stage, 1.0)

        xform = UsdGeom.Xform.Define(stage, "/World/" + "cube_physics_cm")
        UsdGeom.Sphere.Define(stage, "/World/" + "cube_physics_cm/sphere")
        data_folder = self.get_data_folder()
        reference = data_folder + "cube_physics_cm" + ".usda"
        payref = Sdf.Reference(reference.replace("\\", "/"))
        omni.kit.commands.execute("AddReference", stage=stage, prim_path=xform.GetPath(), reference=payref)

        for _ in range(5):
            await omni.kit.app.get_app().next_update_async()

        self.check_resolve(stage, "cube_physics_cm", expected_scale=None, expected_density=60)

        metrics_assembler_dict = stage.GetMetadataByDictKey("customLayerData", "metricsAssembler")
        self.assertTrue(not metrics_assembler_dict)

        await self.new_stage()

    async def test_add_reference_existing_reference(self):
        await self.new_stage()
        stage = omni.usd.get_context().get_stage()
        stage_id = self.setup_stage(stage, 1.0)

        xform = UsdGeom.Xform.Define(stage, "/World/" + "cube_physics_cm")
        data_folder = self.get_data_folder()
        reference = data_folder + "cube_physics_cm" + ".usda"
        payref = Sdf.Reference(reference.replace("\\", "/"))
        omni.kit.commands.execute("AddReference", stage=stage, prim_path=xform.GetPath(), reference=payref)

        for _ in range(5):
            await omni.kit.app.get_app().next_update_async()

        self.check_resolve(stage, "cube_physics_cm")
        self.check_metadata(stage, [xform.GetPath()])

        reference = data_folder + "cube_physics_mm" + ".usda"
        payref = Sdf.Reference(reference.replace("\\", "/"))
        omni.kit.commands.execute("AddReference", stage=stage, prim_path=xform.GetPath(), reference=payref)

        for _ in range(5):
            await omni.kit.app.get_app().next_update_async()

        self.check_resolve(stage, "cube_physics_cm")
        self.check_metadata(stage, [xform.GetPath()])

        await self.new_stage()

    async def test_add_payload(self):
        await self.new_stage()
        stage = omni.usd.get_context().get_stage()
        stage_id = self.setup_stage(stage, 1.0)

        xform = UsdGeom.Xform.Define(stage, "/World/" + "cube_physics_cm")
        data_folder = self.get_data_folder()
        reference = data_folder + "cube_physics_cm" + ".usda"
        payref = Sdf.Payload(reference.replace("\\", "/"))
        omni.kit.commands.execute("AddPayload", stage=stage, prim_path=xform.GetPath(), payload=payref)

        for _ in range(5):
            await omni.kit.app.get_app().next_update_async()

        self.check_resolve(stage, "cube_physics_cm")
        self.check_metadata(stage, [xform.GetPath()])
        await self.new_stage()

    async def test_add_payload_existing_childs(self):
        await self.new_stage()
        stage = omni.usd.get_context().get_stage()
        stage_id = self.setup_stage(stage, 1.0)

        xform = UsdGeom.Xform.Define(stage, "/World/" + "cube_physics_cm")
        UsdGeom.Sphere.Define(stage, "/World/" + "cube_physics_cm/sphere")
        data_folder = self.get_data_folder()
        reference = data_folder + "cube_physics_cm" + ".usda"
        payref = Sdf.Payload(reference.replace("\\", "/"))
        omni.kit.commands.execute("AddPayload", stage=stage, prim_path=xform.GetPath(), payload=payref)

        for _ in range(5):
            await omni.kit.app.get_app().next_update_async()

        self.check_resolve(stage, "cube_physics_cm", expected_scale=None, expected_density=60)

        metrics_assembler_dict = stage.GetMetadataByDictKey("customLayerData", "metricsAssembler")
        self.assertTrue(not metrics_assembler_dict)

        await self.new_stage()

    async def test_add_payload_existing_payload(self):
        await self.new_stage()
        stage = omni.usd.get_context().get_stage()
        stage_id = self.setup_stage(stage, 1.0)

        xform = UsdGeom.Xform.Define(stage, "/World/" + "cube_physics_cm")
        data_folder = self.get_data_folder()
        reference = data_folder + "cube_physics_cm" + ".usda"
        payref = Sdf.Payload(reference.replace("\\", "/"))
        omni.kit.commands.execute("AddPayload", stage=stage, prim_path=xform.GetPath(), payload=payref)

        for _ in range(5):
            await omni.kit.app.get_app().next_update_async()

        self.check_resolve(stage, "cube_physics_cm")
        self.check_metadata(stage, [xform.GetPath()])

        reference = data_folder + "cube_physics_mm" + ".usda"
        payref = Sdf.Payload(reference.replace("\\", "/"))
        omni.kit.commands.execute("AddPayload", stage=stage, prim_path=xform.GetPath(), payload=payref)

        for _ in range(5):
            await omni.kit.app.get_app().next_update_async()

        self.check_resolve(stage, "cube_physics_cm")
        self.check_metadata(stage, [xform.GetPath()])

        await self.new_stage()

    async def test_create_reference(self):
        await self.new_stage()
        stage = omni.usd.get_context().get_stage()
        stage_id = self.setup_stage(stage, 1.0)

        data_folder = self.get_data_folder()
        reference = data_folder + "cube_physics_cm" + ".usda"
        omni.kit.commands.execute(
            "CreateReference",
            usd_context=omni.usd.get_context(),
            path_to="/World/" + "cube_physics_cm",
            asset_path=reference.replace("\\", "/"),
            instanceable=False,
        )
        for _ in range(5):
            await omni.kit.app.get_app().next_update_async()

        self.check_resolve(stage, "cube_physics_cm")
        self.check_metadata(stage, ["/World/cube_physics_cm"])
        await self.new_stage()

    async def test_create_payload(self):
        await self.new_stage()
        stage = omni.usd.get_context().get_stage()
        stage_id = self.setup_stage(stage, 1.0)

        data_folder = self.get_data_folder()
        reference = data_folder + "cube_physics_cm" + ".usda"
        omni.kit.commands.execute(
            "CreatePayload",
            usd_context=omni.usd.get_context(),
            path_to="/World/" + "cube_physics_cm",
            asset_path=reference.replace("\\", "/"),
        )
        for _ in range(5):
            await omni.kit.app.get_app().next_update_async()

        self.check_resolve(stage, "cube_physics_cm")
        self.check_metadata(stage, ["/World/cube_physics_cm"])
        await self.new_stage()

    async def test_load_version_0_stage(self):
        data_folder = self.get_data_folder()
        scene_path = data_folder + "cube_physics_m_ref_cm_version0" + ".usda"
        await omni.usd.get_context().open_stage_async(scene_path)
        stage = omni.usd.get_context().get_stage()

        for _ in range(5):
            await omni.kit.app.get_app().next_update_async()

        self.check_resolve(stage, "cube_physics_cm")
        self.check_metadata(stage, ["/World/cube_physics_cm"])
        await self.new_stage()

    async def test_load_stage(self):
        data_folder = self.get_data_folder()
        scene_path = data_folder + "cube_physics_m_ref_cm" + ".usda"
        await omni.usd.get_context().open_stage_async(scene_path)
        stage = omni.usd.get_context().get_stage()

        for _ in range(5):
            await omni.kit.app.get_app().next_update_async()

        self.check_resolve(stage, "cube_physics_cm")
        self.check_metadata(stage, ["/World/cube_physics_cm"])
        await self.new_stage()

    async def test_load_stage_recursive(self):
        data_folder = self.get_data_folder()
        scene_path = data_folder + "cube_physics_cm_ref_m_ref_cm" + ".usda"
        await omni.usd.get_context().open_stage_async(scene_path)
        stage = omni.usd.get_context().get_stage()

        for _ in range(5):
            await omni.kit.app.get_app().next_update_async()

        self.check_resolve(stage, "cube_physics_m_ref_cm/cube_physics_cm", expected_scale=None, expected_density=60)
        self.check_metadata(stage, ["/World/cube_physics_m_ref_cm"])
        await self.new_stage()

    async def test_copy_prim(self):
        await self.new_stage()
        stage = omni.usd.get_context().get_stage()
        stage_id = self.setup_stage(stage, 1.0)

        data_folder = self.get_data_folder()
        reference = data_folder + "cube_physics_cm" + ".usda"
        omni.kit.commands.execute(
            "CreateReference",
            usd_context=omni.usd.get_context(),
            path_to="/World/" + "cube_physics_cm",
            asset_path=reference.replace("\\", "/"),
            instanceable=False,
        )
        for _ in range(5):
            await omni.kit.app.get_app().next_update_async()

        self.check_resolve(stage, "cube_physics_cm")

        omni.kit.commands.execute("CopyPrim", path_from="/World/" + "cube_physics_cm")

        for _ in range(5):
            await omni.kit.app.get_app().next_update_async()

        self.check_resolve(stage, "cube_physics_cm_01")
        self.check_metadata(stage, ["/World/cube_physics_cm", "/World/cube_physics_cm_01"])

        await self.new_stage()

    async def test_move_prim(self):
        await self.new_stage()
        stage = omni.usd.get_context().get_stage()
        stage_id = self.setup_stage(stage, 1.0)

        data_folder = self.get_data_folder()
        reference = data_folder + "cube_physics_cm" + ".usda"
        omni.kit.commands.execute(
            "CreateReference",
            usd_context=omni.usd.get_context(),
            path_to="/World/" + "cube_physics_cm",
            asset_path=reference.replace("\\", "/"),
            instanceable=False,
        )
        for _ in range(5):
            await omni.kit.app.get_app().next_update_async()

        self.check_resolve(stage, "cube_physics_cm")

        omni.kit.commands.execute(
            "MovePrim", path_from="/World/" + "cube_physics_cm", path_to="/World/" + "cube_physics_cm_01"
        )

        for _ in range(5):
            await omni.kit.app.get_app().next_update_async()

        self.check_resolve(stage, "cube_physics_cm_01")
        self.check_metadata(stage, ["/World/cube_physics_cm_01"])

        await self.new_stage()

    async def test_delete_prim(self):
        await self.new_stage()
        stage = omni.usd.get_context().get_stage()
        stage_id = self.setup_stage(stage, 1.0)

        data_folder = self.get_data_folder()
        reference = data_folder + "cube_physics_cm" + ".usda"
        omni.kit.commands.execute(
            "CreateReference",
            usd_context=omni.usd.get_context(),
            path_to="/World/" + "cube_physics_cm",
            asset_path=reference.replace("\\", "/"),
            instanceable=False,
        )
        for _ in range(5):
            await omni.kit.app.get_app().next_update_async()

        self.check_resolve(stage, "cube_physics_cm")

        omni.kit.commands.execute("CopyPrim", path_from="/World/" + "cube_physics_cm")

        for _ in range(5):
            await omni.kit.app.get_app().next_update_async()

        self.check_resolve(stage, "cube_physics_cm_01")
        self.check_metadata(stage, ["/World/cube_physics_cm", "/World/cube_physics_cm_01"])

        omni.kit.commands.execute("DeletePrims", paths=["/World/cube_physics_cm_01"])
        for _ in range(5):
            await omni.kit.app.get_app().next_update_async()
        self.check_metadata(stage, ["/World/cube_physics_cm"])

        omni.kit.commands.execute("DeletePrims", paths=["/World/cube_physics_cm"])
        for _ in range(5):
            await omni.kit.app.get_app().next_update_async()
        self.check_metadata(stage, [])

        await self.new_stage()

    async def test_disable_metrics_assembler(self):
        await self.new_stage()
        stage = omni.usd.get_context().get_stage()
        stage_id = self.setup_stage(stage, 1.0)

        orig_setting = carb.settings.get_settings().get_as_int(
            metricsAssembler.SETTINGS_METRICS_ASSEMBLER_OPERATION_MODE
        )
        carb.settings.get_settings().set_int(
            metricsAssembler.SETTINGS_METRICS_ASSEMBLER_OPERATION_MODE, MetricsAssemblerMode.DISABLED
        )

        data_folder = self.get_data_folder()
        reference = data_folder + "cube_physics_cm" + ".usda"
        omni.kit.commands.execute(
            "CreateReference",
            usd_context=omni.usd.get_context(),
            path_to="/World/" + "cube_physics_cm",
            asset_path=reference.replace("\\", "/"),
            instanceable=False,
        )
        for _ in range(5):
            await omni.kit.app.get_app().next_update_async()

        self.check_resolve(stage, "cube_physics_cm", expected_scale=None, expected_density=60)

        carb.settings.get_settings().set_int(metricsAssembler.SETTINGS_METRICS_ASSEMBLER_OPERATION_MODE, orig_setting)

        await self.new_stage()

    async def test_warn_metrics_assembler(self):
        await self.new_stage()
        stage = omni.usd.get_context().get_stage()
        stage_id = self.setup_stage(stage, 1.0)

        orig_setting = carb.settings.get_settings().get_as_int(
            metricsAssembler.SETTINGS_METRICS_ASSEMBLER_OPERATION_MODE
        )
        carb.settings.get_settings().set_int(
            metricsAssembler.SETTINGS_METRICS_ASSEMBLER_OPERATION_MODE, MetricsAssemblerMode.WARN
        )

        data_folder = self.get_data_folder()
        reference = data_folder + "cube_physics_cm" + ".usda"
        omni.kit.commands.execute(
            "CreateReference",
            usd_context=omni.usd.get_context(),
            path_to="/World/" + "cube_physics_cm",
            asset_path=reference.replace("\\", "/"),
            instanceable=False,
        )
        for _ in range(5):
            await omni.kit.app.get_app().next_update_async()

        self.check_resolve(stage, "cube_physics_cm", expected_scale=None, expected_density=60)

        carb.settings.get_settings().set_int(metricsAssembler.SETTINGS_METRICS_ASSEMBLER_OPERATION_MODE, orig_setting)

        await self.new_stage()

    async def test_ask_resolve_metrics_assembler(self):
        await self.new_stage()
        stage = omni.usd.get_context().get_stage()
        stage_id = self.setup_stage(stage, 1.0)

        orig_setting = carb.settings.get_settings().get_as_int(
            metricsAssembler.SETTINGS_METRICS_ASSEMBLER_OPERATION_MODE
        )
        carb.settings.get_settings().set_int(
            metricsAssembler.SETTINGS_METRICS_ASSEMBLER_OPERATION_MODE, MetricsAssemblerMode.ASK
        )

        data_folder = self.get_data_folder()
        reference = data_folder + "cube_physics_cm" + ".usda"
        omni.kit.commands.execute(
            "CreateReference",
            usd_context=omni.usd.get_context(),
            path_to="/World/" + "cube_physics_cm",
            asset_path=reference.replace("\\", "/"),
            instanceable=False,
        )

        for _ in range(5):
            await omni.kit.app.get_app().next_update_async()

        resolve_button = ui_test.find("Mismatched Units//Frame/VStack[0]/HStack[2]/Button[0]")
        await resolve_button.click()

        for _ in range(5):
            await omni.kit.app.get_app().next_update_async()

        self.check_resolve(stage, "cube_physics_cm")
        self.check_metadata(stage, ["/World/cube_physics_cm"])

        carb.settings.get_settings().set_int(metricsAssembler.SETTINGS_METRICS_ASSEMBLER_OPERATION_MODE, orig_setting)

        await self.new_stage()

    async def test_ask_cancel_metrics_assembler(self):
        await self.new_stage()
        stage = omni.usd.get_context().get_stage()
        stage_id = self.setup_stage(stage, 1.0)

        orig_setting = carb.settings.get_settings().get_as_int(
            metricsAssembler.SETTINGS_METRICS_ASSEMBLER_OPERATION_MODE
        )
        carb.settings.get_settings().set_int(
            metricsAssembler.SETTINGS_METRICS_ASSEMBLER_OPERATION_MODE, MetricsAssemblerMode.ASK
        )

        data_folder = self.get_data_folder()
        reference = data_folder + "cube_physics_cm" + ".usda"
        omni.kit.commands.execute(
            "CreateReference",
            usd_context=omni.usd.get_context(),
            path_to="/World/" + "cube_physics_cm",
            asset_path=reference.replace("\\", "/"),
            instanceable=False,
        )

        for _ in range(5):
            await omni.kit.app.get_app().next_update_async()

        cancel_button = ui_test.find("Mismatched Units//Frame/VStack[0]/HStack[2]/Button[1]")
        await cancel_button.click()

        for _ in range(5):
            await omni.kit.app.get_app().next_update_async()

        self.check_resolve(stage, "cube_physics_cm", expected_scale=None, expected_density=60)

        carb.settings.get_settings().set_int(metricsAssembler.SETTINGS_METRICS_ASSEMBLER_OPERATION_MODE, orig_setting)

        await self.new_stage()

    async def test_overlay_metrics_assembler(self):
        await self.new_stage()
        stage = omni.usd.get_context().get_stage()
        stage_id = self.setup_stage(stage, 1.0)
        viewport_api_id_str = "Viewport/Viewport0"
        viewport_setting_path = get_per_viewport_setting_path(viewport_api_id_str, METRICS_ASSEMBLER_HUD_SETTING_SUFFIX)

        orig_setting = carb.settings.get_settings().get_as_bool(viewport_setting_path)
        carb.settings.get_settings().set_bool(viewport_setting_path, False)

        for _ in range(5):
            await omni.kit.app.get_app().next_update_async()

        carb.settings.get_settings().set_bool(viewport_setting_path, True)

        for _ in range(5):
            await omni.kit.app.get_app().next_update_async()

        carb.settings.get_settings().set_bool(viewport_setting_path, orig_setting)

        await self.new_stage()

    async def test_variant_switch_stage(self):
        data_folder = self.get_data_folder()
        scene_path = data_folder + "cube_physics_m_ref_cm" + ".usda"
        await omni.usd.get_context().open_stage_async(scene_path)
        stage = omni.usd.get_context().get_stage()

        for _ in range(5):
            await omni.kit.app.get_app().next_update_async()

        self.check_resolve(stage, "cube_physics_cm")
        self.check_metadata(stage, ["/World/cube_physics_cm"])

        cube_prim = stage.GetPrimAtPath("/World/cube_physics_cm/Cube")
        self.assertTrue(cube_prim.HasAPI(UsdPhysics.RigidBodyAPI))

        prim = stage.GetPrimAtPath("/World/cube_physics_cm")
        vset = prim.GetVariantSet("physicsVariants")
        vset.SetVariantSelection("Default")

        self.assertTrue(not cube_prim.HasAPI(UsdPhysics.RigidBodyAPI))

        for _ in range(5):
            await omni.kit.app.get_app().next_update_async()

        vset.SetVariantSelection("PhysicsLowDensity")

        for _ in range(5):
            await omni.kit.app.get_app().next_update_async()

        self.assertTrue(cube_prim.HasAPI(UsdPhysics.RigidBodyAPI))
        self.check_resolve(stage, "cube_physics_cm", expected_density=10 * 100 * 100 * 100)
        self.check_metadata(stage, ["/World/cube_physics_cm"])

        await self.new_stage()

    async def test_variant_switch_stage_disabled_listener(self):
        data_folder = self.get_data_folder()
        scene_path = data_folder + "cube_physics_m_ref_cm" + ".usda"
        await omni.usd.get_context().open_stage_async(scene_path)
        stage = omni.usd.get_context().get_stage()

        orig_setting = carb.settings.get_settings().get_as_bool(
            metricsAssembler.SETTINGS_METRICS_ASSEMBLER_PARAMS_CHANGE_LISTENER_ENABLED
        )
        carb.settings.get_settings().set_bool(
            metricsAssembler.SETTINGS_METRICS_ASSEMBLER_PARAMS_CHANGE_LISTENER_ENABLED, False
        )

        for _ in range(5):
            await omni.kit.app.get_app().next_update_async()

        self.check_resolve(stage, "cube_physics_cm")
        self.check_metadata(stage, ["/World/cube_physics_cm"])

        cube_prim = stage.GetPrimAtPath("/World/cube_physics_cm/Cube")
        self.assertTrue(cube_prim.HasAPI(UsdPhysics.RigidBodyAPI))

        prim = stage.GetPrimAtPath("/World/cube_physics_cm")
        vset = prim.GetVariantSet("physicsVariants")
        vset.SetVariantSelection("Default")
        for _ in range(5):
            await omni.kit.app.get_app().next_update_async()

        self.assertTrue(not cube_prim.HasAPI(UsdPhysics.RigidBodyAPI))

        vset.SetVariantSelection("PhysicsLowDensity")
        for _ in range(5):
            await omni.kit.app.get_app().next_update_async()

        self.assertTrue(cube_prim.HasAPI(UsdPhysics.RigidBodyAPI))
        self.check_resolve(stage, "cube_physics_cm")
        self.check_metadata(stage, ["/World/cube_physics_cm"])

        carb.settings.get_settings().set_bool(
            metricsAssembler.SETTINGS_METRICS_ASSEMBLER_PARAMS_CHANGE_LISTENER_ENABLED, orig_setting
        )

        await self.new_stage()
