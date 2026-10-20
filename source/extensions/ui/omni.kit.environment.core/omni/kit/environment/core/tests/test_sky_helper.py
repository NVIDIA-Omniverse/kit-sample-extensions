# SPDX-FileCopyrightText: Copyright (c) 2022-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
## NVIDIA CORPORATION and its licensors retain all intellectual property
## and proprietary rights in and to this software, related documentation
## and any modifications thereto.  Any use, reproduction, disclosure or
## distribution of this software and related documentation without an express
## license agreement from NVIDIA CORPORATION is strictly prohibited.
##
from pathlib import Path

import carb
import omni.kit.test
import omni.kit.undo
import omni.usd
from omni.kit.environment.core import EnvironmentSettings
from omni.kit.test import AsyncTestCase
from pxr import UsdGeom

from ..sky import SkyHelper

CURRENT_PATH = Path(__file__).parent
TEST_DATA_PATH = CURRENT_PATH.parent.parent.parent.parent.parent.joinpath("data").joinpath("tests")


class TestSkyHelper(AsyncTestCase):
    async def setUp(self):
        self.usd_context_name = ""
        self.usd_context = omni.usd.get_context(self.usd_context_name)
        await self.usd_context.new_stage_async()
        self.stage = self.usd_context.get_stage()

        self.stage.SetDefaultPrim(UsdGeom.Xform.Define(self.stage, "/World").GetPrim())

        self._helper = SkyHelper()

    async def tearDown(self):
        self._helper = None
        self.usd_context = None
        self.stage = None

    async def test_default_sky(self):
        settings = carb.settings.get_settings()
        saved_auto_sky = settings.get(EnvironmentSettings.ENV_AUTO)
        saved_default_sky = settings.get(EnvironmentSettings.ENV_DEFAULT)
        settings.set(EnvironmentSettings.ENV_DEFAULT, f"{TEST_DATA_PATH}/Skies/Dynamic/simple.usd")
        settings.set(EnvironmentSettings.ENV_AUTO, True)

        try:
            await self.usd_context.new_stage_async()

            for _ in range(10):
                await omni.kit.app.get_app().next_update_async()

            path, _ = self._helper.find_sky()
            self.assertIsNotNone(path)
        finally:
            settings.set(EnvironmentSettings.ENV_AUTO, saved_auto_sky)
            settings.set(EnvironmentSettings.ENV_DEFAULT, saved_default_sky)
