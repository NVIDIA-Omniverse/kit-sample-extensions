# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
from pathlib import Path
from typing import Iterable

import carb.settings
import omni.kit.ui_test as ui_test
import omni.ui as ui
import omni.usd
from omni.kit.viewport.utility import get_active_viewport, get_active_viewport_window
from omni.ui.tests.test_base import OmniUiTest

from ..teleport import Teleport

CURRENT_PATH = Path(__file__).parent
TEST_DATA_PATH = CURRENT_PATH.parent.parent.parent.parent.parent.joinpath("data").joinpath("tests")
TEST_OBJECT_PRIM_PATH = "/test_obj"
SETTING_SHOW_POSITION = "exts/omni.kit.tool.teleport/showPosition"


# -- TRANSITION FOR SUPPORTING BOTH VP1 AND VP2
def is_viewport_legacy():
    viewport_api = get_active_viewport()
    return hasattr(viewport_api, "legacy_window")


# -- TRANSITION END


def is_near_point(p1, p2):
    return (abs(p1[0] - p2[0]) + abs(p1[1] - p2[1]) + abs(p1[2] - p2[2])) < 1


class TestTeleportBase(OmniUiTest):

    async def setUp(self):
        await super().setUp()
        usd_context = omni.usd.get_context()
        if not usd_context.get_stage():
            await usd_context.new_stage_async()
            await ui_test.human_delay(8)
        self._settings = carb.settings.get_settings()
        self._golden_img_dir = TEST_DATA_PATH.absolute().joinpath("golden_img").absolute()
        self._teleport = Teleport.get_instance(test=True)
        self._teleport.set_active(True, test=True)
        await ui_test.human_delay(8)
        await ui_test.wait_n_updates(300)
        if is_viewport_legacy():
            self._golden_img_dir = self._golden_img_dir.joinpath("legacy")

    # After running each test
    async def tearDown(self):
        usd_context = omni.usd.get_context()
        self._teleport.set_active(False)
        # TODO: why this cause the 105.2 linux test failed?
        # await usd_context.close_stage_async()
        carb.settings.get_settings().set(SETTING_SHOW_POSITION, False)
        self._teleport = None
        await super().tearDown()

    async def _dock_viewport(self, width=1200, height=900, block_device=False):
        """Utility function to dock viewport window and focus on turntable panel."""
        viewport = get_active_viewport_window()
        await self.docked_test_window(window=viewport, width=width, height=height, block_devices=block_device)
        await ui_test.wait_n_updates()

    async def _reset_camera(self, cam_path, cam_mtx):
        omni.kit.commands.create(
            "TransformPrimCommand", path=cam_path, new_transform_matrix=cam_mtx, usd_context_name=""
        ).do()
        await omni.kit.app.get_app().next_update_async()


def create_test_object(prim_path=TEST_OBJECT_PRIM_PATH, prim_type="Plane", attrs=None):
    kwargs = {"prim_type": prim_type, "prim_path": prim_path}
    if attrs:
        kwargs["attributes"] = attrs
    omni.kit.commands.execute("CreatePrimWithDefaultXform", **kwargs)
