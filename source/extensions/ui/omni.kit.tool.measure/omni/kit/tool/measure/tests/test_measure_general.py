# Copyright (c) 2022, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

from pathlib import Path

import omni.kit.app
import omni.kit.ui_test as ui_test
import omni.usd
from pxr import Sdf, Usd, UsdGeom, Vt

from .test_util import TestMeasureBase

CURRENT_PATH = Path(__file__).parent
TEST_DATA_PATH = CURRENT_PATH


class TestMeasureGeneral(TestMeasureBase):
    async def setUp(self):
        await super().setUp()

    async def tearDown(self):
        await super().tearDown()

    async def test_freebie(self):
        self.assertTrue(True)

    async def test_common_utils(self):
        from ..common import (
            convert_distance_and_units,
            equal_float,
            get_stage_meters_per_unit,
            get_stage_units,
            remap,
            remap_01,
        )
        from ..common.notification import (
            post_disreguard_future_notification,
            post_info_notification,
            post_warn_notification,
        )

        stage = omni.usd.get_context().get_stage()

        # Test all branches of get_stage_units()
        self.assertEqual(get_stage_units(), "cm")
        UsdGeom.SetStageMetersPerUnit(stage, UsdGeom.LinearUnits.millimeters)
        self.assertEqual(get_stage_units(), "mm")
        UsdGeom.SetStageMetersPerUnit(stage, UsdGeom.LinearUnits.meters)
        self.assertEqual(get_stage_units(), "m")
        UsdGeom.SetStageMetersPerUnit(stage, UsdGeom.LinearUnits.kilometers)
        self.assertEqual(get_stage_units(), "km")
        UsdGeom.SetStageMetersPerUnit(stage, UsdGeom.LinearUnits.inches)
        self.assertEqual(get_stage_units(), "in")
        UsdGeom.SetStageMetersPerUnit(stage, UsdGeom.LinearUnits.feet)
        self.assertEqual(get_stage_units(), "ft")
        UsdGeom.SetStageMetersPerUnit(stage, UsdGeom.LinearUnits.miles)
        self.assertEqual(get_stage_units(), "mi")
        # Test non-handled value type
        UsdGeom.SetStageMetersPerUnit(stage, UsdGeom.LinearUnits.yards)
        self.assertEqual(get_stage_units(), "x0.9144m")
        # Reset to CM (Default)
        UsdGeom.SetStageMetersPerUnit(stage, UsdGeom.LinearUnits.centimeters)

        self.assertAlmostEqual(get_stage_meters_per_unit(), 0.01)
        self.assertEqual(convert_distance_and_units(53.5, "m"), (0.535, "m"))
        self.assertFalse(equal_float(0.0, 1.0))
        self.assertEqual(remap(0.5, 0, 1, 0, 2, False), 1)
        self.assertEqual(remap_01(0.5, 0, 1, True), 0.5)

        post_info_notification("This is an info notification")
        await ui_test.human_delay(5)
        post_warn_notification("This is a warn notification")
        await ui_test.human_delay(5)
        post_disreguard_future_notification("This is a Disregard notification", lambda: None)
        await ui_test.human_delay(5)

        await self.wait_for_notifications(timeout_seconds=5.0)
        await self.dismiss_notification()
