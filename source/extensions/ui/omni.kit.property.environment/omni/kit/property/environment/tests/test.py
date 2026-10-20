# SPDX-FileCopyrightText: Copyright (c) 2021-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
import asyncio
from pathlib import Path

import omni.kit.app
import omni.kit.commands
import omni.kit.test
import omni.usd
from omni.kit.environment.core import SkyHelper
from omni.kit.test_suite.helpers import wait_stage_loading
from omni.ui.tests.test_base import OmniUiTest

CURRENT_PATH = Path(__file__).parent
TEST_DATA_PATH = CURRENT_PATH.parent.parent.parent.parent.parent.joinpath("data").joinpath("tests")
SKIES_PATH = "https://omniverse-content-production.s3.us-west-2.amazonaws.com/Assets/Skies/2022_1/Skies/"


class TestEnvironmentWidget(OmniUiTest):
    # Before running each test
    async def setUp(self):
        await super().setUp()

        omni.kit.window.property.managed_frame.reset_collapsed_state()
        omni.kit.window.property.managed_frame.set_collapsed_state("Property/Materials on selected models", True)

        self._golden_img_dir = TEST_DATA_PATH.absolute().joinpath("golden_img").absolute()

        import omni.kit.window.property as p

        self._w = p.get_window()

    # After running each test
    async def tearDown(self):
        await super().tearDown()
        omni.kit.window.property.managed_frame.reset_collapsed_state()

    async def test_dynamic_ui(self):
        await self._load_and_compare(f"{SKIES_PATH}/Dynamic/CloudySky.usd", "env_property_dynamic")

    async def test_hdri_ui(self):
        await self._load_and_compare(f"{SKIES_PATH}/Evening/evening_road_01.hdr", "env_property_hdri")

    async def _load_and_compare(self, sky_url: str, image_name: str):
        usd_context = omni.usd.get_context()

        await self.docked_test_window(
            window=self._w._window,
            width=450,
            height=750,
        )

        omni.usd.get_context().new_stage()
        await omni.kit.app.get_app().next_update_async()
        try:
            from omni.kit.actions.core import get_action_registry

            action_registry = get_action_registry()
            action = action_registry.get_action("omni.kit.environment.core", "import")
            sky_type = SkyHelper.get_env_file_type(sky_url)
            action.execute(sky_type, sky_url)
        except ImportError:
            from omni.kit.environment.core import import_environment

            sky_type = SkyHelper.get_env_file_type(sky_url)
            import_environment(sky_type, sky_url)

        await asyncio.sleep(10)
        await omni.kit.app.get_app().next_update_async()

        # Select the prim.
        usd_context.get_selection().set_selected_prim_paths(["/Environment"], True)

        # Need to wait for an additional frames for omni.ui rebuild to take effect
        await self.wait_for_update(usd_context)

        image_name = self.__get_full_file_name(image_name)
        await self.finalize_test(golden_img_dir=self._golden_img_dir, golden_img_name=image_name)

    def __get_full_file_name(self, image_name) -> str:
        try:
            # Serach bar enanbled in property window in kit 105
            import omni.kit.widget.searchfield

            image_name += "_search"
        except:
            pass
        image_name += ".png"

        return image_name

    async def wait_for_update(self, usd_context=omni.usd.get_context(), wait_frames=10):
        max_loops = 0
        while max_loops < wait_frames:
            _, files_loaded, total_files = usd_context.get_stage_loading_status()
            await omni.kit.app.get_app().next_update_async()
            if files_loaded or total_files:
                continue
            max_loops = max_loops + 1
