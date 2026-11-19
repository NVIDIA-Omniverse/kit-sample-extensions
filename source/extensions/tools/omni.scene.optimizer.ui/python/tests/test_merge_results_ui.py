# SPDX-FileCopyrightText: Copyright (c) 2022-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
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
from unittest.mock import patch

import omni.kit.test
import omni.kit.ui_test as ui_test
from omni.scene.optimizer.ui import core, report
from omni.scene.optimizer.ui.report_widgets import merge_results

OPERATION_MERGE = "merge"
GROUP_MERGE = "Merge Static Meshes"
MERGE_ARGUMENTS = {"meshPrimPaths": [], "mergePoint": 0, "considerMaterials": True}

OPERATION_CONFIGURE = "executionContext"
CONFIGURE_ARGUMENTS = {"generateReport": True, "captureStats": True}

EXT_PATH = omni.kit.app.get_app().get_extension_manager().get_extension_path_by_module(__name__)
TEST_DATA_PATH = pathlib.Path(EXT_PATH).joinpath("data")


# Test classes derived from omni.kit.test.AsyncTestCase will be auto-discoverable by omni.kit.test
class Test_Merge_Results_Panel(omni.kit.test.AsyncTestCase):
    """Test various aspects of the Merge Results UI"""

    async def setUp(self):
        """Setup for each test case"""

        # Create a SceneOptimizer panel
        self.panel = core.SceneOptimizerPanel()

        # Wait 2 update frames. Due to the lazy-load build_fn nature of
        # the UI we must do this in order to wait for the UI to build
        # properly.
        await ui_test.wait_n_updates(2)

    async def test_execution_with_merge_report(self):
        """Test basic command execution generating a report"""

        context = omni.usd.get_context()
        context.open_stage(str(TEST_DATA_PATH.joinpath("simpleFourCubesAndConeWithMaterials.usd")))

        # Assert the main Operations UI is empty to begin with
        widgets = len(self.panel.operation_widgets)
        self.assertEqual(widgets, 0)

        # Configure to Generate report
        self.panel.add_operation(OPERATION_CONFIGURE, args=CONFIGURE_ARGUMENTS)

        # Assert the operation was added
        widgets = len(self.panel.operation_widgets)
        self.assertEqual(widgets, 1)

        # Configure to Merge Meshes
        self.panel.add_operation(OPERATION_MERGE, args=MERGE_ARGUMENTS)

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

        merge_entries = None
        for group in optimize_report.entryGroups:
            if group.operation == GROUP_MERGE:
                merge_entries = group.entries
                break
        self.assertTrue(len(merge_entries) > 0)

        # Check entries for the three basic message categories we need:
        found_buckets = False
        found_hashdesc = False
        found_merge = False

        for entry in merge_entries:
            if entry.category == merge_results.CATEGORY_BUCKET:
                found_buckets = True
            if entry.category == merge_results.CATEGORY_BUCKET_HASHDESC:
                found_hashdesc = True
            if entry.category == merge_results.CATEGORY_MERGE:
                found_merge = True

        self.assertTrue(found_buckets)
        self.assertTrue(found_hashdesc)
        self.assertTrue(found_merge)

        await ui_test.wait_n_updates(2)

        self.panel.tab_group.select_tab(1)

        await ui_test.wait_n_updates(2)

        tab = tabs[1]
        tab.widgets[1]._on_show_merge_results_clicked()
        merge_ui = tab.widgets[1]._merge_results_panel

        # Launch the result UI and assert we parsed the logs correctly.
        # If these break because of logging changes to the Merge operation then we'll need to
        # update the regexes at the top of merge_results.py
        await ui_test.wait_n_updates(2)

        # Assert we had 5 input meshes
        self.assertTrue(len(merge_ui._mesh_hashes), 5)

        # Assert we had 3 buckets
        self.assertTrue(len(merge_ui._hash_descriptions), 3)

        # Assert we captured some properties
        self.assertTrue(len(merge_ui._all_properties) > 0)

        # Assert only 2 of the 3 buckets resulted in a merged mesh
        self.assertEqual(len(merge_ui._merged_hash_set), 2)
        self.assertEqual(len(merge_ui._output_to_input_map), 2)

        # Assert mapped the two output to their respective inputs.
        # NOTE: merge is done in reverse order.
        merged_inputs = merge_ui._output_to_input_map["/merged"]
        self.assertTrue("/World/Cube_02" in merged_inputs)
        self.assertTrue("/World/Cube_03" in merged_inputs)

        merged_inputs2 = merge_ui._output_to_input_map["/merged_1"]
        self.assertTrue("/World/Cube" in merged_inputs2)
        self.assertTrue("/World/Cube_01" in merged_inputs2)

        x = merge_ui._input_tree_view.screen_position_x + 70
        y = merge_ui._input_tree_view.screen_position_y + 100

        # Click one of the items in the input tree view to ensure it
        # can be selected without causing an exception.
        pos = ui_test.Vec2(x, y)
        await ui_test.emulate_mouse_move_and_click(pos, right_click=False, double=False)

        # Assert requesting children returns nothing (not a tree)
        items = merge_ui._attributes_data_model.get_item_children("foo")
        self.assertListEqual(items, [])

        merge_ui._attributes_data_model.clear()

        # Clear any items.
        merge_ui._input_data_model.clear()

        # Hide the window now we are done with it.
        merge_ui._window.visible = False

        await ui_test.wait_n_updates(2)

        # Select the merge report tab, should also not raise an exception.
        self.panel.tab_group.select_tab(1)
        await ui_test.wait_n_updates(2)

    async def test_merge_results_parse(self):
        """Test parsing invalid entry data"""

        merge_entries = list()

        # Invalid
        merge_entries.append(report.Entry("INFO", "BUCKET", "invalid"))
        merge_entries.append(report.Entry("INFO", "BUCKET.HASHDESC", "invalid"))

        # Valid top-level
        message = """Hash: 12345
Attr: invalid
Schema: TestSchema
Schema:invalid

invalid
Parent Path:invalid
Spatial Cluster: 2
Spatial Cluster: 5
Spatial Cluster:5
"""
        merge_entries.append(report.Entry("INFO", "BUCKET.HASHDESC", message))
        merge_ui = merge_results.MergeResultsPanel(merge_entries)

        self.assertIsNotNone(merge_ui)

        # Close window, to prevent it blocking other tests
        merge_ui._window.visible = False
        await ui_test.wait_n_updates(2)

    async def test_invalid_hash(self):
        """Test finding an invalid hash"""

        model = merge_results.TreeModel()
        self.assertListEqual(model.find_items_by_hash("foo"), [])

    async def test_attribute_models(self):
        """Invalid column values, filters"""

        model = merge_results.AttributeTableModel([], {}, [])
        self.assertFalse(model.column_values_differ(0))

        model.__source = None
        self.assertListEqual(model.get_item_children("invalid"), [])

        # Test attribute filter model destroy
        filter_model = merge_results.AttributeTableFilterModel(model)
        filter_model.destroy()
        self.assertListEqual(filter_model.get_item_children(None), [])

    async def test_execution_with_merge_report_differing_schema(self):
        """Test basic command execution generating a report"""

        context = omni.usd.get_context()
        context.open_stage(str(TEST_DATA_PATH.joinpath("meshSchemas.usda")))

        # Assert the main Operations UI is empty to begin with
        widgets = len(self.panel.operation_widgets)
        self.assertEqual(widgets, 0)

        # Configure to Generate report
        self.panel.add_operation(OPERATION_CONFIGURE, args=CONFIGURE_ARGUMENTS)

        # Assert the operation was added
        widgets = len(self.panel.operation_widgets)
        self.assertEqual(widgets, 1)

        # Configure to Merge Meshes
        self.panel.add_operation(OPERATION_MERGE, args=MERGE_ARGUMENTS)

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

        await ui_test.wait_n_updates(2)

        self.panel.tab_group.select_tab(1)

        await ui_test.wait_n_updates(2)

        # This code used to trigger a crash
        tab = tabs[1]
        tab.widgets[1]._on_show_merge_results_clicked()
        merge_ui = tab.widgets[1]._merge_results_panel

        merge_ui._attributes_data_model.clear()

        # Clear any items.
        merge_ui._input_data_model.clear()

        # Hide the window now we are done with it.
        merge_ui._window.visible = False

        await ui_test.wait_n_updates(2)

        # Select the merge report tab, should also not raise an exception.
        self.panel.tab_group.select_tab(1)
        await ui_test.wait_n_updates(2)
