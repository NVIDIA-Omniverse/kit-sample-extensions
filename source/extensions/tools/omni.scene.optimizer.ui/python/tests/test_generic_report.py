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
from omni.scene.optimizer.ui.report_widgets import generic, stats

OPERATION_OPTIMIZE_MATERIALS = "optimizeMaterials"
OPTIMIZE_MATERIAL_ARGUMENTS = {"materialPrimPaths": [], "optimizeMaterialsMode": 0}

OPERATION_CONFIGURE = "executionContext"
CONFIGURE_ARGUMENTS = {"generateReport": True, "captureStats": True}

EXT_PATH = omni.kit.app.get_app().get_extension_manager().get_extension_path_by_module(__name__)
TEST_DATA_PATH = pathlib.Path(EXT_PATH).joinpath("data")


# Test classes derived from omni.kit.test.AsyncTestCase will be auto-discoverable by omni.kit.test
class Test_Generic_Panel(omni.kit.test.AsyncTestCase):
    """Test various aspects of the Merge Results UI"""

    async def setUp(self):
        """Setup for each test case"""

        # Create a SceneOptimizer panel
        self.panel = core.SceneOptimizerPanel()

        # Wait 2 update frames. Due to the lazy-load build_fn nature of
        # the UI we must do this in order to wait for the UI to build
        # properly.
        await ui_test.wait_n_updates(2)

    async def test_execution_with_report(self):
        """Test command execution generating a "generic widget" and stats report"""

        context = omni.usd.get_context()
        context.open_stage(str(TEST_DATA_PATH.joinpath("optimizeMaterials.usda")))

        # Assert the main Operations UI is empty to begin with
        widgets = len(self.panel.operation_widgets)
        self.assertEqual(widgets, 0)

        # Configure to Generate report
        self.panel.add_operation(OPERATION_CONFIGURE, args=CONFIGURE_ARGUMENTS)

        # Assert the operation was added
        widgets = len(self.panel.operation_widgets)
        self.assertEqual(widgets, 1)

        # Configure to Optimize Materials
        self.panel.add_operation(OPERATION_OPTIMIZE_MATERIALS, args=OPTIMIZE_MATERIAL_ARGUMENTS)

        # Assert the operation was added
        widgets = len(self.panel.operation_widgets)
        self.assertEqual(widgets, 2)

        # Execute the optimize materials command
        self.panel.operation_widgets[1].execute()

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
        self.assertEqual(len(optimize_report.entryGroups), 3)  # optimize materials

        await ui_test.wait_n_updates(2)

        report_tab = tabs[1]

        material_entries = None
        for group in optimize_report.entryGroups:
            if group.operation == "Optimize Materials":
                material_entries = group.entries
                break

        # Add some messages of varying levels to ensure they get created without
        # causing an exception.
        material_entries.append(report.Entry("DEBUG", "TESTCATEGORY", "Test Debug"))
        material_entries.append(report.Entry("WARNING", "TESTCATEGORY", "Test Warning"))
        material_entries.append(report.Entry("ERROR", "TESTCATEGORY", "Test Error"))

        self.assertTrue(len(material_entries) > 0)

        widget = generic.GenericWidget(material_entries)

        await ui_test.wait_n_updates(2)

        widget._delegate.build_header(0)
        widget._delegate.build_header(1)
        widget._delegate.build_header(2)

        children = widget._data_model.get_item_children(None)
        self.assertEqual(len(children), len(material_entries))

        for child in children:
            self.assertEqual([], widget._data_model.get_item_children(child))
            widget._delegate.build_widget(widget._data_model, child, 0, "INFO", False)

        self.assertEqual(widget._data_model.get_item_value_model_count(None), 3)
        widget._data_model.clear()

        # Select tab
        button = 0
        x = 0
        y = 0
        modifier = None
        self.panel.tab_group._tab_clicked(1, button, x, y, None)
        self.assertEqual(self.panel.tab_group.active_tab, 1)

        # Then delete
        await self.panel.tab_group.delete_tab(1)
        self.assertEqual(len(self.panel.tab_group.tabs), 1)

        stat_entries = None
        for group in optimize_report.entryGroups:
            if group.operation == "Stats":
                stat_entries = group.entries
                break
        self.assertTrue(len(stat_entries) > 0)

        widget = stats.StatsWidget(stat_entries)

        await ui_test.wait_n_updates(2)

        widget._delegate.build_header(0)
        widget._delegate.build_header(1)
        widget._delegate.build_header(2)
        widget._delegate.build_header(3)

        children = widget._data_model.get_item_children(None)

        for child in children:
            self.assertEqual([], widget._data_model.get_item_children(child))
            widget._delegate.build_widget(widget._data_model, child, 0, "INFO", False)

        self.assertEqual(widget._data_model.get_item_value_model_count(None), 4)
        widget._data_model.clear()

        # Clear and verify
        self.panel._do_clear()
        widgets = len(self.panel.operation_widgets)
        self.assertEqual(widgets, 0)

        # Also as we have a report, test a report tab can be created with it.
        tab = core.ReportTab("Test", report_path)
        tab.build_fn()

        await ui_test.wait_n_updates(2)

        self.assertEqual(tab.name, "Test")
