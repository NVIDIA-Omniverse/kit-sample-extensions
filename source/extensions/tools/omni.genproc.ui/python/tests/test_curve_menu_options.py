## Copyright (c) 2022, NVIDIA CORPORATION.  All rights reserved.
##
## NVIDIA CORPORATION and its licensors retain all intellectual property
## and proprietary rights in and to this software, related documentation
## and any modifications thereto.  Any use, reproduction, disclosure or
## distribution of this software and related documentation without an express
## license agreement from NVIDIA CORPORATION is strictly prohibited.
##

import pathlib
from pathlib import Path

import omni.graph.core as og
import omni.kit
import omni.kit.app
import omni.usd
from omni.genproc.ui.scripts.core import Core
from omni.kit.test.async_unittest import AsyncTestCase

EXTENSION_FOLDER_PATH = Path(omni.kit.app.get_app().get_extension_manager().get_extension_path_by_module(__name__))
TEST_DATA_PATH = EXTENSION_FOLDER_PATH.joinpath("data/tests")

# Note: these tests are now largely subsumed by their counterparts in test_menus, which exercise more
# of the extension's code by simulating mouse clicks on the actual menu options.
# However, from a coverage standpoint these tests still contribute a very small amount of additional
# coverage, so we've left them in for now.


class TestCurveMenus(AsyncTestCase):

    TEST_GRAPH_PATH = "/World/TestGraph"

    async def setUp(self):
        self._usd_context = omni.usd.get_context()
        usd_path = TEST_DATA_PATH.absolute()
        test_file_path = str(usd_path.joinpath("curve_menu_tests.usda").absolute())
        await self._usd_context.open_stage_async(test_file_path)

        self._stage = self._usd_context.get_stage()
        self.assertIsNotNone(self._stage)

        og.Controller.edit({"graph_path": self.TEST_GRAPH_PATH, "evaluator_name": "push"})

        self._core = Core()
        self._core.on_startup()

    async def tearDown(self):
        self._core.on_shutdown()
        await self._usd_context.new_stage_async()
        self._core = None
        self._stage = None
        self._usd_context = None

    async def test_curve_from_xformables_core(self):

        self._core.curve_from_xformables(
            graph_path=self.TEST_GRAPH_PATH, xformable_paths=["/World/Cube_{:02d}".format(i) for i in range(1, 5)]
        )

        self.assertTrue(self._stage.GetPrimAtPath("{}/transforms_to_curve".format(self.TEST_GRAPH_PATH)).IsValid())

    async def test_get_curve_data_core(self):

        self._core.get_curve_data(graph_path=self.TEST_GRAPH_PATH, curve_paths=["/World/BasisCurves"])

        self.assertTrue(self._stage.GetPrimAtPath("{}/get_curve_data".format(self.TEST_GRAPH_PATH)).IsValid())

    async def test_curves_with_ramp_core(self):

        self._core.tag_curves_with_ramp(graph_path=self.TEST_GRAPH_PATH, curve_paths=["/World/BasisCurves"])

        self.assertTrue(self._stage.GetPrimAtPath("{}/tag_curves".format(self.TEST_GRAPH_PATH)).IsValid())

    async def test_resample_curves_core(self):

        self._core.resample_curves(graph_path=self.TEST_GRAPH_PATH, curve_paths=["/World/BasisCurves"])

        self.assertTrue(self._stage.GetPrimAtPath("{}/resample_curves".format(self.TEST_GRAPH_PATH)).IsValid())
