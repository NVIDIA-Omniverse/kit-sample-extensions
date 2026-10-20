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
import sys
import unittest

import omni.kit
import omni.kit.app
import omni.usd
from omni.genproc.ui.scripts import curve_zone_sign_menu as ZoneSignMenu
from omni.kit import ui_test
from omni.kit.test.async_unittest import AsyncTestCase
from omni.kit.test_suite.helpers import wait_for_viewport_ready
from omni.kit.ui_test import Vec2
from pxr import Sdf, Usd

EXTENSION_FOLDER_PATH = pathlib.Path(
    omni.kit.app.get_app().get_extension_manager().get_extension_path_by_module(__name__)
)
TEST_DATA_PATH = EXTENSION_FOLDER_PATH.joinpath("data/tests")


class TestZoneSignMenu(AsyncTestCase):
    # Before running each test
    async def setUp(self):
        await wait_for_viewport_ready()
        # setup
        await ui_test.find("Stage").focus()
        self._viewport = ui_test.find("Viewport")
        await self._viewport.focus()

        self.usd_context = omni.usd.get_context()
        self._usd_path = TEST_DATA_PATH.absolute()
        self.test_file_path = str(self._usd_path.joinpath("curve_menu_tests.usda").absolute())
        await self.usd_context.open_stage_async(self.test_file_path)

        self._stage = self.usd_context.get_stage()
        self.assertIsNotNone(self._stage)

    # After running each test
    async def tearDown(self):
        self._viewport = None
        usd_context = omni.usd.get_context()
        await usd_context.new_stage_async()

    @unittest.skipIf(sys.platform.startswith("linux"), "OM-89473 flaky in linux viewport next")
    async def test_add_zone_sign(self):
        self._stage = self.usd_context.get_stage()
        prim = self._stage.GetPrimAtPath("/World/BasisCurves")

        # click on menu item
        omni.usd.get_context().get_selection().set_selected_prim_paths(["/World/BasisCurves"], True)
        await ui_test.human_delay(20)
        await self._viewport.right_click()
        await ui_test.human_delay(20)
        await ui_test.select_context_menu(f"Add/{ZoneSignMenu.ZONE_SIGN_ADDITIVE_MENU_ENTRY}", offset=Vec2(10, 10))
        await ui_test.human_delay()

        zoneSignAttr = prim.GetAttribute(ZoneSignMenu.ZONE_SIGN_ATTRIBUTE_NAME)
        self.assertTrue(zoneSignAttr)
        self.assertEqual(zoneSignAttr.Get(), ZoneSignMenu.ZONE_SIGN_ADDITIVE_ATTRIBUTE_VALUE)

        omni.usd.get_context().get_selection().set_selected_prim_paths(["/World/BasisCurves"], True)
        await ui_test.human_delay(20)
        await self._viewport.right_click()
        await ui_test.human_delay(20)
        await ui_test.select_context_menu(f"Add/{ZoneSignMenu.ZONE_SIGN_SUBTRACTIVE_MENU_ENTRY}", offset=Vec2(10, 10))
        await ui_test.human_delay()

        self.assertEqual(zoneSignAttr.Get(), ZoneSignMenu.ZONE_SIGN_SUBTRACTIVE_ATTRIBUTE_VALUE)
