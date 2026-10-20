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

import omni.kit.test
from omni.metrics.assembler.core import get_metrics_assembler_interface
from pxr import Gf, Sdf, Usd, UsdGeom, UsdPhysics, UsdUtils

CUSTOM_RULE_TOKEN = "nvidia:resolve:attribute"
EPSILON = 1e-3


# Tests for divergent layer USD file
class MetricsAssemblerLayerTests(omni.kit.test.AsyncTestCase):
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

        default_prim = UsdGeom.Xform.Define(stage, "/World").GetPrim()
        stage.SetDefaultPrim(default_prim)

        return stage_id

    def setup_payload(self, stage, file_name):
        data_folder = os.path.abspath(os.path.normpath(os.path.join(__file__, "../../../../../../data/")))
        data_folder = data_folder.replace("\\", "/") + "/"
        file_path = data_folder + file_name + ".usda"

        root_layer = stage.GetRootLayer()
        new_layer = Sdf.Layer.FindOrOpen(file_path)
        self.assertTrue(new_layer)
        root_layer.subLayerPaths.insert(0, file_path)

    async def test_layer_divergency_mpu_check(self):
        stage = Usd.Stage.CreateInMemory()
        stage_id = self.setup(stage)

        divergent_stage = get_metrics_assembler_interface().resolve_stage(stage_id)
        self.assertTrue(not divergent_stage)

        self.setup_payload(stage, "cube_meters")

        divergent_stage = get_metrics_assembler_interface().resolve_stage(stage_id)
        self.assertTrue(divergent_stage)

    async def test_layer_divergency_kgpu_check(self):
        stage = Usd.Stage.CreateInMemory()
        stage_id = self.setup(stage)

        divergent_stage = get_metrics_assembler_interface().resolve_stage(stage_id)
        self.assertTrue(not divergent_stage)

        self.setup_payload(stage, "cube_kilograms")

        divergent_stage = get_metrics_assembler_interface().resolve_stage(stage_id)
        self.assertTrue(divergent_stage)

    async def test_layer_divergency_upaxis_check(self):
        stage = Usd.Stage.CreateInMemory()
        stage_id = self.setup(stage)

        divergent_stage = get_metrics_assembler_interface().resolve_stage(stage_id)
        self.assertTrue(not divergent_stage)

        self.setup_payload(stage, "cube_upAxis")

        divergent_stage = get_metrics_assembler_interface().resolve_stage(stage_id)
        self.assertTrue(divergent_stage)

    async def test_layer_rule_resolve_attribute(self):
        stage = Usd.Stage.CreateInMemory()
        stage_id = self.setup(stage)
        self._stageId = stage_id
        self.setup_payload(stage, "cube_meters")

        # we registered CUSTOM_RULE_TOKEN lets check the value
        cube_prim = stage.GetPrimAtPath("/World/Cube")
        custom_attribute = cube_prim.GetAttribute(CUSTOM_RULE_TOKEN)
        start_value = custom_attribute.Get()
        self.assertTrue(start_value == 1.0)

        divergent_stage = get_metrics_assembler_interface().resolve_stage(stage_id)
        self.assertTrue(divergent_stage)

        resolved_value = custom_attribute.Get()
        self.assertTrue(abs(resolved_value - 100.0) < EPSILON)

    async def test_layer_xform_scale_resolve(self):
        stage = Usd.Stage.CreateInMemory()
        stage_id = self.setup(stage)
        self._stageId = stage_id
        self.setup_payload(stage, "cube_meters")

        cube_prim = stage.GetPrimAtPath("/World/Cube")
        xform = UsdGeom.Xformable(cube_prim)
        start_value = xform.ComputeLocalToWorldTransform(Usd.TimeCode.Default()).ExtractTranslation()
        self.assertTrue(Gf.IsClose(start_value, Gf.Vec3d(1.0), EPSILON))

        divergent_stage = get_metrics_assembler_interface().resolve_stage(stage_id)
        self.assertTrue(divergent_stage)

        resolved_value = xform.ComputeLocalToWorldTransform(Usd.TimeCode.Default()).ExtractTranslation()
        self.assertTrue(Gf.IsClose(resolved_value, Gf.Vec3d(100.0), EPSILON))

        inst_prim = stage.GetPrimAtPath("/World")
        scale_attr = inst_prim.GetAttribute("xformOp:scale:unitsResolve")
        self.assertTrue(not scale_attr)

        scale_attr = cube_prim.GetAttribute("xformOp:scale:unitsResolve")
        self.assertTrue(scale_attr)
