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

import omni.kit.test
import omni.kit.undo
import omni.usd
from omni.kit.environment.core import get_sunstudy_player, import_environment
from omni.kit.test import AsyncTestCase
from pxr import UsdGeom

from ..sky import SkyHelper

CURRENT_PATH = Path(__file__).parent
TEST_DATA_PATH = CURRENT_PATH.parent.parent.parent.parent.parent.joinpath("data").joinpath("tests")
SKIES_PATH = f"{TEST_DATA_PATH}/Skies"


class TestPlayDymanicSky(AsyncTestCase):
    async def setUp(self):
        self.usd_context_name = ""
        self.usd_context = omni.usd.get_context(self.usd_context_name)
        await self.usd_context.new_stage_async()
        self.stage = self.usd_context.get_stage()

        self.stage.SetDefaultPrim(UsdGeom.Xform.Define(self.stage, "/World").GetPrim())

        self._player = get_sunstudy_player()

    async def tearDown(self):
        self._helper = None
        self.usd_context = None
        self.stage = None

    async def test_play(self):
        self.assertFalse(self._player._playing_model.as_bool)

        # Default no dynamic sky, can not play
        result = self._player.start()
        self.assertFalse(result)

        # Apply dynamic sky
        self.usd_context = omni.usd.get_context()
        await self.usd_context.new_stage_async()

        sky_url = f"{SKIES_PATH}/Dynamic/sunstudy.usd"
        sky_type = SkyHelper.get_env_file_type(sky_url)
        import_environment(sky_type, sky_url)
        for _ in range(10):
            await omni.kit.app.get_app().next_update_async()

        # Play with dynamic sky
        result = self._player.start()
        self.assertTrue(result)
        self.assertTrue(self._player._playing_model.as_bool)

        while self._player._playing_model.as_bool:
            await omni.kit.app.get_app().next_update_async()
