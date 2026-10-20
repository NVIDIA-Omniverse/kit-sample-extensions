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
from omni.kit.test_suite.helpers import wait_stage_loading

from .utils import toggle_on_named_column


class TestVariant(omni.kit.test.AsyncTestCase):
    async def setUp(self):
        from pathlib import Path

        # get file path
        extension_path = omni.kit.app.get_app().get_extension_manager().get_extension_path_by_module(__name__)
        await omni.usd.get_context().open_stage_async(str(Path(extension_path).joinpath("data/tests/Cup.usd")))
        await wait_stage_loading()
        # Show Variant column - stage options menu in a ui.TreeView inside a ui.Menu
        await toggle_on_named_column("Variant")

    async def tearDown(self):
        pass

    async def test_variant_column(self):
        stage_window = ui_test.find("Stage")
        await stage_window.focus()
        await ui_test.human_delay()
        stage = omni.usd.get_context().get_stage()
        prim = stage.GetPrimAtPath("/Cup")

        # verify default state
        self.assertEqual(prim.GetVariantSets().GetVariantSet("shadingVariant").GetVariantSelection(), "Default")
        self.assertEqual(prim.GetVariantSets().GetVariantSet("modelingVariant").GetVariantSelection(), "CupA")

        # get widgets
        stage_tree = ui_test.find("Stage//Frame/**/ScrollingFrame/TreeView[*].visible==True")
        widgets = stage_tree.find_all("**/ComboBox[*]")
        self.assertNotEqual(widgets, [])
        shading_widget = None
        modeling_widget = None
        for widget in widgets:
            index = widget.model.get_item_value_model(None, 0).get_value_as_int()
            items = widget.model.get_item_children(None)

            if items[index].model.as_string == "Default":
                shading_widget = widget
            elif items[index].model.as_string == "CupA":
                modeling_widget = widget
            else:
                carb.log_error(f"unknown widget {widget}")
                return

        # can't use widget.click as open combobox has no readable size and clicks goto stage window
        shading_widget.model.set_value("Red")
        modeling_widget.model.set_value("CupC")
        await ui_test.human_delay()

        # verify new state
        self.assertEqual(prim.GetVariantSets().GetVariantSet("shadingVariant").GetVariantSelection(), "Red")
        self.assertEqual(prim.GetVariantSets().GetVariantSet("modelingVariant").GetVariantSelection(), "CupC")
