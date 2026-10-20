## Copyright (c) 2022, NVIDIA CORPORATION.  All rights reserved.
##
## NVIDIA CORPORATION and its licensors retain all intellectual property
## and proprietary rights in and to this software, related documentation
## and any modifications thereto.  Any use, reproduction, disclosure or
## distribution of this software and related documentation without an express
## license agreement from NVIDIA CORPORATION is strictly prohibited.
##

# deprecated omni.particle.system.core
"""
import pathlib

import carb.settings
import omni.kit
import omni.kit.app
import omni.usd
from omni.kit.test.async_unittest import AsyncTestCase
from pxr import Gf, Sdf

EXTENSION_FOLDER_PATH = pathlib.Path(
    omni.kit.app.get_app().get_extension_manager().get_extension_path_by_module(__name__)
)
TEST_DATA_PATH = EXTENSION_FOLDER_PATH.joinpath("data/tests")

# Deprecated particle system
import omni.particle.system.core
import omni.graph.core as ogc

class TestParticleSystemRamps(AsyncTestCase):
    ######################################################################
    # WARNING: changing the value of this flag will switch this script
    # from running the tests to overwriting the 'golden' data. If a test
    # is failing, make sure you understand why / whether it's ok to change
    # the ground truth data before running the tests with this flag set
    # to True.
    ######################################################################
    WRITE_TEST_RESULTS = False

    # Before running each test
    async def setUp(self):
        self._smallNumber = 0.001

        # change settings so that we get repeatable particle system results
        self._settings = carb.settings.get_settings()
        self._prev_use_fixed_dt = self._settings.get(omni.particle.system.core.useFixedTimeStep)
        self._prev_random_seed = self._settings.get(omni.particle.system.core.randomSeed)
        self._settings.set(omni.particle.system.core.useFixedTimeStep, True)
        self._settings.set(omni.particle.system.core.randomSeed, 1337)

    # After running each test
    async def tearDown(self):
        if self.WRITE_TEST_RESULTS:
            (result, _, _) = await self._usd_context.save_as_stage_async(self._golden_file_path)
            self.assertTrue(result, "Failed to save stage at path: {}".format(self._golden_file_path))

        # restore persistent settings that we changed for this test
        self._settings.set(omni.particle.system.core.randomSeed, self._prev_random_seed)
        self._settings.set(omni.particle.system.core.useFixedTimeStep, self._prev_use_fixed_dt)

        self._stage = None
        self._usd_context = None

    async def setupStage(self, path_to_stage):
        # Load stage -- note this must happen after changing the settings, since the OG nodes
        # will be initialized when the stage is loaded.
        self._usd_path = TEST_DATA_PATH.absolute()
        test_file_path = str(self._usd_path.joinpath(path_to_stage).absolute())

        self._usd_context = omni.usd.get_context()
        await self._usd_context.open_stage_async(test_file_path)
        self._stage = self._usd_context.get_stage()
        self.assertIsNotNone(self._stage)

        self._graph = ogc.get_graph_by_path("/World/effect")
        self.assertIsNotNone(self._graph, f"Failed to find graph in test scene")

        # disable the settings that require viewport access, since we haven't set one up in this test
        geo_rep_node = self._graph.get_node("/World/effect/geometry_replicator")
        geo_rep_node.get_attribute("inputs:faceActiveCamera").set(False)
        geo_rep_node.get_attribute("inputs:orientWithActiveCamera").set(False)

    async def test_objectindex_ramp(self):
        await self.setupStage("particle_system_object_ramp_tests.usda")
        self._golden_file_path = str(self._usd_path.joinpath("golden_data_object_ramp.usda").absolute())

        # turn on the solver
        solver_node = self._graph.get_node(f"/World/effect/solver")
        solver_node.get_attribute("inputs:active").set(True)

        # let the particle system play -- we'll let it run for a while to give collisions a chance to occur
        for _ in range(50):
            await omni.kit.app.get_app().next_update_async()

        outputPrim = self._stage.GetPrimAtPath("/World/output")
        self.assertTrue(outputPrim.IsValid(), "Invalid output prim")
        attr = outputPrim.GetAttribute("points")
        self.assertTrue(attr.IsValid(), "Invalid output points attribute")
        test_points = attr.Get()

        # open the scene that has our 'answer key'
        await self._usd_context.open_stage_async(self._golden_file_path)
        self._stage = self._usd_context.get_stage()
        self.assertIsNotNone(self._stage)

        if self.WRITE_TEST_RESULTS:
            resultsPrim = self._stage.DefinePrim("/test_ramp")
            attr = resultsPrim.CreateAttribute("points", Sdf.ValueTypeNames.Point3fArray)
            attr.Set(test_points)
        else:
            resultsPrim = self._stage.GetPrimAtPath("/test_ramp")
            self.assertTrue(resultsPrim.IsValid(), "Invalid results prim")
            attr = resultsPrim.GetAttribute("points")
            self.assertTrue(attr.IsValid(), "Invalid results attribute")
            points = attr.Get()
            self.assertTrue(
                len(points) == len(test_points),
                "Test points count does not match reference points count ({} vs {})".format(
                    len(test_points), len(points)
                ),
            )
            for (point, test_point) in zip(points, test_points):
                self.assertTrue(
                    Gf.IsClose(point, test_point, self._smallNumber),
                    "Test point {} is not close to reference point {}".format(test_point, point),
                )

    async def test_color_ramp(self):
        await self.setupStage("particle_system_color_ramp_tests.usda")
        self._golden_file_path = str(self._usd_path.joinpath("golden_data_color_ramp.usda").absolute())

        # disable the settings that require viewport access, since we haven't set one up in this test
        self._geo_rep_node = self._graph.get_node("/World/effect/geometry_replicator")
        self._geo_rep_node.get_attribute("inputs:faceActiveCamera").set(False)
        self._geo_rep_node.get_attribute("inputs:orientWithActiveCamera").set(False)
        self._geo_rep_node.get_attribute("inputs:inheritParticleColorAndOpacity").set(True)

        self._emitter_node = self._graph.get_node("/World/effect/emitter")
        self._emitter_node.get_attribute("inputs:generateColorAndOpacity").set(True)

        # use random colors and opacity
        self._emitter_node.get_attribute("inputs:colorRandom").set([1, 1, 1])
        self._emitter_node.get_attribute("inputs:opacityRandom").set(1)
        reference_color = [0, 0, 0]
        reference_opacity = 0
        self._emitter_node.get_attribute("inputs:color").set(reference_color)
        self._emitter_node.get_attribute("inputs:opacity").set(reference_opacity)

        # turn on the solver
        solver_node = self._graph.get_node(f"/World/effect/solver")
        solver_node.get_attribute("inputs:active").set(True)

        # let the particle system play -- we'll let it run for a while to give collisions a chance to occur
        for _ in range(50):
            await omni.kit.app.get_app().next_update_async()

        outputPrim = self._stage.GetPrimAtPath("/World/output")
        self.assertTrue(outputPrim.IsValid(), "Invalid output prim")
        attr = outputPrim.GetAttribute("points")
        self.assertTrue(attr.IsValid(), "Invalid output points attribute")
        test_points = attr.Get()

        attr = outputPrim.GetAttribute("primvars:displayColor")
        self.assertTrue(attr.IsValid(), "Invalid output colors attribute")
        test_colors = attr.Get()
        attr = outputPrim.GetAttribute("primvars:displayColor:indices")
        self.assertTrue(attr.IsValid(), "Invalid output color indices attribute")
        test_color_indices = attr.Get()

        attr = outputPrim.GetAttribute("primvars:displayOpacity")
        self.assertTrue(attr.IsValid(), "Invalid output opacities attribute")
        test_opacities = attr.Get()
        attr = outputPrim.GetAttribute("primvars:displayOpacity:indices")
        self.assertTrue(attr.IsValid(), "Invalid output opacity indices attribute")
        test_opacity_indices = attr.Get()

        # open the scene that has our 'answer key'
        await self._usd_context.open_stage_async(self._golden_file_path)
        self._stage = self._usd_context.get_stage()
        self.assertIsNotNone(self._stage)

        if self.WRITE_TEST_RESULTS:
            resultsPrim = self._stage.DefinePrim("/test_ramp")
            attr = resultsPrim.CreateAttribute("points", Sdf.ValueTypeNames.Point3fArray)
            attr.Set(test_points)
            attr = resultsPrim.CreateAttribute("primvars:displayColor", Sdf.ValueTypeNames.Float3Array)
            attr.Set(test_colors)
            attr = resultsPrim.CreateAttribute("primvars:displayColor:indices", Sdf.ValueTypeNames.IntArray)
            attr.Set(test_color_indices)
            attr = resultsPrim.CreateAttribute("primvars:displayOpacity", Sdf.ValueTypeNames.FloatArray)
            attr.Set(test_opacities)
            attr = resultsPrim.CreateAttribute("primvars:displayOpacity:indices", Sdf.ValueTypeNames.IntArray)
            attr.Set(test_opacity_indices)
        else:
            resultsPrim = self._stage.GetPrimAtPath("/test_ramp")
            self.assertTrue(resultsPrim.IsValid(), "Invalid results prim")
            attr = resultsPrim.GetAttribute("points")
            self.assertTrue(attr.IsValid(), "Invalid results attribute")
            points = attr.Get()
            self.assertTrue(
                len(points) == len(test_points),
                "Test points count does not match reference points count ({} vs {})".format(
                    len(test_points), len(points)
                ),
            )
            for (point, test_point) in zip(points, test_points):
                self.assertTrue(
                    Gf.IsClose(point, test_point, self._smallNumber),
                    "Test point {} is not close to reference point {}".format(test_point, point),
                )

            attr = resultsPrim.GetAttribute("primvars:displayColor")
            self.assertTrue(attr.IsValid(), "Invalid output attribute")
            out_colors = attr.Get()
            attr = resultsPrim.GetAttribute("primvars:displayColor:indices")
            self.assertTrue(attr.IsValid(), "Invalid output attribute")
            out_color_indices = attr.Get()

            attr = resultsPrim.GetAttribute("primvars:displayOpacity")
            self.assertTrue(attr.IsValid(), "Invalid output attribute")
            out_opacities = attr.Get()
            attr = resultsPrim.GetAttribute("primvars:displayOpacity:indices")
            self.assertTrue(attr.IsValid(), "Invalid output attribute")
            out_opacity_indices = attr.Get()

            self.assertTrue(
                len(out_colors) == len(test_colors),
                "Output color count does not match reference color count ({} vs {})".format(
                    len(out_colors), len(test_colors)
                ),
            )
            self.assertTrue(
                len(out_color_indices) == len(test_color_indices),
                "Output color index count does not match reference color index count ({} vs {})".format(
                    len(out_color_indices), len(test_color_indices)
                ),
            )
            self.assertTrue(
                len(out_opacities) == len(test_opacities),
                "Output opacity count does not match reference opacity count ({} vs {})".format(
                    len(out_opacities), len(test_opacities)
                ),
            )
            self.assertTrue(
                len(out_opacity_indices) == len(test_opacity_indices),
                "Output opacity index count does not match reference opacity index count ({} vs {})".format(
                    len(out_opacity_indices), len(test_opacity_indices)
                ),
            )

            for (color, test_color) in zip(out_colors, test_colors):
                self.assertTrue(
                    Gf.IsClose(color, test_color, self._smallNumber),
                    "Test color {} is not close to reference color {}".format(test_color, color),
                )

            for (idx, test_idx) in zip(out_color_indices, test_color_indices):
                self.assertTrue(
                    idx == test_idx, "Test color index {} does not match reference color index {}".format(test_idx, idx)
                )

            for (opacity, test_opacity) in zip(out_opacities, test_opacities):
                self.assertTrue(
                    Gf.IsClose(opacity, test_opacity, self._smallNumber),
                    "Test opacity {} is not close to reference opacity {}".format(test_opacity, opacity),
                )

            for (idx, test_idx) in zip(out_opacity_indices, test_opacity_indices):
                self.assertTrue(
                    idx == test_idx,
                    "Test opacity index {} does not match reference opacity index {}".format(test_idx, idx),
                )
"""
