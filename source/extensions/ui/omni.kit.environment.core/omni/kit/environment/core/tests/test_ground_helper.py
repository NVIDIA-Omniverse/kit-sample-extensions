# SPDX-FileCopyrightText: Copyright (c) 2021-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
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
import asyncio
import traceback
from pathlib import Path

import carb
import carb.input
import carb.settings
import carb.tokens
import omni.kit.app
import omni.kit.test
import omni.ui as ui
import omni.usd
from omni.kit.environment.core import EnvironmentProperties, EnvironmentSettings, GroundHelper, GroundType
from omni.kit.viewport.utility import capture_viewport_to_file, get_active_viewport
from omni.ui.tests.compare_utils import CompareError, compare
from omni.ui.tests.test_base import OmniUiTest
from pxr import Usd

CURRENT_PATH = Path(__file__).parent
TEST_DATA_PATH = CURRENT_PATH.parent.parent.parent.parent.parent.joinpath("data").joinpath("tests")
GOLDEN_IMAGE_PATH = TEST_DATA_PATH.joinpath("golden_img")
DEFAULT_CAMPOSY_PATH = "/app/viewport/defaultCamPos/y"
OUTPUTS_DIR = Path(omni.kit.test.get_test_output_path())


class TestGroundHelper(OmniUiTest):
    # Before running each test
    async def setUp(self):
        await super().setUp()

        self.__settings = carb.settings.get_settings()
        self.__settings.set(DEFAULT_CAMPOSY_PATH, 25)
        self.__saved_ground = self.__settings.get(EnvironmentSettings.GROUND_ENABLE)

        self._helper = GroundHelper()

    # After running each test
    async def tearDown(self):
        self._stage_sub = None
        self.__settings.set(EnvironmentSettings.GROUND_ENABLE, self.__saved_ground)
        await super().tearDown()

    async def test_create_ground(self):
        ground_prim = self._helper.find_ground()
        self.assertIsNone(ground_prim)

        self.__settings.set(EnvironmentSettings.GROUND_ENABLE, True)

        await omni.usd.get_context().new_stage_async()

        # Wait for ground loaded
        await asyncio.sleep(20)
        await self._capture_viewport_and_compare("ground")

        self.assertEqual(self._helper.ground_material, "/Environment/Looks/Ground")
        self._helper._ground_type_model.set_value(GroundType.SHADOWS)
        await self.wait_n_updates(4)
        self.assertEqual(GroundHelper().ground_material, "")

    async def _capture_viewport_and_compare(self, image_name: str, threshold=100):
        capture_filename = OUTPUTS_DIR.joinpath(image_name + ".png")
        golden_filename = GOLDEN_IMAGE_PATH.joinpath(image_name + ".png")
        differ_filename = OUTPUTS_DIR.joinpath(image_name + ".differmap.png")
        carb.settings.get_settings().set("/persistent/app/viewport/displayOptions", 0)

        import omni.kit.app

        await omni.kit.app.get_app().next_update_async()
        viewport_api = get_active_viewport()
        capture_viewport_to_file(viewport_api, capture_filename)
        await omni.kit.app.get_app().next_update_async()
        while True:
            # Sometime there will be error "Permission denied" when opening capture file
            # Make sure file could be read here
            result, _, _ = omni.client.read_file(str(capture_filename))
            if result == omni.client.Result.OK:
                break
            else:
                await omni.kit.app.get_app().next_update_async()

        try:
            diff = compare(capture_filename, golden_filename, differ_filename)
            if diff >= threshold:
                print(f"##teamcity[publishArtifacts '{capture_filename} => results']")
                print(f"##teamcity[publishArtifacts '{differ_filename} => results']")
                print(f"##teamcity[publishArtifacts '{golden_filename} => golden']")
            return diff
        except CompareError as e:
            carb.log_error(f"[omni.ui.tests.compare] Failed to compare images for {image_name}. Error: {e}")
            exc = traceback.format_exc()
            carb.log_error(f"[omni.ui.tests.compare] Traceback:\n{exc}")
