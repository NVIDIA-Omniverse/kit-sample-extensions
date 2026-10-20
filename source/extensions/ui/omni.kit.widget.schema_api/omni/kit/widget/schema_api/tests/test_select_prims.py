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


class TestSelectPrims(OmniUiTest):
    async def setUp(self):
        await omni.usd.get_context().new_stage_async()
        await arrange_windows("Stage", 64)

    async def tearDown(self):
        pass

    async def test_select_prims(self):
        if not hasattr(omni.kit.property.usd, "get_registered_schemas"):
            carb.log_warn("not compatible with this version of omni.kit.property.usd. Version 4.3.0+ is required")
            return

        await ui_test.find("Stage").focus()

        await open_stage(get_test_data_path(__name__, "bound_shapes.usda"))
        await wait_stage_loading()

        stage = omni.usd.get_context().get_stage()
        for prim in get_prims(stage):
            await select_prims([prim.GetPath().pathString])
            await ui_test.human_delay(10)
            await select_prims([])
            await ui_test.human_delay(10)
