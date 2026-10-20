# SPDX-FileCopyrightText: Copyright (c) 2024-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.


import os
import pathlib

import omni.kit.clipboard as clipboard
import omni.kit.test
import omni.kit.ui_test as ui_test
from omni.scene.optimizer.ui import core, report
from omni.scene.optimizer.ui.report_widgets import coinciding

OPERATION_COINCIDING = "findCoincidingGeometry"
GROUP_COINCIDING = "Find Coincident Geometry"
COINCIDING_ARGUMENTS = {"primPaths": [], "tolerance": 0.001}

OPERATION_CONFIGURE = "executionContext"
CONFIGURE_ARGUMENTS = {"generateReport": True, "captureStats": True}

EXT_PATH = omni.kit.app.get_app().get_extension_manager().get_extension_path_by_module(__name__)
TEST_DATA_PATH = pathlib.Path(EXT_PATH).joinpath("data")


# Test classes derived from omni.kit.test.AsyncTestCase will be auto-discoverable by omni.kit.test
class Test_Coinciding_Results_Panel(omni.kit.test.AsyncTestCase):
    """Test various aspects of the Coinciding Results UI"""

    async def setUp(self):
        """Setup for each test case"""

        # Create a SceneOptimizer panel
        self.panel = core.SceneOptimizerPanel()

        # Wait 2 update frames. Due to the lazy-load build_fn nature of
        # the UI we must do this in order to wait for the UI to build
        # properly.
        await ui_test.wait_n_updates(2)

    async def test_execution_with_coinciding_report(self):
        """Test basic command execution generating a report"""

        context = omni.usd.get_context()
        context.open_stage(str(TEST_DATA_PATH.joinpath("coincidingMeshes.usda")))

        # Assert the main Operations UI is empty to begin with
        widgets = len(self.panel.operation_widgets)
        self.assertEqual(widgets, 0)

        # Configure to Generate report
        self.panel.add_operation(OPERATION_CONFIGURE, args=CONFIGURE_ARGUMENTS)

        # Assert the operation was added
        widgets = len(self.panel.operation_widgets)
        self.assertEqual(widgets, 1)

        # Add operation
        self.panel.add_operation(OPERATION_COINCIDING, args=COINCIDING_ARGUMENTS)

        # Assert the operation was added
        widgets = len(self.panel.operation_widgets)
        self.assertEqual(widgets, 2)

        # Run the commands. This should run printStats with reporting enabled and
        # trigger a new tab to be created.
        self.panel.execute()

        # Allow UI to refresh
        await ui_test.wait_n_updates(2)

        # After execute, should be 2 tabs
        tabs = self.panel.tab_group.tabs
        self.assertEqual(len(tabs), 2)

        # Assert the report exists and has at least some kind of basic
        # data written to it.
        report_path = tabs[1].reportPath
        self.assertTrue(os.path.isfile(report_path))
        self.assertTrue(os.path.getsize(report_path) > 0)

        optimize_report = report.Report(report_path)
        self.assertEqual(len(optimize_report.entryGroups), 3)  # stats, merge, stats

        coinciding_entries = None
        for group in optimize_report.entryGroups:
            if group.operation == GROUP_COINCIDING:
                coinciding_entries = group.entries
                break
        self.assertTrue(len(coinciding_entries) > 0)

        await ui_test.wait_n_updates(2)

        self.panel.tab_group.select_tab(1)

        await ui_test.wait_n_updates(2)

        tab = tabs[1]
        coinciding_ui = tab.widgets[1]

        # Confirm that the CoincidingWidget info entries list was created.
        # There should be 8 INFO entries generated.
        self.assertTrue(coinciding_ui._info_entries is not None)
        self.assertEqual(len(coinciding_ui._info_entries), 8)

        # Make sure the model was created.
        self.assertTrue(coinciding_ui._info_model is not None)
        info_model_children = coinciding_ui._info_model.get_item_children(None)
        self.assertEqual(len(info_model_children), 8)
        self.assertTrue(info_model_children[2]._model is not None)

        # Check that /World/Cone occurs once in the list of entries.
        path_count = sum(c._model.get_value_as_string() == "/World/Cone" for c in info_model_children)
        self.assertEqual(path_count, 1)

        # Select something
        coinciding_ui._tree_view.selection = [info_model_children[2]]
        await ui_test.wait_n_updates(2)

        # Force hover, so menu works
        coinciding_ui._item_hovered(info_model_children[2], True)
        await ui_test.wait_n_updates(2)

        # Click to show a menu
        pos = ui_test.Vec2(
            coinciding_ui._tree_view.screen_position_x + 10, coinciding_ui._tree_view.screen_position_y + 60
        )

        await ui_test.emulate_mouse_move_and_click(pos, right_click=True, double=False)

        # Click the first item in the menu (select prims)
        menu_pos = ui_test.Vec2(pos.x + 10, pos.y + 10)

        await ui_test.emulate_mouse_move(menu_pos, 1)
        await ui_test.wait_n_updates(2)
        await ui_test.emulate_mouse_click(False, False)
        await ui_test.wait_n_updates(2)

        # Assert one item selected
        self.assertEqual(len(coinciding_ui._selected_paths), 1)

        # Show menu again
        await ui_test.emulate_mouse_move_and_click(pos, right_click=True, double=False)

        # Similar to above, select second item (copy paths)
        menu_pos = ui_test.Vec2(pos.x + 10, pos.y + 40)
        await ui_test.emulate_mouse_move(menu_pos, 1)
        await ui_test.wait_n_updates(2)
        await ui_test.emulate_mouse_click(False, False)
        await ui_test.wait_n_updates(2)

        selected = str(coinciding_ui._selected_paths)

        # Assert selection matches the clipboard
        self.assertEqual(clipboard.paste(), selected)
