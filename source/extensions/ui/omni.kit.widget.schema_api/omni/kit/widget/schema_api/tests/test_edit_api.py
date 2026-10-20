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
    get_test_data_path,
    open_stage,
    select_prims,
    wait_stage_loading,
)
from omni.ui.tests.test_base import OmniUiTest
from pxr import Gf, Sdf, Usd, UsdGeom


class TestEditAPI(OmniUiTest):
    async def setUp(self):
        await omni.usd.get_context().new_stage_async()
        await arrange_windows("Stage", 64)

    async def tearDown(self):
        pass

    async def test_add_schema_api(self):
        if not hasattr(omni.kit.property.usd, "get_registered_schemas"):
            carb.log_warn("not compatible with this version of omni.kit.property.usd. Version 4.3.0+ is required")
            return

        await ui_test.find("Stage").focus()

        await open_stage(get_test_data_path(__name__, "bound_shapes.usda"))
        stage = omni.usd.get_context().get_stage()

        # select prim
        await select_prims(["/World/Cone"])
        await ui_test.human_delay(10)

        # test "+add" menu
        def hide_widgets():
            # collapse unwanted frames
            for widget_ref in ui_test.find_all("Property//Frame/**/CollapsableFrame[*]"):
                widget_ref.widget.collapsed = True

                if widget_ref.widget.title in ["Geometry"]:
                    widget_ref.widget.collapsed = False

        async def click_item(item_name):
            for w in ui_test.find_all("Edit API Schema//Frame/**/"):
                if w.widget.identifier == "listbox":
                    await w.click()
                    await ui_test.human_delay(10)

                    api_items = ui_test.find(
                        "APISearchWindow//Frame/**/.identifier=='search_view'"
                    ).model.get_item_children(None)
                    widget = ui_test.find(f"APISearchWindow//Frame/**/Label[*].text=='{item_name}'")
                    await widget.click()
                    await ui_test.human_delay(10)

        for widget in ui_test.find_all("Property//Frame/**/Button[*]"):
            if widget.widget.text.endswith(" Add"):
                # click +Add
                await widget.click()
                await ui_test.human_delay()
                await ui_test.select_context_menu("Edit API Schema  ", offset=ui_test.Vec2(10, 10))
                await ui_test.human_delay(10)

                # add API
                await click_item("CollectionAPI:allShapes")
                hide_widgets()

                # remove API from property window
                await ui_test.find(
                    "Property//Frame/**/Button[*].identifier=='CollectionAPI:allShapes.remove_api_schema_button'"
                ).click()
                await ui_test.human_delay(10)

                # add API
                await click_item("CollectionAPI:allGeom")
                hide_widgets()
                await ui_test.find(
                    "Edit API Schema//Frame/**/Button[*].identifier=='CollectionAPI:allGeom.remove_api_schema_button'"
                ).click()
                await ui_test.human_delay(10)

        # change selection to update window
        await select_prims(["/World"])
        await ui_test.human_delay(10)

        # close the stage to close the window
        await omni.usd.get_context().close_stage_async()

        await ui_test.human_delay(10)
