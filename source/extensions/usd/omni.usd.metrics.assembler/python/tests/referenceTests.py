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

import carb
import omni.kit.test
import omni.metrics.assembler.core.bindings._metricsAssembler as metricsAssembler
from omni.metrics.assembler.core import get_metrics_assembler_interface
from pxr import Gf, Usd, UsdGeom, UsdPhysics, UsdUtils

CUSTOM_RULE_TOKEN = "nvidia:resolve:attribute"
EPSILON = 1e-3


# Tests for divergent referenced USD file
class MetricsAssemblerReferenceTests(omni.kit.test.AsyncTestCase):
    async def setUp(self):
        # register custom rule
        self._custom_id = get_metrics_assembler_interface().register_custom_resolve_rule(CUSTOM_RULE_TOKEN, 1, 0)

    async def tearDown(self):
        get_metrics_assembler_interface().unregister_custom_resolve_rule(self._custom_id)

    def setup(self, stage):
        cache = UsdUtils.StageCache.Get()
        cache.Insert(stage)
        stage_id = cache.GetId(stage).ToLongInt()

        # setup stage in cm
        UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.y)
        UsdGeom.SetStageMetersPerUnit(stage, 0.01)
        UsdPhysics.SetStageKilogramsPerUnit(stage, 1.0)
        return stage_id

    def setup_reference(self, stage, file_name, instance_path="/World/xformInst"):
        data_folder = os.path.abspath(os.path.normpath(os.path.join(__file__, "../../../../../../data/")))
        data_folder = data_folder.replace("\\", "/") + "/"

        xform = UsdGeom.Xform.Define(stage, instance_path)
        xform.GetPrim().GetReferences().AddReference(data_folder + file_name + ".usda")

    async def test_reference_divergency_mpu_check(self):
        stage = Usd.Stage.CreateInMemory()
        stage_id = self.setup(stage)

        divergent_stage = get_metrics_assembler_interface().resolve_stage(stage_id)
        self.assertTrue(not divergent_stage)

        self.setup_reference(stage, "cube_meters")

        divergent_stage = get_metrics_assembler_interface().resolve_stage(stage_id)
        self.assertTrue(divergent_stage)

    async def test_reference_divergency_kgpu_check(self):
        stage = Usd.Stage.CreateInMemory()
        stage_id = self.setup(stage)

        divergent_stage = get_metrics_assembler_interface().resolve_stage(stage_id)
        self.assertTrue(not divergent_stage)

        self.setup_reference(stage, "cube_kilograms")

        divergent_stage = get_metrics_assembler_interface().resolve_stage(stage_id)
        self.assertTrue(divergent_stage)

    async def test_reference_divergency_upaxis_check(self):
        stage = Usd.Stage.CreateInMemory()
        stage_id = self.setup(stage)

        divergent_stage = get_metrics_assembler_interface().resolve_stage(stage_id)
        self.assertTrue(not divergent_stage)

        self.setup_reference(stage, "cube_upAxis")

        divergent_stage = get_metrics_assembler_interface().resolve_stage(stage_id)
        self.assertTrue(divergent_stage)

    async def test_reference_rule_resolve_attribute(self):
        stage = Usd.Stage.CreateInMemory()
        stage_id = self.setup(stage)
        self._stageId = stage_id
        self.setup_reference(stage, "cube_meters")

        # we registered CUSTOM_RULE_TOKEN lets check the value
        cube_prim = stage.GetPrimAtPath("/World/xformInst/Cube")
        custom_attribute = cube_prim.GetAttribute(CUSTOM_RULE_TOKEN)
        start_value = custom_attribute.Get()
        self.assertTrue(start_value == 1.0)

        divergent_stage = get_metrics_assembler_interface().resolve_stage(stage_id)
        self.assertTrue(divergent_stage)

        resolved_value = custom_attribute.Get()
        self.assertTrue(abs(resolved_value - 100.0) < EPSILON)

    async def test_reference_xform_mpu_resolve(self):
        stage = Usd.Stage.CreateInMemory()
        stage_id = self.setup(stage)
        self._stageId = stage_id
        self.setup_reference(stage, "cube_meters")

        cube_prim = stage.GetPrimAtPath("/World/xformInst/Cube")
        xform = UsdGeom.Xformable(cube_prim)
        start_value = xform.ComputeLocalToWorldTransform(Usd.TimeCode.Default()).ExtractTranslation()
        self.assertTrue(Gf.IsClose(start_value, Gf.Vec3d(1.0), EPSILON))

        divergent_stage = get_metrics_assembler_interface().resolve_stage(stage_id)
        self.assertTrue(divergent_stage)

        resolved_value = xform.ComputeLocalToWorldTransform(Usd.TimeCode.Default()).ExtractTranslation()
        self.assertTrue(Gf.IsClose(resolved_value, Gf.Vec3d(100.0), EPSILON))

        inst_prim = stage.GetPrimAtPath("/World/xformInst")
        scale_attr = inst_prim.GetAttribute("xformOp:scale:unitsResolve")
        self.assertTrue(scale_attr)

    async def test_reference_xform_mpu_resolve_xform_common_api(self):
        stage = Usd.Stage.CreateInMemory()
        stage_id = self.setup(stage)
        self._stageId = stage_id
        self.setup_reference(stage, "cube_meters")

        settings = carb.settings.acquire_settings_interface()
        settings.set(metricsAssembler.SETTINGS_METRICS_ASSEMBLER_CONFORM_TO_XFORM_COMMON_API, True)

        cube_prim = stage.GetPrimAtPath("/World/xformInst/Cube")
        xform = UsdGeom.Xformable(cube_prim)
        start_value = xform.ComputeLocalToWorldTransform(Usd.TimeCode.Default()).ExtractTranslation()
        self.assertTrue(Gf.IsClose(start_value, Gf.Vec3d(1.0), EPSILON))

        divergent_stage = get_metrics_assembler_interface().resolve_stage(stage_id)
        self.assertTrue(divergent_stage)

        resolved_value = xform.ComputeLocalToWorldTransform(Usd.TimeCode.Default()).ExtractTranslation()
        self.assertTrue(Gf.IsClose(resolved_value, Gf.Vec3d(100.0), EPSILON))

        inst_prim = stage.GetPrimAtPath("/World/xformInst")
        scale_attr = inst_prim.GetAttribute("xformOp:scale:unitsResolve")
        self.assertTrue(not scale_attr)

        scale_attr = inst_prim.GetAttribute("xformOp:scale")
        self.assertTrue(scale_attr)
        self.assertTrue(Gf.IsClose(scale_attr.Get(), Gf.Vec3f(100.0), EPSILON))

        settings.set(metricsAssembler.SETTINGS_METRICS_ASSEMBLER_CONFORM_TO_XFORM_COMMON_API, False)

    async def test_reference_xform_mpu_pivot_resolve(self):
        stage = Usd.Stage.CreateInMemory()
        stage_id = self.setup(stage)
        self._stageId = stage_id
        self.setup_reference(stage, "cube_meters")

        cube_prim = stage.GetPrimAtPath("/World/xformInst/Cube")
        inst_prim = stage.GetPrimAtPath("/World/xformInst")
        xform = UsdGeom.Xformable(cube_prim)
        xform_inst = UsdGeom.Xformable(inst_prim)
        xform_inst.ClearXformOpOrder()
        xform_inst.AddTranslateOp().Set((0, 0, 0))
        xform_inst.AddTranslateOp(opSuffix="pivot", isInverseOp=False).Set(Gf.Vec3d(0, 0, 0))
        xform_inst.AddRotateXYZOp()
        xform_inst.AddScaleOp().Set((1, 1, 1))
        xform_inst.AddTranslateOp(opSuffix="pivot", isInverseOp=True)

        divergent_stage = get_metrics_assembler_interface().resolve_stage(stage_id)
        self.assertTrue(divergent_stage)

        scale_attr = inst_prim.GetAttribute("xformOp:scale:unitsResolve")
        self.assertTrue(scale_attr)

        self.assertTrue(xform_inst.GetOrderedXformOps()[-1].IsInverseOp())

    async def test_reference_xform_upaxis_resolve(self):
        stage = Usd.Stage.CreateInMemory()
        stage_id = self.setup(stage)
        self._stageId = stage_id
        self.setup_reference(stage, "cube_upAxis")

        cube_prim = stage.GetPrimAtPath("/World/xformInst/Cube")
        xform = UsdGeom.Xformable(cube_prim)
        start_value = xform.ComputeLocalToWorldTransform(Usd.TimeCode.Default()).ExtractTranslation()
        self.assertTrue(Gf.IsClose(start_value, Gf.Vec3d(1.0), EPSILON))

        divergent_stage = get_metrics_assembler_interface().resolve_stage(stage_id)
        self.assertTrue(divergent_stage)

        resolved_value = xform.ComputeLocalToWorldTransform(Usd.TimeCode.Default()).ExtractTranslation()
        self.assertTrue(Gf.IsClose(resolved_value, Gf.Vec3d(100.0, 100.0, -100.0), EPSILON))

        inst_prim = stage.GetPrimAtPath("/World/xformInst")
        scale_attr = inst_prim.GetAttribute("xformOp:scale:unitsResolve")
        self.assertTrue(scale_attr)

        rotate_attr = inst_prim.GetAttribute("xformOp:rotateX:unitsResolve")
        self.assertTrue(rotate_attr)

        val = rotate_attr.Get()
        self.assertTrue(val == -90.0)

    async def test_reference_xform_upaxis_resolve_xform_common_api(self):
        stage = Usd.Stage.CreateInMemory()
        stage_id = self.setup(stage)
        self._stageId = stage_id
        self.setup_reference(stage, "cube_upAxis")

        settings = carb.settings.acquire_settings_interface()
        settings.set(metricsAssembler.SETTINGS_METRICS_ASSEMBLER_CONFORM_TO_XFORM_COMMON_API, True)

        cube_prim = stage.GetPrimAtPath("/World/xformInst/Cube")
        xform = UsdGeom.Xformable(cube_prim)
        start_value = xform.ComputeLocalToWorldTransform(Usd.TimeCode.Default()).ExtractTranslation()
        self.assertTrue(Gf.IsClose(start_value, Gf.Vec3d(1.0), EPSILON))

        divergent_stage = get_metrics_assembler_interface().resolve_stage(stage_id)
        self.assertTrue(divergent_stage)

        resolved_value = xform.ComputeLocalToWorldTransform(Usd.TimeCode.Default()).ExtractTranslation()
        self.assertTrue(Gf.IsClose(resolved_value, Gf.Vec3d(100.0, 100.0, -100.0), EPSILON))

        inst_prim = stage.GetPrimAtPath("/World/xformInst")
        scale_attr = inst_prim.GetAttribute("xformOp:scale:unitsResolve")
        self.assertTrue(not scale_attr)

        rotate_attr = inst_prim.GetAttribute("xformOp:rotateX:unitsResolve")
        self.assertTrue(not rotate_attr)

        rotate_attr = inst_prim.GetAttribute("xformOp:rotateXYZ")
        self.assertTrue(rotate_attr.Get()[0] == -90.0)

        settings.set(metricsAssembler.SETTINGS_METRICS_ASSEMBLER_CONFORM_TO_XFORM_COMMON_API, False)

    async def test_reference_xform_mpu_resolve_recursive(self):
        stage = Usd.Stage.CreateInMemory()
        stage_id = self.setup(stage)
        self._stageId = stage_id
        self.setup_reference(stage, "cube_meters")

        # level0 reference
        cube_prim = stage.GetPrimAtPath("/World/xformInst/Cube")
        xform = UsdGeom.Xformable(cube_prim)
        start_value = xform.ComputeLocalToWorldTransform(Usd.TimeCode.Default()).ExtractTranslation()
        self.assertTrue(Gf.IsClose(start_value, Gf.Vec3d(1.0), EPSILON))

        divergent_stage = get_metrics_assembler_interface().resolve_stage(stage_id)
        self.assertTrue(divergent_stage)

        resolved_value = xform.ComputeLocalToWorldTransform(Usd.TimeCode.Default()).ExtractTranslation()
        self.assertTrue(Gf.IsClose(resolved_value, Gf.Vec3d(100.0), EPSILON))

        inst_prim = stage.GetPrimAtPath("/World/xformInst")
        scale_attr = inst_prim.GetAttribute("xformOp:scale:unitsResolve")
        self.assertTrue(scale_attr)

        # nested reference
        self.setup_reference(stage, "cube_meters", "/World/xformInst/xformInst")

        cube_prim = stage.GetPrimAtPath("/World/xformInst/xformInst/Cube")
        xform = UsdGeom.Xformable(cube_prim)
        start_value = xform.ComputeLocalToWorldTransform(Usd.TimeCode.Default()).ExtractTranslation()
        self.assertTrue(Gf.IsClose(start_value, Gf.Vec3d(100.0), EPSILON))

        divergent_stage = get_metrics_assembler_interface().resolve_hierarchy(stage_id, "/World/xformInst/xformInst")
        self.assertTrue(divergent_stage)

        resolved_value = xform.ComputeLocalToWorldTransform(Usd.TimeCode.Default()).ExtractTranslation()
        self.assertTrue(Gf.IsClose(resolved_value, Gf.Vec3d(100.0), EPSILON))

        inst_prim = stage.GetPrimAtPath("/World/xformInst/xformInst")
        scale_attr = inst_prim.GetAttribute("xformOp:scale:unitsResolve")
        self.assertTrue(scale_attr)
