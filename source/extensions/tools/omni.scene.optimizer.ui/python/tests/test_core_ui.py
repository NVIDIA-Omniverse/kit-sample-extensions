# SPDX-FileCopyrightText: Copyright (c) 2022-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.


import base64
import json
import os
import tempfile
import time
from unittest.mock import MagicMock, patch

import carb.settings
import omni.kit.test
import omni.kit.ui_test as ui_test
import omni.stats
import omni.ui as ui
from omni.kit.ui_test.input import emulate_mouse_slow_move
from omni.scene.optimizer.ui import argument_widgets, core, preset_info, tabs
from pxr import Sdf, UsdGeom

VALID_OPERATION_NAME = "merge"

INVALID_OPERATION_NAME = "foo"

VALID_OPERATION_ARGUMENTS = {"meshPrimPaths": ["/foo", "/bar"], "mergePoint": 0}

INVALID_OPERATION_ARGUMENTS = {
    "meshPrimPaths": 0,  # Invalid type for PrimPaths type
    "mergePoint": "Component",  # Invalid type for Enum type
    "foo": "bar",  # Invalid argument name
}

OPERATION_CONFIGURE = "executionContext"
OPERATION_DECIMATE = "decimateMeshes"
OPERATION_OPTIMIZE_PRIMVARS = "optimizePrimvars"
OPERATION_REMOVE_ATTRIBUTES = "removeAttributes"

ARGS_GENERATE_REPORT = {"generateReport": True, "captureStats": True}


# Test classes derived from omni.kit.test.AsyncTestCase will be auto-discoverable by omni.kit.test
class Test_Scene_Optimizer_Panel(omni.kit.test.AsyncTestCase):
    """Test various aspects of the UI"""

    async def setUp(self):
        """Setup for each test case"""

        # Create a SceneOptimizer panel
        self.panel = core.SceneOptimizerPanel()

        # Wait 2 update frames. Due to the lazy-load build_fn nature of
        # the UI we must do this in order to wait for the UI to build
        # properly.
        await ui_test.wait_n_updates(2)

    async def test_add_operation(self):
        """Check the behaviour of SceneOptimizerPanel.add_operation"""

        # Assert that there are no operations in the panel when freshly constructed.
        returned = len(self.panel.operation_widgets)
        expected = 0
        self.assertEqual(returned, expected)

        # Assert that adding an operation with a valid name increases the number of operations by one.
        self.panel.add_operation(VALID_OPERATION_NAME)
        returned = len(self.panel.operation_widgets)
        expected = expected + 1
        self.assertEqual(returned, expected)

        # Assert that adding the same operation a second time increases the number of operations.
        self.panel.add_operation(VALID_OPERATION_NAME)
        returned = len(self.panel.operation_widgets)
        expected = expected + 1
        self.assertEqual(returned, expected)

        # Assert that adding an operation with an invalid name does not increases the number of operations.
        self.panel.add_operation(INVALID_OPERATION_NAME)
        returned = len(self.panel.operation_widgets)
        expected = expected + 0
        self.assertEqual(returned, expected)

        # Assert that adding an operation with the "collapsed" argument results in the expected collapsed state.

        # The default value if "collapsed" is not specified should be "False".
        self.panel.add_operation(VALID_OPERATION_NAME)
        operation_widget = self.panel.operation_widgets[-1]
        returned = operation_widget.collapsed
        expected = False
        self.assertEqual(returned, expected)

        # If "collapsed" is specified as "False" then the operation widget should reflect that.
        self.panel.add_operation(VALID_OPERATION_NAME, collapsed=False)
        operation_widget = self.panel.operation_widgets[-1]
        returned = operation_widget.collapsed
        expected = False
        self.assertEqual(returned, expected)

        # If "collapsed" is specified as "True" then the operation widget should reflect that.
        self.panel.add_operation(VALID_OPERATION_NAME, collapsed=True)
        operation_widget = self.panel.operation_widgets[-1]
        returned = operation_widget.collapsed
        expected = True
        self.assertEqual(returned, expected)

        # Assert that adding an operation with the "argument_values" argument results in the expected argument values.

        # If the arguments match those of the operation in terms of name and type then the value is set.
        self.panel.add_operation(VALID_OPERATION_NAME, args=VALID_OPERATION_ARGUMENTS)
        operation_widget = self.panel.operation_widgets[-1]
        operation_args = operation_widget.get_args()
        # Assert that for all arguments passed the value matches what was passed
        for key, expected in VALID_OPERATION_ARGUMENTS.items():
            returned = operation_args.get(key)
            self.assertEqual(returned, expected)

        # If the arguments do not match those of the operation in terms of name or type then the value is not set.
        self.panel.add_operation(VALID_OPERATION_NAME, args=INVALID_OPERATION_ARGUMENTS)
        operation_widget = self.panel.operation_widgets[-1]
        operation_args = operation_widget.get_args()
        # Assert that for all arguments passed the value matches what was passed
        for key, expected in INVALID_OPERATION_ARGUMENTS.items():
            returned = operation_args.get(key)
            self.assertNotEqual(returned, expected)

        self.assertIsNone(operation_widget._get_arg_info("invalid arg"))

        # TODO: Add tests for all Argument types to ensure correct value type handling is in place.

    async def test_code_arg(self):
        """Test getting/setting python code"""
        value = "test string"

        _bytes = value.encode("ascii")
        base64_bytes = base64.b64encode(_bytes)
        base64_value = base64_bytes.decode("ascii")

        args = {"displayName": "test", "displayType": "code"}
        widget = argument_widgets.construct_argument_widget(args, "My Widget")

        widget.set_value(base64_value)
        self.assertEqual(base64_value, widget.get_value())

    async def test_paths_widget(self):
        """Test dropping an SdfPath on a path widget"""

        args = {"displayName": "test", "metadata": {}}
        widget = argument_widgets.PrimPathsArgumentWidget(args)

        # Mock class
        class Event:
            def __init__(self, mime_data):
                self.mime_data = mime_data

        self.assertTrue(omni.usd.get_context().new_stage())

        value = widget.get_value()
        self.assertListEqual(value, [])

        self.assertFalse(widget.drop_accept("error!"))
        self.assertTrue(widget.drop_accept("/World/Foo"))

        widget.drop(Event("/World/Foo"))

        # Drop "invalid" path
        widget.drop(Event("()"))

        value = widget.get_value()
        self.assertListEqual(value, ["/World/Foo"])

        # Assert the edit paths panel opens
        widget.edit_paths()
        self.assertIsNotNone(widget._edit_panel)

        # Assert toggling its visibility clears it
        # widget._edit_panel.window.visible = False
        widget.tidy_up()
        self.assertIsNone(widget._edit_panel)

        # Clear
        widget.set_value([])
        self.assertListEqual(widget.get_value(), [])

        # Test adding from USD selection
        stage = omni.usd.get_context().get_stage()
        stage.DefinePrim("/World", "Xform")
        stage.DefinePrim("/World/Mesh1", "Mesh")
        stage.DefinePrim("/World/Mesh2", "Mesh")

        # Select the path in the stage
        selection = omni.usd.get_context().get_selection()
        selection.set_selected_prim_paths(["/World/Mesh1"], True)

        # Press the add paths button
        widget.add_paths(0, 0, 0, False)

        # Assert the selection from the stage was added to the widget
        self.assertListEqual(widget.get_value(), ["/World/Mesh1"])

        # Add Mesh2 to the stage selection
        selection.set_selected_prim_paths(["/World/Mesh1", "/World/Mesh2"], True)

        # Drop one of the paths that is selected
        widget.drop(Event("/World/Mesh1"))

        # Assert dropping one of the selected paths drops both of them
        self.assertListEqual(widget.get_value(), ["/World/Mesh1", "/World/Mesh2"])

        # Reset
        widget.set_value([])
        self.assertListEqual(widget.get_value(), [])

        # Select "nothing""
        selection.set_selected_prim_paths([], True)
        widget.add_paths(0, 0, 0, 0)

        # No change
        self.assertListEqual(widget.get_value(), [])

        # Assert updating paths
        widget.update_paths(["/World/Mesh1"])
        self.assertListEqual(widget.get_value(), ["/World/Mesh1"])

    async def test_float_widget(self):
        """Test float min/max"""

        args = {"displayName": "test", "metadata": {"min": 1.0, "max": 2.0}}
        widget = argument_widgets.FloatArgumentWidget(args)

        # Assert a value can be set as expected
        widget.set_value(1.5)
        self.assertEqual(widget.get_value(), 1.5)

        # Assert min
        widget.set_value(-1.0)
        self.assertEqual(widget.get_value(), 1.0)

        # Assert max
        widget.set_value(5.0)
        self.assertEqual(widget.get_value(), 2.0)

        # Re-test, but with only a miniumum set
        # The underlying omni.ui widget only works if there is a max that
        # is higher than the min, so this tests our handling of that works.
        args = {"displayName": "test", "metadata": {"min": 1.0}}
        widget = argument_widgets.FloatArgumentWidget(args)

        # Assert a value can be set as expected
        widget.set_value(1.5)
        self.assertEqual(widget.get_value(), 1.5)

        # Assert min is respected
        widget.set_value(-1.0)
        self.assertEqual(widget.get_value(), 1.0)

        # No max
        widget.set_value(500.0)
        self.assertEqual(widget.get_value(), 500.0)

    async def test_int_widget(self):
        """Test int min/max"""

        args = {"displayName": "test", "metadata": {"min": 1.0, "max": 5.0}}
        widget = argument_widgets.IntArgumentWidget(args)

        # Assert a value can be set as expected
        widget.set_value(2)
        self.assertEqual(widget.get_value(), 2)

        # Assert min
        widget.set_value(-5)
        self.assertEqual(widget.get_value(), 1)

        # Assert max
        widget.set_value(10)
        self.assertEqual(widget.get_value(), 5)

        # Re-test, but with only a miniumum set
        # The underlying omni.ui widget only works if there is a max that
        # is higher than the min, so this tests our handling of that works.
        args = {"displayName": "test", "metadata": {"min": 1.0}}
        widget = argument_widgets.IntArgumentWidget(args)

        # Assert a value can be set as expected
        widget.set_value(2)
        self.assertEqual(widget.get_value(), 2)

        # Assert min is respected
        widget.set_value(-10)
        self.assertEqual(widget.get_value(), 1)

        # No max
        widget.set_value(500)
        self.assertEqual(widget.get_value(), 500)

    async def test_float_slider_widget(self):
        """Test float slider min/max"""

        args = {"displayName": "test", "metadata": {"min": 1.0, "max": 2.0}}
        widget = argument_widgets.FloatSliderArgumentWidget(args)

        # Assert a value can be set as expected
        widget.set_value(1.5)
        self.assertEqual(widget.get_value(), 1.5)

        # Assert the min works
        self.assertEqual(widget._widget.min, 1.0)

        # Assert the max works
        self.assertEqual(widget._widget.max, 2.0)

    async def test_int_slider_widget(self):
        """Test int slider min/max"""
        args = {"displayName": "test", "metadata": {"min": 1, "max": 5}}
        widget = argument_widgets.IntSliderArgumentWidget(args)

        # Assert a value can be set as expected
        widget.set_value(2)
        self.assertEqual(widget.get_value(), 2)

        # Assert the min works
        self.assertEqual(widget._widget.min, 1)

        # Assert the max works
        self.assertEqual(widget._widget.max, 5)

    async def test_float_presets_widget(self):
        """Test float presets widget"""

        args = {"displayName": "test", "metadata": {}, "floatPresets": [["foo", 1.0], ["bar", 2.0]]}
        widget = argument_widgets.FloatPresetsArgumentWidget(args)

        widget.set_value(1.999)
        widget.set_value(2.0)
        self.assertEqual(widget.get_value(), 2.0)
        self.assertEqual(widget._get_index(1.0), 0)
        self.assertEqual(widget._get_index(2.0), 1)
        self.assertFalse(widget._is_valid_index(None))

    async def test_attribute_list_widget(self):
        """Test the AttributeList widget"""

        self.panel.add_operation(OPERATION_REMOVE_ATTRIBUTES)

        widget = self.panel.operation_widgets[0]
        attr_widget = widget._widgets_by_name["attributes"]

        await ui_test.wait_n_updates(2)

        # Set some attributes
        attributes = ["primvars:", "foo", "123###"]
        attr_widget.set_value(attributes)

        # Allow UI to refresh
        await ui_test.wait_n_updates(2)

        # Assert the value was set and returned as expected.
        self.assertEqual(attr_widget.get_value(), attributes)

        # "Clear" one of the attributes
        attr_widget._clear_clicked(1)
        await ui_test.wait_n_updates(2)

        # Assert the value was set and returned as expected.
        del attributes[1]
        await ui_test.wait_n_updates(2)
        self.assertEqual(attr_widget.get_value(), attributes)

        # Append a new attribute
        await attr_widget.focus_text_field()
        attr_widget._text_field_new.model.set_value("newAttr")
        await ui_test.wait_n_updates(2)

        # Take focus off the text field now, which will trigger the end-edit
        # callback and update everything.
        attr_widget._text_field_new.widget.focus_keyboard(focus=False)
        await ui_test.wait_n_updates(2)

        # Assert the value was added
        attributes.append("newAttr")
        self.assertEqual(attributes, attr_widget.get_value())

        async def edit_existing(attr_index, new_value):
            """
            Extra waits are needed to ensure the various UI callbacks
            trigger and complete before we interact with the widget.
            """
            await omni.kit.app.get_app().next_update_async()
            attr_widget._attribute_fields[attr_index].widget.focus_keyboard(focus=True)
            await ui_test.wait_n_updates(4)
            attr_widget._attribute_fields[attr_index].widget.model.set_value(new_value)
            attr_widget._attribute_fields[attr_index].widget.focus_keyboard(focus=False)
            await ui_test.wait_n_updates(4)

        # Edit an existing value by renaming it
        await edit_existing(0, "ui:")

        attributes[0] = "ui:"
        self.assertEqual(attributes, attr_widget.get_value())

        # Edit an existing one by clearing the name, to delete it
        await edit_existing(0, "")

        del attributes[0]
        self.assertEqual(attributes, attr_widget.get_value())

    async def test_argument_default_value(self):
        """Test setting to default"""

        args = {
            "displayName": "test",
            "displayType": "text",
            "defaultValue": "test value",
            "hidden": True,
            "metadata": {},
        }
        widget = argument_widgets.construct_argument_widget(args)
        widget.restore_default_value()

        # Assert default
        self.assertEqual(widget.get_value(), "test value")

        # Assert setting a new value
        widget.set_value("changed value")
        self.assertEqual(widget.get_value(), "changed value")

        # Revert
        widget._control_state_mouse_pressed_fn(0, 0, 0, 0)
        self.assertEqual(widget.get_value(), "test value")

        # Clear and then test
        widget._info["defaultValue"] = None
        widget._control_state_mouse_pressed_fn(0, 0, 0, 0)
        self.assertEqual(widget.get_value(), "test value")

    async def test_execution_with_report(self):
        """Test basic command execution generating a report"""

        # As we want to run operations we need a valid stage
        stage = omni.usd.get_context().new_stage()

        # Assert the main Operations UI is empty to begin with
        widgets = len(self.panel.operation_widgets)
        self.assertEqual(widgets, 0)

        # Simplest thing to generate a report
        self.panel.add_operation(OPERATION_CONFIGURE, args=ARGS_GENERATE_REPORT)

        # Assert the operation was added
        widgets = len(self.panel.operation_widgets)
        self.assertEqual(widgets, 1)

        # Assert only the one default tab (Operations)
        tabCount = len(self.panel.tab_group.tabs)
        self.assertEqual(tabCount, 1)

        # Run the commands. This should run printStats with reporting enabled and
        # trigger a new tab to be created.
        self.panel.execute()

        # Allow UI to refresh
        await ui_test.wait_n_updates(2)

        # After execute, should be 2 tabs
        tabs = self.panel.tab_group.tabs
        self.assertEqual(len(tabs), 2)

        # Assert the *type* of tab - operations, and the new Report
        self.assertTrue(isinstance(tabs[0], core.OperationsTab))
        self.assertTrue(isinstance(tabs[1], core.ReportTab))

        # Assert the report exists and has at least some kind of basic
        # data written to it.
        reportPath = tabs[1].reportPath
        self.assertTrue(os.path.isfile(reportPath))
        self.assertTrue(os.path.getsize(reportPath) > 0)

        # Try removing the first tab
        self.assertEqual(len(self.panel.tab_group.tabs), 2)
        await self.panel.tab_group.delete_tab(0, 0)
        await ui_test.wait_n_updates(2)
        self.assertEqual(len(self.panel.tab_group.tabs), 2)

        # Now try "middle clicking" the last tab to close
        self.panel.tab_group.active_tab = 1
        self.panel.tab_group._tab_clicked(1, 0, 0, 2, None)
        await ui_test.wait_n_updates(2)
        self.assertEqual(len(self.panel.tab_group.tabs), 1)

        await ui_test.wait_n_updates(2)

        # Run the commands. This should run printStats with reporting enabled and
        # trigger a new tab to be created.
        self.panel.execute()
        # Run the commands. This should run printStats with reporting enabled and
        # trigger a new tab to be created.
        self.panel.execute()

        await ui_test.wait_n_updates(2)

        self.panel.tab_group.select_tab(2)
        await ui_test.wait_n_updates(2)

        # "Middle-click" the tab before the one that was selected.
        self.panel.tab_group._tab_clicked(1, 0, 0, 2, None)
        await ui_test.wait_n_updates(2)
        self.assertEqual(len(self.panel.tab_group.tabs), 2)

        # Test hovering over an invalid tab doesn't raise
        self.panel.tab_group._tab_hovered(100, True)

        # Test hovering over a valid tab doesn't raise
        self.panel.tab_group._tab_hovered(1, True)

        self.panel.tab_group._tab_hovered(0, True)

        # Test hovering tab
        self.panel.tab_group.active_tab = 0
        self.panel.tab_group._tab_hovered(1, True)

        # Delete remaining tab
        self.panel.tab_group._delete_button_clicked(1, 0, 0, 0, None)
        await ui_test.wait_n_updates(2)

        # One remaining tab.
        self.assertEqual(len(self.panel.tab_group.tabs), 1)

        # Create a few tabs
        self.panel.execute()
        self.panel.execute()
        self.panel.execute()
        await ui_test.wait_n_updates(2)
        self.assertEqual(len(self.panel.tab_group.tabs), 4)

        await self.panel.tab_group.delete_tab(2)
        await self.panel.tab_group.delete_tab(2)
        await self.panel.tab_group.delete_tab(1)

        self.assertEqual(len(self.panel.tab_group.tabs), 1)

        self.panel.tab_group.destroy()

    async def test_invalid_argument_widget(self):
        """Test constructing an invalid widget type"""

        args = {"type": "invalid type"}
        widget = argument_widgets.construct_argument_widget(args)
        self.assertIsNone(widget)

    async def test_presets(self):
        """Test presets"""

        # Check there are 6 presets
        presets = preset_info.get_preset_info_for_execution_context()
        self.assertEqual(len(presets), 6)

        # Get the first and test that adding it adds the correct number of widgets
        preset = presets[0]

        self.assertEqual(len(self.panel.operation_widgets), 0)
        self.panel.add_preset(preset["name"])

        await ui_test.wait_n_updates(2)

        self.assertEqual(len(self.panel.operation_widgets), len(preset["arguments"]))

        # Test "Load Preset" menu
        button = 0
        self.panel.load_preset(0, 0, button, None)

        # Wait for UI update
        await ui_test.wait_n_updates(2)

        # Get the current menu and assert it has the expected number of children
        menu = ui.Menu.get_current()
        self.assertIsNotNone(menu)

        expected_len = len(presets)

        # Assert menu has the same number
        menu_items = ui.Inspector.get_children(menu)

        # Count the number of items between separators.
        # We have "Load Presets", then a separator, then the presets.
        # Following that may or may not be another separator and any
        # saved recently used items.
        actual_len = 0
        seen_separator = False
        for item in menu_items:
            if isinstance(item, ui.Separator):
                if seen_separator:
                    break
                else:
                    seen_separator = True
                    continue

            if seen_separator:
                actual_len += 1

        self.assertEqual(actual_len, expected_len)

    async def test_invalid_presets(self):
        """Test adding invalid preset"""

        with patch(
            "omni.scene.optimizer.ui.core.SceneOptimizerPanel.get_preset_with_name",
            MagicMock(return_value="""{"name": "foo"}"""),
        ) as mock_bar:
            self.panel.add_preset("foo")
            self.assertEqual(len(self.panel.operation_widgets), 0)
            self.panel.add_preset("bar")
            self.assertEqual(len(self.panel.operation_widgets), 0)

        self.assertIsNone(self.panel.get_preset_with_name("foo"))
        self.panel.add_preset("foo")
        self.assertEqual(len(self.panel.operation_widgets), 0)

    async def test_popup_dialog(self):
        """Test opening/closing a popup works"""

        self.panel.open_popup_dialog("Test", "Test", None, None)
        self.assertIsNotNone(self.panel._popup_dialog)
        self.panel.close_popup_dialog()
        self.assertFalse(self.panel._popup_dialog.visible)

    async def test_warning_dialog(self):
        """Test the security warning dialog"""
        self.panel.open_security_warning_dialog("Test", "Test", None, None)
        self.assertIsNotNone(self.panel._security_warning_dialog)
        self.panel.close_security_warning_dialog()
        self.assertFalse(self.panel._security_warning_dialog.visible)

    async def test_drag(self):
        """Test dragging a widget"""

        # Create a couple of operations
        self.panel.add_operation(OPERATION_CONFIGURE, args=ARGS_GENERATE_REPORT)
        self.panel.add_operation(VALID_OPERATION_NAME)
        self.assertEqual(len(self.panel.operation_widgets), 2)

        # Get their names
        first_name = self.panel.operation_widgets[0].name()
        second_name = self.panel.operation_widgets[1].name()

        # Allow UI to build
        await ui_test.wait_n_updates(2)

        # Test via emulated mouse drag/drop.
        # Get the current positions of the widgets
        pos_first = self.panel.operation_widgets[0].pos()
        pos_second = self.panel.operation_widgets[1].pos()

        # Create start/end Vec2s for the ui_test emulation function
        # Start is just inside the second widget, where the drag handle is
        pos_start = ui_test.Vec2(pos_second[0] + 10, pos_second[1] + 10)

        # End is just above above the first widget (-5) and just in (+10), where the
        # drag position markers are
        pos_end = ui_test.Vec2(pos_first[0] + 10, pos_first[1] - 5)

        # Emulate the drag and then wait for the UI
        await ui_test.input.emulate_mouse_drag_and_drop(pos_start, pos_end)
        await ui_test.wait_n_updates(2)

        # Assert the drag/drop worked and the widgets have been reordered
        self.assertEqual(self.panel.operation_widgets[0].name(), second_name)
        self.assertEqual(self.panel.operation_widgets[1].name(), first_name)

        pos_first = self.panel.operation_widgets[1].pos()
        pos_second = self.panel.operation_widgets[1].pos()

        # This is similar to above, but not actually rearranging - pos first/second are
        # the same thing, so testing it doesn't change order.
        pos_start = ui_test.Vec2(pos_second[0] + 10, pos_second[1] + 10)
        pos_end = ui_test.Vec2(pos_first[0] + 10, pos_first[1] - 5)

        # Emulate the drag and then wait for the UI
        await ui_test.input.emulate_mouse_drag_and_drop(pos_start, pos_end)
        await ui_test.wait_n_updates(2)

        # Assert the drag/drop worked and the widgets have been reordered
        self.assertEqual(self.panel.operation_widgets[0].name(), second_name)
        self.assertEqual(self.panel.operation_widgets[1].name(), first_name)

        # Assert nothing happens if dragging isn't active
        self.panel.mouse_moved(0, 0, None, None)

    async def test_operations_menu(self):
        """Test the "Add Scene Optimizer Operation" menu"""

        # x/y don't matter. Button must be 0
        x = 0
        y = 0
        button = 0

        # Trigger "add operation" menu"
        self.panel.menu(x, y, button, None)

        # Wait for UI update
        await ui_test.wait_n_updates(2)

        # Get the current menu and assert it has the expected number of children
        menu = ui.Menu.get_current()
        self.assertIsNotNone(menu)

    async def test_invalid_tabs(self):
        """Test invalid tab code"""

        # Assert creating a BaseTab directly
        with self.assertRaises(NotImplementedError):
            tab = tabs.BaseTab("test name")
            tab.build_fn()

        # Assert creating a tab group with no tabs
        with self.assertRaises(ValueError):
            tab_group = tabs.TabGroup([])

    async def test_security_warning(self):
        """Test security warning for python code"""

        # Create temporary file on disk
        f = tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w+")

        # Create a fake pythonScript operation, which should trigger the security warning
        args = [{"operation": "pythonScript", "python": "invalid python"}]
        json.dump(args, f)

        # Close the file, windows can't read it if it is still open.
        f.close()

        # Security warning is not around
        self.assertIsNone(self.panel._security_warning_dialog)

        self.panel.filepath = f.name
        self.panel.proceed_load_definition()

        # Security warning should have activated
        self.assertIsNotNone(self.panel._security_warning_dialog)
        self.assertTrue(self.panel._security_warning_dialog.visible)

        # Dismiss it
        self.panel.close_security_warning_dialog()
        self.assertFalse(self.panel._security_warning_dialog.visible)

        # Try and clean up the file
        try:
            os.unlink(f.name)
        except:  # pragma: no cover
            pass

    async def test_panel_visibility(self):
        """Test toggling the panel via the SceneOptimizerUI class"""

        # Build a panel. Toggle visibility.
        ui = core.SceneOptimizerUI()

        # Assert menu would be not checked
        self.assertFalse(ui._ticked_fn())

        ui._toggle_panel()
        await ui_test.wait_n_updates(2)

        # Assert menu would be checked
        self.assertTrue(ui._ticked_fn())

        self.assertTrue(ui._panel.window.visible)

        ui._toggle_panel()
        await ui_test.wait_n_updates(2)

        self.assertFalse(ui._panel.window.visible)

        ui._panel.add_operation(VALID_OPERATION_NAME, args=VALID_OPERATION_ARGUMENTS)
        await ui_test.wait_n_updates(2)

        ui._toggle_panel()
        await ui_test.wait_n_updates(2)

        ui._toggle_panel()
        await ui_test.wait_n_updates(2)

        ui.shutdown()

        # Assert at the end: this ensures no exceptions were raised
        # during construction of the panel, visibility updates etc.
        self.assertTrue(True)

    async def test_definition(self):
        def on_click(dialog, filename, dirname):  # pragma: no cover
            pass

        self.panel.filepath = tempfile.gettempdir()
        file_dialog = self.panel.file_dialog(on_click, "Test Dialog")
        await ui_test.wait_n_updates(2)

        # Hide, then destroy, to ensure it is not triggering a runloop
        file_dialog.hide()
        file_dialog.destroy()
        file_dialog = None
        await ui_test.wait_n_updates(2)

    async def test_save_load_definition(self):
        """Test UI save/load of JSON definition"""
        # Add operation and assert
        self.assertEqual(len(self.panel.operation_widgets), 0)
        self.panel.add_operation(VALID_OPERATION_NAME, args=VALID_OPERATION_ARGUMENTS)
        self.assertEqual(len(self.panel.operation_widgets), 1)

        # Show save dialog
        dialog = self.panel.file_dialog(self.panel.save_definition, "Save")

        await ui_test.wait_n_updates(2)

        # Navigate to where we will save the file
        dialog.navigate_to(tempfile.gettempdir())

        await ui_test.wait_n_updates(2)

        # Create named temp file
        f = tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w+")

        # Close, so windows doesn't get upset
        f.close()

        # Strip .json before passing in. The panel will add it back.
        stripped = f.name.replace(".json", "")

        # Set
        dialog.set_filename(stripped)
        await ui_test.wait_n_updates(2)

        # Accept the dialog
        dialog._click_apply_handler(os.path.basename(f.name), os.path.dirname(f.name))

        await ui_test.wait_n_updates(2)

        # Click the "Overwrite" button, as it was created when we made the NamedTemporaryFile
        pos = ui_test.Vec2(
            self.panel._popup_dialog_ok.screen_position_x + 5, self.panel._popup_dialog_ok.screen_position_y + 5
        )
        await ui_test.emulate_mouse_move_and_click(pos, right_click=False, double=False)

        # Destroy dialog
        dialog.hide()
        dialog.destroy()
        dialog = None
        await ui_test.wait_n_updates(2)

        # Clear the operations
        dialog = self.panel.clear()
        await ui_test.wait_n_updates(2)

        dialog._on_okay()
        await ui_test.wait_n_updates(2)

        # Should be empty now
        self.assertEqual(len(self.panel.operation_widgets), 0)

        # Empty, so should return no dialog
        self.assertIsNone(self.panel.clear())

        class MockDialog:
            def hide(self):
                pass

        # Load the definition we just saved based on the file
        self.panel.load_definition(MockDialog(), os.path.basename(f.name), os.path.dirname(f.name))

        await ui_test.wait_n_updates(2)

        # Should have one operation again
        self.assertEqual(len(self.panel.operation_widgets), 1)

        # Load again, to check "overwrite""
        self.panel.load_definition(None, os.path.basename(f.name), os.path.dirname(f.name))

        await ui_test.wait_n_updates(2)

        # Click the "Overwrite" button, as it was created when we made the NamedTemporaryFile
        pos = ui_test.Vec2(
            self.panel._popup_dialog_ok.screen_position_x + 5, self.panel._popup_dialog_ok.screen_position_y + 5
        )
        await ui_test.emulate_mouse_move_and_click(pos, right_click=False, double=False)

        # Should still only be one, as we replaced
        self.assertEqual(len(self.panel.operation_widgets), 1)

        # Save again, unique file, with no json extension
        self.panel.save_definition(None, "testfile", tempfile.gettempdir())

        # Remove temp files
        try:
            os.unlink(self.panel.filepath)
            os.unlink(f.name)
        except:  # pragma: no cover
            pass

        # Test omni url

        # Patch write_file to return OK result
        with patch(
            "omni.client.write_file",
            MagicMock(return_value=(omni.client.Result.OK)),
        ) as mock_client:
            # Fake URL with an omniverse prefix, which will trigger the mocked write
            self.panel.save_definition(None, "testfile", "omniverse://test.url")

        # Patch write_file to return error result
        with patch(
            "omni.client.write_file",
            MagicMock(return_value=(omni.client.Result.ERROR)),
        ) as mock_client:
            # Fake URL with an omniverse prefix, which will trigger the mocked write
            self.panel.save_definition(None, "testfile", "omniverse://test.url")

    async def test_delete_widget(self):
        """Test deleting a widget"""

        self.assertEqual(len(self.panel.operation_widgets), 0)

        self.panel.add_operation(VALID_OPERATION_NAME, args=VALID_OPERATION_ARGUMENTS)

        self.assertEqual(len(self.panel.operation_widgets), 1)

        widget = self.panel.operation_widgets[0]
        self.panel.delete(widget, 0, 0, 0, 0)

        self.assertEqual(len(self.panel.operation_widgets), 0)

    async def test_empty_report_path(self):
        """Test adding an empty report path"""

        # No reports
        self.assertEqual(len(self.panel._reports), 0)

        self.panel.add_report_path(None)

        # Still no reports
        self.assertEqual(len(self.panel._reports), 0)

    async def test_no_stats(self):
        """Test executing with no stats does not fail"""

        args = {"captureStats": False}
        self.panel.add_operation("executionContext", args=args)
        self.assertEqual(len(self.panel.operation_widgets), 1)
        self.panel.execute()
        await ui_test.wait_n_updates(2)

        # Didn't crash!
        self.assertTrue(True)

    async def test_delete_widget_del(self):
        """Test del on a widget"""

        info = self.panel.get_operator_info("executionContext")
        w = core.OperationWidget(info, None, False, args={})
        self.assertTrue(w.height() > 0)

        # Make sure calling del to delete sub-widgets does not trigger
        # a problem
        w.__del__()

        # No issues
        self.assertTrue(True)

    async def test_panel_drop_exceptions(self):
        """Test panel base drop functionality"""

        # This function should do nothing
        self.assertFalse(self.panel.drop_accept(None))

        # No drag start
        self.assertIsNone(self.panel.drag_begin(None, None))

        # Nothing, return false
        self.panel.drop_index = 0
        self.assertFalse(self.panel.drag_ended(0, 0, 0, 0))

        # Yay
        self.assertFalse(self.panel.drop(None, None))

    async def test_delete_specific_widget(self):
        """Test deleting a specific widget"""

        self.assertEqual(len(self.panel.operation_widgets), 0)
        self.panel.add_operation(VALID_OPERATION_NAME, args=VALID_OPERATION_ARGUMENTS)
        self.assertEqual(len(self.panel.operation_widgets), 1)

        widget = self.panel.operation_widgets[0]

        # Assert removing a specific widget removes it
        self.panel.delete(widget, 0, 0, 0, 0)
        self.assertEqual(len(self.panel.operation_widgets), 0)

    async def test_textfield_hover(self):
        """Test hovering over a text field"""

        self.panel.add_operation(VALID_OPERATION_NAME)

        widget = self.panel.operation_widgets[0]
        text_widget = widget._widgets_by_name["rootPath"]

        await ui_test.wait_n_updates(2)

        pos = ui_test.Vec2(
            text_widget.screen_position_x + text_widget.computed_width - 30,
            text_widget.screen_position_y + (text_widget.computed_height / 2),
        )

        await ui_test.emulate_mouse_move(pos, 1)
        await ui_test.wait_n_updates(2)

        # Now move away from the clear button
        end_pos = ui_test.Vec2(text_widget.screen_position_x, text_widget.screen_position_y)

        # await ui_test.emulate_mouse_move(pos, 5)
        await emulate_mouse_slow_move(pos, end_pos, num_steps=8, human_delay_speed=4)
        await ui_test.wait_n_updates(2)

    async def test_textfield_clear(self):
        """Test clicking the "clear" button on a widget"""

        self.panel.add_operation(VALID_OPERATION_NAME)

        widget = self.panel.operation_widgets[0]
        text_widget = widget._widgets_by_name["rootPath"]

        text_widget.set_value("test value")

        self.assertEqual(text_widget.get_value(), "test value")

        await ui_test.wait_n_updates(2)

        pos = ui_test.Vec2(
            text_widget.screen_position_x + text_widget.computed_width - 30,
            text_widget.screen_position_y + (text_widget.computed_height / 2),
        )

        await ui_test.emulate_mouse_move(pos, 1)
        await ui_test.wait_n_updates(2)

        # Click (not right, not double)
        await ui_test.emulate_mouse_click(False, False)

        await ui_test.wait_n_updates(2)

        self.assertEqual(text_widget.get_value(), "")

    async def test_joined_args(self):
        """Test joinNext arguments"""

        self.panel.add_operation(OPERATION_DECIMATE)

        widget = self.panel.operation_widgets[0]
        await ui_test.wait_n_updates(2)

        # Assert the widget was created as expected
        self.assertTrue(widget)

    async def test_text_list(self):
        """Test TextList widget"""

        self.panel.add_operation(OPERATION_OPTIMIZE_PRIMVARS)

        widget = self.panel.operation_widgets[0]
        text_widget = widget._widgets_by_name["primvars"]

        await ui_test.wait_n_updates(2)

        # Can't set string, must set list
        text_widget.set_value("foo bar")
        await ui_test.wait_n_updates(2)
        value = text_widget.get_value()
        self.assertListEqual(value, [])

        # Set valid list
        text_widget.set_value(["foo", "bar"])
        await ui_test.wait_n_updates(2)
        value = text_widget.get_value()
        self.assertListEqual(value, ["foo", "bar"])

    async def test_bool_widget_invalid_value(self):
        """Test setting invalid bool value"""

        args = {"displayName": "test"}
        widget = argument_widgets.BoolArgumentWidget(args)
        self.assertEqual(widget.get_value(), False)

        # Should do nothing, as it is not a bool
        widget.set_value(50)
        self.assertEqual(widget.get_value(), False)

        widget.set_value(True)
        self.assertTrue(widget.get_value())

    async def test_dialog_filter(self):
        """Test file dialog filter"""

        class MockDialog:
            def __init__(self, filter):
                self.current_filter_option = filter

        class MockItem:
            def __init__(self, folder, path=""):
                self.is_folder = folder
                self.path = path

        # Filter out folders
        self.assertTrue(self.panel.on_filter_item(MockDialog(0), MockItem(True)))

        # Only JSON supported
        self.assertFalse(self.panel.on_filter_item(MockDialog(0), MockItem(False, "foo.txt")))

        # Filter option
        self.assertTrue(self.panel.on_filter_item(MockDialog(1), MockItem(False, "foo.txt")))

        # Filter option
        self.assertTrue(self.panel.on_filter_item(MockDialog(0), MockItem(False, "foo.json")))

    async def test_nucleus_link(self):
        """Test nucleus link"""

        # Mock JSON data to avoid having to authenticate with nucleus
        json_data = """[
            {
              "operation": "optimizeMaterials",
              "materialPrimPaths": [],
              "optimizeMaterialsMode": 0
            },
            {
              "operation": "merge",
              "meshPrimPaths": [],
              "considerMaterials": true,
              "materialAlbedoAsVertexColors": false,
              "parentXform": false,
              "considerMetadata": false,
              "originalGeomOption": 1,
              "rootPath": "",
              "notes": ""
            },
            {
              "operation": "pruneLeaves",
              "pruneMode": 0
            }
        ]
        """

        # Patch read_file to return valid JSON data
        with patch(
            "omni.client.read_file",
            MagicMock(return_value=(omni.client.Result.OK, "", memoryview(bytes(json_data, "utf-8")))),
        ) as mock_client:
            # Fake URL with an omniverse prefix, which will trigger the mocked read
            self.panel.filepath = "omniverse://mock/test/data.json"
            self.panel.proceed_load_definition()

        # Wait for UI to rebuild
        await ui_test.wait_n_updates(2)
        self.assertEqual(len(self.panel.operation_widgets), 3)

    async def test_invalad_nucleus_link(self):
        """Test invalid nucleus link"""

        with self.assertRaises(Exception):
            self.panel.filepath = "https://example.invalid/test/data.json"
            self.panel.proceed_load_definition()

    async def test_carb_stats_population(self):
        """Test populating carb::stats"""

        await ui_test.wait_n_updates(2)

        # Enable the statistics setting that triggers SO to start processing stats
        settings = carb.settings.get_settings()
        settings.set_bool("/profiler/enableDeviceUtilizationQuery", True)

        # Bit of time to get things ready
        await ui_test.wait_n_updates(6)

        # Create a stage
        self.assertTrue(omni.usd.get_context().new_stage())
        stage = omni.usd.get_context().get_stage()

        # Create a prim, which will trigger a stats update
        stage.DefinePrim("/World", "Xform")

        # Wait >500ms (the configured delay in SO) for our callbacks to process
        # Windows needs a touch more time
        time.sleep(0.6)
        await ui_test.wait_n_updates(2)

        # Find the scope that should have now been created
        stats = omni.stats.get_stats_interface()
        scopes = stats.get_scopes()

        scope_node = None
        for scope in scopes:
            if "Scene Optimizer" in scope["name"]:
                scope_node = scope
                break

        # Assert stats have been added
        self.assertIsNotNone(scope_node)

        def get_stats(scope_node):
            """Extract a couple of stats to use as verification"""
            xforms = 0
            meshes = 0
            materials = 0

            stat_nodes = stats.get_stats(scope_node["scopeId"])

            for node in stat_nodes:
                if node["name"] == "typeXform":
                    xforms = node["value"]
                elif node["name"] == "typeMesh":
                    meshes = node["value"]
                elif node["name"] == "totalMaterials":
                    materials = node["value"]

            return (xforms, meshes, materials)

        # Assert expected counts
        xforms, meshes, materials = get_stats(scope_node)
        self.assertEqual(xforms, 1)
        self.assertEqual(meshes, 0)
        self.assertEqual(materials, 0)

        # Create some more prims, with a delay
        # This is to trigger the event coalescer in to rescheduling itself
        # between the prims being added
        stage.DefinePrim("/World/Mesh1", "Mesh")

        papi = UsdGeom.PrimvarsAPI(stage.GetPrimAtPath("/World/Mesh1"))
        primvar = papi.CreatePrimvar("displayColor", Sdf.ValueTypeNames.Color3f)
        primvar.Set([(1, 0, 0), (1, 1, 0), (1, 1, 1), (0, 1, 0), (0, 1, 1), (0, 0, 1)])

        time.sleep(0.2)
        await ui_test.wait_n_updates(2)
        stage.DefinePrim("/World/Mesh2", "Mesh")
        stage.DefinePrim("/World/Material1", "Material")

        # Wait for stats to update again
        time.sleep(0.6)
        await ui_test.wait_n_updates(2)

        xforms, meshes, materials = get_stats(scope_node)
        self.assertEqual(xforms, 1)
        self.assertEqual(meshes, 2)
        self.assertEqual(materials, 1)

        # "Edit" a prim
        await ui_test.wait_n_updates(2)
        imageable = UsdGeom.Imageable(stage.GetPrimAtPath("/World/Mesh2"))
        imageable.MakeInvisible()
        await ui_test.wait_n_updates(2)

        # Edit a known prim that we will skip updates on
        camPrim = stage.DefinePrim("/OmniverseKit_Persp", "Camera")
        await ui_test.wait_n_updates(2)
        camPrim.CreateAttribute("testAttr", Sdf.ValueTypeNames.Int).Set(1)
        await ui_test.wait_n_updates(2)

        # Remove a prim
        stage.RemovePrim("/World/Mesh1")
        # Wait for stats to update again
        time.sleep(0.6)
        await ui_test.wait_n_updates(2)

        xforms, meshes, materials = get_stats(scope_node)
        self.assertEqual(xforms, 1)
        self.assertEqual(meshes, 1)
        self.assertEqual(materials, 1)

        # Now disable settings, to get coverage on the cleanup code.
        # But trigger an update first, so we also trigger the "wait"
        # code during cleanup.
        await ui_test.wait_n_updates(2)
        stage.DefinePrim("/World/Mesh3", "Mesh")
        time.sleep(0.1)
        await ui_test.wait_n_updates(2)

        settings.set_bool("/profiler/enableDeviceUtilizationQuery", False)
        time.sleep(0.2)
        await ui_test.wait_n_updates(2)
