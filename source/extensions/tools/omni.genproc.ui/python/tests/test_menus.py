## Copyright (c) 2022, NVIDIA CORPORATION.  All rights reserved.
##
## NVIDIA CORPORATION and its licensors retain all intellectual property
## and proprietary rights in and to this software, related documentation
## and any modifications thereto.  Any use, reproduction, disclosure or
## distribution of this software and related documentation without an express
## license agreement from NVIDIA CORPORATION is strictly prohibited.
##
import os
import pathlib

import omni.graph.core as og
import omni.kit
import omni.kit.app
import omni.kit.menu
import omni.usd
from omni.genproc.ui.scripts import menu_common
from omni.kit import ui_test
from omni.ui.tests.test_base import OmniUiTest
from pxr import Sdf, Usd

EXTENSION_FOLDER_PATH = pathlib.Path(
    omni.kit.app.get_app().get_extension_manager().get_extension_path_by_module(__name__)
)
TEST_DATA_PATH = EXTENSION_FOLDER_PATH.joinpath("data/tests")


class TestGenprocMenus(OmniUiTest):

    TEST_GRAPH_PATH = "/World/TestGraph"

    async def setUp(self):
        self._usd_context = omni.usd.get_context()

        usd_path = TEST_DATA_PATH.absolute()
        test_file_path = str(usd_path.joinpath("curve_menu_tests.usda").absolute())
        await self._usd_context.open_stage_async(test_file_path)

        self._stage = self._usd_context.get_stage()
        self.assertIsNotNone(self._stage)

        og.Controller.edit({"graph_path": self.TEST_GRAPH_PATH, "evaluator_name": "push"})

        await omni.kit.app.get_app().next_update_async()

        stage_panel = ui_test.find("Stage")
        self.assertIsNotNone(stage_panel)
        await stage_panel.focus()
        self._viewport = ui_test.find("Viewport")
        self.assertIsNotNone(self._viewport)
        await self._viewport.focus()

        omni.kit.menu.utils.refresh_menu_items("Create")
        await ui_test.human_delay(10)

    async def tearDown(self):
        await self._usd_context.new_stage_async()
        self._viewport = None
        self._usd_context = None

    async def test_curve_from_xformables(self):
        graph_path = self.TEST_GRAPH_PATH
        xformable_paths = ["/World/Cube_{:02d}".format(i) for i in range(1, 5)]

        self._usd_context.get_selection().set_selected_prim_paths([graph_path, *xformable_paths], True)

        # click on menu item
        await ui_test.human_delay(10)
        await ui_test.menu_click(f"Create/BasisCurves/Graph/{menu_common.CURVE_FROM_XFORMABLES}")
        await ui_test.human_delay(10)

        # popup options are auto-populated based on selection; click 'ok'
        button = ui_test.find("Curve from Xformables//Frame/**/Button[*].identifier=='btn_ok'")
        self.assertIsNotNone(button, "Failed to find button for Curve from Xformables window")
        await button.click()
        await ui_test.wait_n_updates(10)

        self.assertTrue(self._stage.GetPrimAtPath("{}/transforms_to_curve".format(self.TEST_GRAPH_PATH)).IsValid())

    async def test_get_curve_data(self):
        graph_path = self.TEST_GRAPH_PATH
        curve_paths = ["/World/BasisCurves"]

        self._usd_context.get_selection().set_selected_prim_paths([graph_path, *curve_paths], True)

        # click on menu item
        await ui_test.human_delay(10)
        await ui_test.menu_click(f"Create/BasisCurves/Graph/{menu_common.GET_CURVE_DATA}")
        await ui_test.human_delay(10)

        # popup options are auto-populated based on selection; click 'ok'
        button = ui_test.find("Get Curve Data//Frame/**/Button[*].identifier=='btn_ok'")
        self.assertIsNotNone(button, "Failed to find button for Get Curve Data window")
        await button.click()
        await ui_test.wait_n_updates(10)

        self.assertTrue(self._stage.GetPrimAtPath("{}/get_curve_data".format(self.TEST_GRAPH_PATH)).IsValid())

    async def test_tag_curves_with_ramp(self):
        graph_path = self.TEST_GRAPH_PATH
        curve_paths = ["/World/BasisCurves"]

        self._usd_context.get_selection().set_selected_prim_paths([graph_path, *curve_paths], True)

        # click on menu item
        await ui_test.human_delay(10)
        await ui_test.menu_click(f"Create/BasisCurves/Graph/{menu_common.TAG_CURVES_WITH_RAMP}")
        await ui_test.human_delay(10)

        # popup options are auto-populated based on selection; click 'ok'
        button = ui_test.find("Tag Curves with Ramp//Frame/**/Button[*].identifier=='btn_ok'")
        self.assertIsNotNone(button, "Failed to find button for Tag Curves with Ramp window")
        await button.click()
        await ui_test.wait_n_updates(10)

        self.assertTrue(self._stage.GetPrimAtPath("{}/tag_curves".format(self.TEST_GRAPH_PATH)).IsValid())

    async def test_resample_curves(self):
        graph_path = self.TEST_GRAPH_PATH
        curve_paths = ["/World/BasisCurves"]

        self._usd_context.get_selection().set_selected_prim_paths([graph_path, *curve_paths], True)

        # click on menu item
        await ui_test.human_delay(10)
        await ui_test.menu_click(f"Create/BasisCurves/Graph/{menu_common.RESAMPLE_CURVES}")
        await ui_test.human_delay(10)

        # popup options are auto-populated based on selection; click 'ok'
        button = ui_test.find("Resample Curves//Frame/**/Button[*].identifier=='btn_ok'")
        self.assertIsNotNone(button, "Failed to find button for Resample Curves window")
        await button.click()
        await ui_test.wait_n_updates(10)

        self.assertTrue(self._stage.GetPrimAtPath("{}/resample_curves".format(self.TEST_GRAPH_PATH)).IsValid())
