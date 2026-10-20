# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
import omni.kit.test
import omni.ui as ui
import omni.usd
from omni.kit import ui_test
from omni.kit.test_suite.helpers import wait_stage_loading

from .utils import toggle_on_named_column


class TestVariantColumns(omni.kit.test.AsyncTestCase):
    async def setUp(self):
        from pathlib import Path

        # get file path
        extension_path = omni.kit.app.get_app().get_extension_manager().get_extension_path_by_module(__name__)
        await omni.usd.get_context().open_stage_async(str(Path(extension_path).joinpath("data/tests/Cup_3.usd")))
        await wait_stage_loading()
        # Show Variant column - stage options menu in a ui.TreeView inside a ui.Menu
        await toggle_on_named_column("Variant")

    async def tearDown(self):
        pass

    async def test_variant_column_height(self):
        stage_window = ui_test.find("Stage")
        await stage_window.focus()
        await ui_test.human_delay()

        stage = omni.usd.get_context().get_stage()

        # verify widgets height
        stage_tree = ui_test.find("Stage//Frame/**/ScrollingFrame/TreeView[*].visible==True")
        stage_tree.widget.set_expanded(None, True, True)
        await ui_test.human_delay()
        widgets = stage_tree.find_all("**/ZStack[*].identifier != ''")
        self.assertNotEqual(widgets, [])

        expected_values = {
            "variant_zstack__cup": ui.Length(22),
            "variant_zstack__cup_scope": ui.Length(22),
            "variant_zstack__scope": ui.Length(44),
        }

        for widget in widgets:
            self.assertAlmostEqual(widget.widget.height, expected_values[widget.widget.identifier])
