# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

import carb
import omni.kit.test
import omni.ui as ui
import omni.usd
from omni.kit import ui_test
from omni.kit.test_suite.helpers import (
    arrange_windows,
    get_prims,
    get_test_data_path,
    open_stage,
    select_prims,
    wait_stage_loading,
)
from omni.ui.tests.test_base import OmniUiTest
from pxr import Gf, Sdf, Usd, UsdGeom


class TestReopenWindow(OmniUiTest):
    async def setUp(self):
        await omni.usd.get_context().new_stage_async()
        await arrange_windows("Stage", 64)

    async def tearDown(self):
        pass

    async def test_reopen_window(self):
        if not hasattr(omni.kit.property.usd, "get_registered_schemas"):
            carb.log_warn("not compatible with this version of omni.kit.property.usd. Version 4.3.0+ is required")
            return

        await ui_test.find("Stage").focus()

        await open_stage(get_test_data_path(__name__, "bound_shapes.usda"))
        stage = omni.usd.get_context().get_stage()

        # select prim
        await select_prims(["/World/Cone"])
        await ui_test.human_delay(10)

        for i in range(1, 10):
            for widget in ui_test.find_all("Property//Frame/**/Button[*]"):
                if widget.widget.text.endswith(" Add"):
                    # click +Add
                    await widget.click()
                    await ui_test.human_delay()
                    await ui_test.select_context_menu("Edit API Schema  ", offset=ui_test.Vec2(10, 10))

                    window = ui.Workspace.get_window("Edit API Schema")
                    self.assertIsNotNone(window)
                    self.assertTrue(window.visible)

                    window.visible = False
                    await ui_test.human_delay(10)
