## Copyright (c) 2022, NVIDIA CORPORATION.  All rights reserved.
##
## NVIDIA CORPORATION and its licensors retain all intellectual property
## and proprietary rights in and to this software, related documentation
## and any modifications thereto.  Any use, reproduction, disclosure or
## distribution of this software and related documentation without an express
## license agreement from NVIDIA CORPORATION is strictly prohibited.
##

import pathlib
import platform
import sys
import unittest

import carb.settings
import omni.kit
import omni.kit.app
import omni.usd
from omni.kit.test.async_unittest import AsyncTestCase
from pxr import Gf, UsdGeom

EXTENSION_FOLDER_PATH = pathlib.Path(
    omni.kit.app.get_app().get_extension_manager().get_extension_path_by_module(__name__)
)
TEST_DATA_PATH = EXTENSION_FOLDER_PATH.joinpath("data/tests/stage")


class TestCamera(AsyncTestCase):
    # Before running each test
    async def setUp(self):
        self._usd_context = omni.usd.get_context()
        self._stage = None

    # After running each test
    async def tearDown(self):
        if self._stage:
            await self._usd_context.close_stage_async()
            await omni.kit.app.get_app().next_update_async()

    async def setupStage(self, filepath):
        self._usd_path = TEST_DATA_PATH.absolute()
        test_file_path = str(self._usd_path.joinpath(filepath).absolute())

        await self._usd_context.open_stage_async(test_file_path)
        self._stage = self._usd_context.get_stage()
        self.assertIsNotNone(self._stage)

    # If the default perspective camera is outside the stage's bounding box and/or looks
    # away from it, a stage-loaded callback will reposition and reorient it (the camera).
    # In addition to that, if the camera has a "roll" it will be removed by aligning it
    # (the camera) vertically.
    # This test requires FSD to be enabled.
    @unittest.skipIf(platform.processor() == "aarch64", "Unstable when running on linux aarch64")
    async def test_camera_initialization(self):
        settings = carb.settings.get_settings()
        fabric_enable = settings.get("/app/useFabricSceneDelegate")
        if not fabric_enable:
            return
        await self.setupStage("test_scene_2.usd")
        p = self._usd_context.get_stage().GetPrimAtPath("/OmniverseKit_Persp")
        m = UsdGeom.XformCache(0).GetLocalToWorldTransform(p)
        m2 = Gf.Matrix4d(
            (0.7071067811865477, 0, -0.7071067811865477, 0),
            (-0.40824829046386313, 0.8164965809277263, -0.40824829046386313, 0),
            (0.5773502691896258, 0.5773502691896258, 0.5773502691896258, 0),
            (1050, 1050, 1050, 1),
        )
        self.assertEqual(m, m2)
