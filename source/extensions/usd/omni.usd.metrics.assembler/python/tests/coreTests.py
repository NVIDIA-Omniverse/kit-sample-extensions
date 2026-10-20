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
from omni.metrics.assembler.core.bindings._metricsAssembler import UnitsInfo
from pxr import Usd, UsdGeom, UsdPhysics, UsdUtils

CUSTOM_RULE_TOKEN = "nvidia:resolve:attribute"
CUSTOM_RULE_TOKEN_TS = "nvidia:resolve:attributets"
EPSILON = 1e-3


# Tests for divergent core tests using referenced USD file
class MetricsAssemblerCoreTests(omni.kit.test.AsyncTestCase):
    async def setUp(self):
        # register custom rule
        self._custom_id = get_metrics_assembler_interface().register_custom_resolve_rule(CUSTOM_RULE_TOKEN, 1, 0)
        self._custom_id_ts = get_metrics_assembler_interface().register_custom_resolve_rule(CUSTOM_RULE_TOKEN_TS, 1, 0)

    async def tearDown(self):
        get_metrics_assembler_interface().unregister_custom_resolve_rule(self._custom_id)
        get_metrics_assembler_interface().unregister_custom_resolve_rule(self._custom_id_ts)

    def setup(self, stage):
        cache = UsdUtils.StageCache.Get()
        cache.Insert(stage)
        stage_id = cache.GetId(stage).ToLongInt()

        # setup stage in cm and Y upAxis
        UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.y)
        UsdGeom.SetStageMetersPerUnit(stage, 0.01)
        UsdPhysics.SetStageKilogramsPerUnit(stage, 1.0)

        return stage_id

    def setup_reference(self, stage, file_name, instance_path="/World/xformInst"):
        data_folder = os.path.abspath(os.path.normpath(os.path.join(__file__, "../../../../../../data/")))
        data_folder = data_folder.replace("\\", "/") + "/"

        xform = UsdGeom.Xform.Define(stage, instance_path)
        xform.GetPrim().GetReferences().AddReference(data_folder + file_name + ".usda")

    async def test_core_divergency_check_stage(self):
        stage = Usd.Stage.CreateInMemory()
        stage_id = self.setup(stage)

        divergent_stage = get_metrics_assembler_interface().check_stage(stage_id)
        self.assertTrue(not divergent_stage)

        self.setup_reference(stage, "cube_meters")

        divergent_stage = get_metrics_assembler_interface().check_stage(stage_id)
        self.assertTrue(divergent_stage)

        divergent_stage = get_metrics_assembler_interface().resolve_stage(stage_id)
        self.assertTrue(divergent_stage)

    async def test_core_divergency_check_hierarchy(self):
        stage = Usd.Stage.CreateInMemory()
        stage_id = self.setup(stage)

        divergent_stage = get_metrics_assembler_interface().check_stage(stage_id)
        self.assertTrue(not divergent_stage)

        self.setup_reference(stage, "cube_meters")

        divergent_stage = get_metrics_assembler_interface().check_stage(stage_id)
        self.assertTrue(divergent_stage)

        divergent_stage = get_metrics_assembler_interface().resolve_hierarchy(stage_id, "/World/xformInst")
        self.assertTrue(divergent_stage)

    def resolve_start(self, stageId):
        self._resolve_start = True
        self.assertTrue(stageId == self._stageId)

    def resolve_end(self, stageId):
        self._resolve_end = True
        self.assertTrue(stageId == self._stageId)

    def resolve_prim(self, usdPrimPath, stageUnits, resolveUnits):
        self._num_resolved_prims = self._num_resolved_prims + 1
        return True

    def resolve_attribute(
        self, usdPrimPath, attributeName, stageUnits, resolveUnits, metersExponent, kilogramsExponent
    ):
        self._num_resolved_attributes = self._num_resolved_attributes + 1

        # check stage units
        self.assertTrue(stageUnits.meters_per_unit == 0.01)
        self.assertTrue(stageUnits.kilograms_per_unit == 1.0)
        self.assertTrue(stageUnits.up_axis == "Y")

        # check resolve units
        self.assertTrue(resolveUnits.meters_per_unit == 1.0)
        self.assertTrue(resolveUnits.kilograms_per_unit == 1.0)
        self.assertTrue(resolveUnits.up_axis == "Y")

        if attributeName == CUSTOM_RULE_TOKEN and metersExponent == 1:
            self._custom_rule_found = True

        return (True, metersExponent, kilogramsExponent)

    async def test_core_custom_callback(self):
        stage = Usd.Stage.CreateInMemory()
        stage_id = self.setup(stage)
        self._stageId = stage_id
        self.setup_reference(stage, "cube_meters")

        self._resolve_start = False
        self._resolve_end = False
        self._num_resolved_prims = 0
        self._num_resolved_attributes = 0
        self._custom_rule_found = False

        reg_id = get_metrics_assembler_interface().register_custom_callback(
            self.resolve_start, self.resolve_end, self.resolve_prim, self.resolve_attribute
        )

        divergent_stage = get_metrics_assembler_interface().resolve_stage(stage_id)
        self.assertTrue(divergent_stage)

        self.assertTrue(self._resolve_start)
        self.assertTrue(self._resolve_end)

        self.assertTrue(self._custom_rule_found)

        self.assertTrue(self._num_resolved_prims == 2)
        self.assertTrue(self._num_resolved_attributes == 8)

        get_metrics_assembler_interface().unregister_custom_callback(reg_id)

    async def test_core_rule_resolve_attribute(self):
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

    async def test_core_rule_resolve_attribute_time_sampled(self):
        stage = Usd.Stage.CreateInMemory()
        stage_id = self.setup(stage)
        self._stageId = stage_id
        self.setup_reference(stage, "cube_meters")

        # we registered CUSTOM_RULE_TOKEN lets check the value
        cube_prim = stage.GetPrimAtPath("/World/xformInst/Cube")
        custom_attribute = cube_prim.GetAttribute(CUSTOM_RULE_TOKEN_TS)
        val0 = custom_attribute.Get(Usd.TimeCode(0))
        self.assertTrue(val0 == -1.0)
        val1 = custom_attribute.Get(Usd.TimeCode(50))
        self.assertTrue(val1 == 5.0)
        val2 = custom_attribute.Get(Usd.TimeCode(100))
        self.assertTrue(val2 == 1.0)

        divergent_stage = get_metrics_assembler_interface().resolve_stage(stage_id)
        self.assertTrue(divergent_stage)

        resolved_value0 = custom_attribute.Get(Usd.TimeCode(0))
        print(resolved_value0)
        self.assertTrue(abs(resolved_value0 + 100.0) < EPSILON)
        resolved_value1 = custom_attribute.Get(Usd.TimeCode(50))
        self.assertTrue(abs(resolved_value1 - 500.0) < EPSILON)
        resolved_value2 = custom_attribute.Get(Usd.TimeCode(100))
        self.assertTrue(abs(resolved_value2 - 100.0) < EPSILON)

    async def test_core_rule_resolve_attribute_callback(self):
        stage = Usd.Stage.CreateInMemory()
        stage_id = self.setup(stage)
        self._stageId = stage_id
        self.setup_reference(stage, "cube_meters")

        # we registered CUSTOM_RULE_TOKEN lets check the value
        cube_prim = stage.GetPrimAtPath("/World/xformInst/Cube")
        custom_attribute = cube_prim.GetAttribute(CUSTOM_RULE_TOKEN)
        start_value = custom_attribute.Get()
        self.assertTrue(start_value == 1.0)

        def resolve_attribute(usdPrimPath, attributeName, stageUnits, resolveUnits, metersExponent, kilogramsExponent):
            metersExponentOut = metersExponent
            if attributeName == CUSTOM_RULE_TOKEN and metersExponent == 1:
                metersExponentOut = -1

            return (True, metersExponentOut, kilogramsExponent)

        reg_id = get_metrics_assembler_interface().register_custom_callback(None, None, None, resolve_attribute)

        divergent_stage = get_metrics_assembler_interface().resolve_stage(stage_id)
        self.assertTrue(divergent_stage)

        resolved_value = custom_attribute.Get()
        self.assertTrue(abs(resolved_value - 0.01) < EPSILON)

        get_metrics_assembler_interface().unregister_custom_callback(reg_id)

    async def test_core_rule_resolve_attribute_callback_filter(self):
        stage = Usd.Stage.CreateInMemory()
        stage_id = self.setup(stage)
        self._stageId = stage_id
        self.setup_reference(stage, "cube_meters")

        # we registered CUSTOM_RULE_TOKEN lets check the value
        cube_prim = stage.GetPrimAtPath("/World/xformInst/Cube")
        custom_attribute = cube_prim.GetAttribute(CUSTOM_RULE_TOKEN)
        start_value = custom_attribute.Get()
        self.assertTrue(start_value == 1.0)

        def resolve_attribute(usdPrimPath, attributeName, stageUnits, resolveUnits, metersExponent, kilogramsExponent):
            metersExponentOut = metersExponent
            if attributeName == CUSTOM_RULE_TOKEN and metersExponent == 1:
                metersExponentOut = -1

            return (True, metersExponentOut, kilogramsExponent)

        reg_id = get_metrics_assembler_interface().register_custom_callback(
            None, None, None, resolve_attribute, [CUSTOM_RULE_TOKEN]
        )

        divergent_stage = get_metrics_assembler_interface().resolve_stage(stage_id)
        self.assertTrue(divergent_stage)

        resolved_value = custom_attribute.Get()
        self.assertTrue(abs(resolved_value - 0.01) < EPSILON)

        get_metrics_assembler_interface().unregister_custom_callback(reg_id)

    async def test_core_rule_resolve_attribute_callback_filter_miss(self):
        stage = Usd.Stage.CreateInMemory()
        stage_id = self.setup(stage)
        self._stageId = stage_id
        self.setup_reference(stage, "cube_meters")

        # we registered CUSTOM_RULE_TOKEN lets check the value
        cube_prim = stage.GetPrimAtPath("/World/xformInst/Cube")
        custom_attribute = cube_prim.GetAttribute(CUSTOM_RULE_TOKEN)
        start_value = custom_attribute.Get()
        self.assertTrue(start_value == 1.0)

        def resolve_attribute(usdPrimPath, attributeName, stageUnits, resolveUnits, metersExponent, kilogramsExponent):
            metersExponentOut = metersExponent
            if attributeName == CUSTOM_RULE_TOKEN and metersExponent == 1:
                metersExponentOut = -1

            return (True, metersExponentOut, kilogramsExponent)

        # We filter with a different name, hence the callback should not be called
        reg_id = get_metrics_assembler_interface().register_custom_callback(
            None, None, None, resolve_attribute, ["test:attr"]
        )

        divergent_stage = get_metrics_assembler_interface().resolve_stage(stage_id)
        self.assertTrue(divergent_stage)

        resolved_value = custom_attribute.Get()
        # Expect 100 as the default rule got applied only
        self.assertTrue(abs(resolved_value - 100.0) < EPSILON)

        get_metrics_assembler_interface().unregister_custom_callback(reg_id)

    async def test_core_set_layer(self):
        stage = Usd.Stage.CreateInMemory()
        stage_id = self.setup(stage)
        self._stageId = stage_id
        self.setup_reference(stage, "cube_meters")

        session_layer = stage.GetSessionLayer()

        get_metrics_assembler_interface().set_resolve_layer(session_layer.identifier)

        # we registered CUSTOM_RULE_TOKEN lets check the value
        cube_prim = stage.GetPrimAtPath("/World/xformInst/Cube")
        custom_attribute = cube_prim.GetAttribute(CUSTOM_RULE_TOKEN)
        start_value = custom_attribute.Get()
        self.assertTrue(start_value == 1.0)

        divergent_stage = get_metrics_assembler_interface().resolve_stage(stage_id)
        self.assertTrue(divergent_stage)

        resolved_value = custom_attribute.Get()
        self.assertTrue(abs(resolved_value - 100.0) < EPSILON)

        self.assertTrue(session_layer.GetAttributeAtPath(custom_attribute.GetPath()) != None)
        self.assertTrue(stage.GetRootLayer().GetAttributeAtPath(custom_attribute.GetPath()) == None)

        get_metrics_assembler_interface().set_resolve_layer(None)

    async def test_core_check_layer(self):
        stage = Usd.Stage.CreateInMemory()
        stage_id = self.setup(stage)
        self._stageId = stage_id
        self.setup_reference(stage, "cube_meters")

        root_layer = stage.GetRootLayer()
        layers = stage.GetUsedLayers()
        self.assertTrue(len(layers) == 3)

        for layer in layers:
            if "anon" not in layer.identifier:
                ret_val = get_metrics_assembler_interface().check_layers(
                    root_layer.identifier, layer.identifier, stage_id
                )
                self.assertTrue(ret_val["ret_val"])
                self.assertTrue(abs(ret_val["units_info0"].meters_per_unit - 0.01) < 0.01)
                self.assertTrue(abs(ret_val["units_info1"].meters_per_unit - 1.0) < 0.01)

    async def test_core_stage_units_change(self):
        stage = Usd.Stage.CreateInMemory()
        stage_id = self.setup(stage)

        default_prim = UsdGeom.Xform.Define(stage, "/World")
        stage.SetDefaultPrim(default_prim.GetPrim())

        cube = UsdGeom.Cube.Define(stage, "/World/cube")
        xform_api = UsdGeom.XformCommonAPI(cube)
        xform_api.SetTranslate((8, 120, 8))
        xform_api.SetRotate((0, 0, 0))
        xform_api.SetScale((1, 1, 1))

        scale = cube.GetPrim().GetAttribute("xformOp:scale").Get()
        rotate = cube.GetPrim().GetAttribute("xformOp:rotateXYZ").Get()
        self.assertTrue(scale == (1, 1, 1))
        self.assertTrue(rotate == (0, 0, 0))

        new_units = UnitsInfo()
        new_units.meters_per_unit = 1.0
        new_units.kilograms_per_unit = 1.0
        new_units.up_axis = "Z"

        get_metrics_assembler_interface().change_stage_units(stage_id, new_units)

        scale = cube.GetPrim().GetAttribute("xformOp:scale").Get()
        self.assertTrue(scale == (0.01, 0.01, 0.01))

        rotate = cube.GetPrim().GetAttribute("xformOp:rotateXYZ").Get()
        print(rotate)
        self.assertTrue(rotate == (90, 0, 0))

        self.assertTrue(UsdGeom.GetStageMetersPerUnit(stage) == 1.0)
        self.assertTrue(UsdPhysics.GetStageKilogramsPerUnit(stage) == 1.0)
        self.assertTrue(UsdGeom.GetStageUpAxis(stage) == UsdGeom.Tokens.z)
