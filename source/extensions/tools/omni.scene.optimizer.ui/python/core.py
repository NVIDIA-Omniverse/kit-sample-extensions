# SPDX-FileCopyrightText: Copyright (c) 2022-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.


import asyncio
import json
import os
import posixpath
import re
from contextlib import suppress
from functools import partial

import carb
import carb.settings
import omni.client
import omni.kit.commands
import omni.kit.window.cursor

# scene optimizer core
import omni.scene.optimizer.core
import omni.ui as ui
import omni.usd
from omni.kit.menu.utils import MenuItemDescription
from omni.kit.widget.filebrowser import FileBrowserItem
from omni.kit.window.filepicker import FilePickerDialog
from omni.kit.window.popup_dialog import MessageDialog
from pxr import UsdUtils

# scene optimizer ui
from .argument_widgets import GroupedArgumentWidget, JoinedArgumentWidget, construct_argument_widget
from .collapsable import CollapsibleWidget
from .operation_info import get_operation_info_for_execution_context
from .preset_info import get_preset_info_for_execution_context
from .report import Report
from .style import ARG_STYLE, DRAG_BUTTON_STYLE, HEADER_STYLE
from .tabs import BaseTab, TabGroup
from .utils import ImageAndTextButton, get_icon, show_tooltip

MIME_TYPE_REORDER = "SceneOptimizerReorder"

SCENE_OPTIMIZER_MENU = "Window/Utilities/Scene Optimizer"

SCENE_OPTIMIZER_MAX_RECENT_PRESETS = 5
SCENE_OPTIMIZER_RECENT_PRESETS = "/persistent/exts/sceneOptimizer/presets"

# Shared access to scene optimizer plugin interface
__IFACE__ = None


def get_iface():
    """Get the scene optimizer interface"""
    global __IFACE__
    if __IFACE__ is None:
        __IFACE__ = omni.scene.optimizer.core.acquire_interface()
    return __IFACE__


def release_iface():
    """Release the interface"""
    global __IFACE__
    if __IFACE__ is not None:
        omni.scene.optimizer.core.release_interface(__IFACE__)
        __IFACE__ = None


def get_default_execution_context():
    """Get an execution context, configured with appropriate default values."""
    context = omni.scene.optimizer.core.ExecutionContext()
    context.generateReport = True
    context.captureStats = True

    return context


class OperationWidget(CollapsibleWidget):
    """
    A widget to allow defining and configuring a SceneOptimizer Operation to run
    """

    def __init__(self, info, delete_fn, collapsed, args={}):
        # Stash the info for this operation
        self._info = info
        self._args = args

        # Construct and track the widgets for each argument
        self._widgets_by_name = {}
        self._group_widgets = []
        self._group_widgets_by_name = {}
        self._groups = dict()

        # Any conditional args we might need to handle
        self._conditional_args = []

        # Optional function to be used as a callback after the Execute button
        # is clicked
        self._execute_fn = None

        # Create a tooltip from the description and author
        tooltip = ""
        if "description" in self._info:
            tooltip += self._info["description"]

        if "version" in self._info:
            version = self._info["version"]
            tooltip += "\n\nv{}.{}.{}".format(version.major, version.minor, version.rev)
            tooltip += " - "

        if "author" in self._info:
            tooltip += self._info["author"]

        self._tooltip = tooltip

        # Initialize base class, which will call the build function
        super().__init__(info["displayName"], self._build_operation_widgets, delete_fn, collapsed)

    def __del__(self):

        # Notify ArgumentWidgets they should tidy up.
        for _, widget in self._widgets_by_name.items():
            widget.tidy_up()

    def get_tooltip(self):
        """Return the tooltip for this widget"""
        return self._tooltip

    def ui_visibility_changed(self, visible):
        """Called if the main ui visibility changes"""
        if not visible:
            for _, widget in self._widgets_by_name.items():
                widget.tidy_up()

        # Trigger refresh of the menu, to ensure the ticked state is correct
        # next time someone looks at it
        omni.kit.menu.utils.refresh_menu_items(SCENE_OPTIMIZER_MENU)

    def name(self):
        """Return the operation name of this widget"""
        return self.get_args()["operation"]

    def _build_operation_widgets(self):
        """Build the individual operation widgets"""

        # Construct the Collapsable Frame Widget for the Operation
        label = self._info["displayName"]

        def get_joined(arguments, index):
            """Returns a list of arguments in sequence that should be
            joined together
            """

            joinName = arguments[index]["metadata"]["joinNext"]

            # If this is a join group, then skip to process the args
            if "group" in arguments[index]:
                index += 1

            joinedArgs = [arguments[index]]
            _nextArg = arguments[index + 1]

            while _nextArg != None:

                # If this is a conditional arg then mark that we have one
                if "enableIf" in _nextArg["metadata"] or "visibleIf" in _nextArg["metadata"]:
                    self._conditional_args.append(_nextArg.get("name"))

                joinedArgs.append(_nextArg)
                index += 1

                if (
                    index + 1 >= len(arguments)
                    or "joinNext" not in arguments[index + 1]["metadata"]
                    or joinName != arguments[index + 1]["metadata"]["joinNext"]
                ):
                    _nextArg = None
                else:
                    _nextArg = arguments[index + 1]

            return joinedArgs

        # Construct a Vertical Stack to hold the Argument Widgets
        with ui.VStack():

            # Construct Widgets for each of the arguments
            arguments = self._info.get("arguments", [])

            i = 0
            while i < len(arguments):
                argument = arguments[i]
                arg_name = argument.get("name")

                # If this is a conditional arg then mark that we have one
                if "enableIf" in argument["metadata"] or "visibleIf" in argument["metadata"]:
                    self._conditional_args.append(arg_name)

                widgets = None

                # for join-next widgets we want to collect them in a list, so we can
                # construct a join widget from them.
                if "joinNext" in argument["metadata"]:
                    joinedArgs = get_joined(arguments, i)
                    i += len(joinedArgs) - 1

                    if "group" in argument:
                        i += 1

                    # Construct group widget from the joined args
                    widget = construct_argument_widget(joinedArgs)
                    widgets = widget.get_child_widgets()

                    self._group_widgets.append(widget)

                # Groups are similar to joinNext - we need to collect the grouped
                # arguments and pass them on
                elif "group" in argument:

                    groupSize = argument["group"]
                    groupedArgs = []

                    j = 0
                    index = i + 1

                    while j < groupSize:

                        _argument = arguments[index]

                        # Also check for joined args, so they can appear indented
                        # within a group
                        if "joinNext" in _argument["metadata"]:

                            joinedArgs = get_joined(arguments, index)
                            index += len(joinedArgs)

                            if "group" in _argument:
                                index += 1

                            for joinedArg in joinedArgs:
                                self._groups[joinedArg.get("name")] = argument.get("name")

                            groupedArgs.append(joinedArgs)
                        else:
                            self._groups[_argument.get("name")] = argument.get("name")
                            groupedArgs.append(_argument)
                            index += 1

                        j += 1

                        meta = _argument["metadata"]
                        if "enableIf" in meta or "visibleIf" in meta:
                            self._conditional_args.append(_argument.get("name"))

                    # Bump index by all of the group members as they've been processed
                    i = index - 1

                    widget = construct_argument_widget(groupedArgs, group=True)
                    widgets = dict()

                    # Bit of extra pain to extract all the child widgets here
                    childWidgets = widget.get_child_widgets()
                    for childName, childWidget in childWidgets.items():
                        if isinstance(childWidget, JoinedArgumentWidget):
                            joinedWidgets = childWidget.get_child_widgets()
                            for joinedName, joinedWidget in joinedWidgets.items():
                                widgets[joinedName] = joinedWidget
                        else:
                            widgets[childName] = childWidget

                    self._group_widgets.append(widget)
                    self._group_widgets_by_name[argument.get("name")] = widget
                else:
                    # Construct standard argument widget
                    widget = construct_argument_widget(argument)
                    widgets = {arg_name: widget}

                    # We add invisible arguments so that JSON configs with custom
                    # values for hidden arguments are respected.
                    # There are some hidden types that do not have a widget - we
                    # can't get/set a value on those or create them, so they must
                    # be skipped.
                    if widget:
                        widget.visible = argument["metadata"].get("visible", True)
                    else:
                        i += 1
                        continue

                # For any of the new widgets set their value/update function
                for widget_name, widget in widgets.items():

                    widget.set_control_state_updated_fn(self._argument_updated)

                    # Attempt to get an initial value from initial values
                    arg_value = self._args.get(widget_name)
                    if arg_value is not None:
                        widget.set_value(arg_value)

                    # Store the widget so we can get all argument values.
                    self._widgets_by_name[widget_name] = widget

                i += 1

            # If the operation has an associated Command add a button to Execute the Operation
            if self.name() != "executionContext":

                with ui.HStack():

                    # Dummy label to align button with argument widgets.
                    ui.Label("", width=160, height=0, style=ARG_STYLE)

                    button = ui.Button("Execute - {}".format(label), height=30)
                    button.set_clicked_fn(self.execute)
                    button.set_tooltip("Execute this Operation")

        # Now that all args are built, trigger an update so any conditional args
        # can configure their initial state.
        self._update_conditional_args()

    def _argument_updated(self, arg_name):
        """Called when any of the arguments of this widget are updated"""
        self._update_conditional_args()

    def _update_conditional_args(self):
        """Process any conditional args of this widget to update their
        state based on the other argument values.
        """

        hidden_groups = set()

        # Check any conditional args to see if their state has been
        # affected.
        for arg in self._conditional_args:

            arg_info = self._get_arg_info(arg)
            meta = arg_info["metadata"]

            # Locals are just the arg names/values
            _locals = self.get_args()
            _enable = True
            _visible = True

            # Conditionally enabled arguments
            # Note: the exceptions are disabled from coverage, this is primarily a
            # debug message
            if "enableIf" in meta:
                # Use eval for simplicity
                try:
                    _enable = eval(meta["enableIf"], {"__builtins__": None}, _locals)
                except Exception as ex:  # pragma: no cover
                    print("Failed to eval enableIf:", ex)

            # Conditionally visible arguments
            if "visibleIf" in meta:
                try:
                    _visible = eval(meta["visibleIf"], {"__builtins__": None}, _locals)
                except Exception as ex:  # pragma: no cover
                    print("Failed to eval visibleIf:", ex)

            # Adjust the state of the widget.
            # Note that when the arguments are being (re)built, it's possible that
            # the affected argument widget may not exist just yet, due to set_value
            # being called (and therefore this function) as the widgets are created
            if arg in self._widgets_by_name:
                # Visibility is very sensitive.
                # If the parent group is collapsed, don't change any visibility
                # settings, otherwise the layout can get mucked up.
                if arg in self._groups and self._groups[arg] in hidden_groups:
                    continue

                widget = self._widgets_by_name[arg]
                widget.enabled = _enable
                widget.visible = _visible

            elif arg in self._group_widgets_by_name:
                widget = self._group_widgets_by_name[arg]

                # Update the group via async, as otherwise it can
                # get a bit confused and mess up the layout.
                async def toggle_group(widget, enabled, visible):
                    widget.enabled = enabled
                    widget.visible = visible

                asyncio.ensure_future(toggle_group(widget, _enable, _visible))

                # Track this group is hidden so when we find any children
                # we can avoid updating them for now.
                if not _visible:
                    hidden_groups.add(arg)

        # For group widgets, check if all of their children are hidden.
        # If so, hide the parent group widget itself as well.
        for widget in self._group_widgets:
            # Group is already hidden conditionally, no need to
            # do anything here
            if isinstance(widget, GroupedArgumentWidget) and not widget.visible:
                continue

            all_hidden = True
            for child_name in widget.get_child_widgets():
                if child_name in self._widgets_by_name:
                    child_widget = self._widgets_by_name[child_name]
                    if child_widget.visible:
                        all_hidden = False
                        break
            widget.visible = not all_hidden

    def _get_arg_info(self, arg_name):
        """Return the argument info dict"""
        for arg in self._info["arguments"]:
            if arg["name"] == arg_name:
                return arg
        return None

    def get_args(self):
        """Return a dictionary of the argument values from the widget keyed by name"""
        result = {"operation": self._info["name"]}
        for arg_name, arg_widget in self._widgets_by_name.items():
            result[arg_name] = arg_widget.get_value()
        return result

    def get_args_serialized(self):
        """Return a serialized JSON string of the argument values from a widget"""
        args = self.get_args()
        return json.dumps(args)

    def set_execute_fn(self, execute_fn):
        """Set a callback function for after the command has been executed"""
        self._execute_fn = execute_fn

    def execute(self):
        """Execute the kit command associated with this operation using the argument values from the widget"""

        # Get the name of the operation
        name = self._info["name"]

        # Get the command arguments from the current state of the widget
        args = self.get_args_serialized()
        context = get_default_execution_context()
        stage = omni.usd.get_context().get_stage()
        if stage is not None:
            stage_id = UsdUtils.StageCache().Get().Insert(stage).ToLongInt()
            context.usdStageId = stage_id

        # If capture stats is specified on the context, do before and after stats
        if context.captureStats:
            omni.kit.commands.execute("SceneOptimizerOperation", operation="printStats", context=context)

        # Execute the command
        omni.kit.commands.execute("SceneOptimizerOperation", operation=name, args=args, context=context)

        # And the after stats
        if context.captureStats:
            omni.kit.commands.execute("SceneOptimizerOperation", operation="printStats", context=context)

        # If there is a callback, trigger it
        if self._execute_fn:
            self._execute_fn(args, context)


class ReportTab(BaseTab):
    """An individual report tab"""

    def __init__(self, name, reportPath):

        super().__init__(name)

        self.reportPath = reportPath

        # A cache of the report widgets for this tab. This is actually a workaround
        # for an issue where ui.AbstractItemDelegate will fail with obscure warnings
        # if its lifetime is not manually maintained. The ReportTab is maintained so
        # having a cache here lets us keep a reference to the various child widgets.
        self.widgets = list()

    def build_fn(self):
        """Build the widget.

        Parses info out of the report, then iterates the various entries creating
        CollapsableWidgets and constructing them.
        """

        # Parse the report
        report = Report(self.reportPath)

        with ui.VStack(style={"margin": 1}):
            with ui.ScrollingFrame(width=ui.Percent(100), height=ui.Percent(98)):
                with ui.VStack(height=0):

                    for entryGroup in report.entryGroups:
                        title = "{} ({})".format(entryGroup.operation, entryGroup.time)

                        # By default, collapse Stats entries to hide the clutter and make the actual
                        # operation result more visible.
                        collapsed = False
                        if entryGroup.operation == "Stats":
                            collapsed = True

                        cw = CollapsibleWidget(
                            title, partial(entryGroup.build_widget, self), collapsed=collapsed, draggable=False
                        )

            ui.Spacer(width=0)


class OperationsTab(BaseTab):
    """The main Scene Optimizer interface tab"""

    def __init__(self, name, panel, collapsed=False, args=None):

        super().__init__(name, closeable=False)
        self._panel = panel
        self._args = args
        self._collapsed = collapsed

    def build_fn(self):
        """Build the main Operations UI"""

        # Constants
        image_width = 20
        button_width = 110

        with ui.VStack(width=ui.Percent(100)):

            with ui.VStack(style=HEADER_STYLE):

                # Top header - Load/Save, Execute, Clear
                with ui.HStack(width=ui.Percent(100), height=0):

                    ImageAndTextButton(
                        "Load Preset",
                        image_path=get_icon("folder.svg"),
                        width=button_width,
                        height=30,
                        image_width=image_width,
                        image_height=30,
                        mouse_pressed_fn=self._panel.load_preset,
                        tooltip="Load a preset layout of processes with specific settings or a file that has been previously saved",
                    )

                    ImageAndTextButton(
                        "Save Preset",
                        image_path=get_icon("save.svg"),
                        width=button_width,
                        height=30,
                        image_width=18,
                        image_height=18,
                        mouse_pressed_fn=partial(self._panel.file_dialog, self._panel.save_definition, "Save"),
                        tooltip="Save all settings and processes to disk as a preset in .json",
                    )

                    ImageAndTextButton(
                        "Execute All",
                        image_path=get_icon("execute_all.svg"),
                        width=button_width,
                        height=30,
                        image_width=image_width,
                        image_height=30,
                        mouse_pressed_fn=self._panel.execute,
                        tooltip="Execute all processes in order of operations, starting from the top",
                    )

                    # Rather than a vertical separator?
                    ui.Label("")

                    ImageAndTextButton(
                        "Clear All Processes",
                        image_path=get_icon("remove.svg"),
                        width=button_width,
                        height=30,
                        image_width=image_width,
                        image_height=30,
                        mouse_pressed_fn=self._panel.clear,
                        tooltip="Remove all processes",
                    )

                    # Spacer to allow lining the right edge of the buttons up with the
                    # scrolling frame below.
                    ui.Spacer(width=ui.Pixel(14))

                # Custom button to work around not being able to properly center an icon/label.
                # Also in an HStack to add a spacer to line things up with the scrollbar.
                with ui.HStack(width=ui.Percent(100), height=0):
                    ImageAndTextButton(
                        "Add Scene Optimizer Process",
                        image_path=get_icon("add.svg"),
                        width=ui.Percent(98),
                        height=30,
                        image_width=14,
                        image_height=30,
                        mouse_pressed_fn=self._panel.menu,
                        tooltip="Add a new process",
                    )
                    ui.Spacer(height=0, width=ui.Pixel(1))

            # Main operations widget area
            with ui.ScrollingFrame(width=ui.Percent(100)):

                self._panel.stack = ui.VStack(height=0)

                # Set various drag/drop/mouse handling functions
                self._panel.stack.set_accept_drop_fn(self._panel.drop_accept)
                self._panel.stack.set_drop_fn(partial(self._panel.drop, MIME_TYPE_REORDER))
                self._panel.stack.set_mouse_moved_fn(self._panel.mouse_moved)
                self._panel.stack.set_mouse_released_fn(self._panel.mouse_released)

                # Get either passed in args or args from self.operation_widgets, and zip with the
                # expected collapsed state.
                _actual_args = list()

                if self._args is None:
                    _actual_args = [(w.get_args(), w.collapsed) for w in self._panel.operation_widgets]
                else:
                    _actual_args = list(zip(self._args, [self._collapsed] * len(self._args)))

                # Now that we have copied the args (if we are rebuilding existing widgets)
                # we can nuke the existing widgets and rebuild.
                self._panel.operation_widgets.clear()
                self._panel.drop_targets = list()

                for _args, _collapsed in _actual_args:
                    if self._panel.is_valid_operation(_args["operation"]):
                        self._panel.add_operation(_args["operation"], collapsed=_collapsed, args=_args)


class SceneOptimizerPanel:
    def __init__(self):

        self.operation_widgets = []  # Operation Widgets
        self.filepath = ""

        self.drop_targets = []
        self.drag_widget = None
        self.drop_index = -1

        self._command_menu = ui.Menu(menu_compatibility=False, style={"padding": 2})
        self._preset_menu = ui.Menu(menu_compatibility=False, style={"padding": 2})

        self._reports = []  # Any reports that have been created this session

        self.window = ui.Window("Scene Optimizer", width=600, height=600)
        self.update_ui()

        # Reuseable popup dialog windows
        self._popup_dialog = None
        self._popup_dialog_ok = None
        self._security_warning_dialog = None

        self._settings = carb.settings.get_settings()

    def get_operator_info(self, name):
        """Get the operator metadata for the specified operation"""

        # Special case for executionContext
        if name == "executionContext":
            return get_operation_info_for_execution_context()

        iface = get_iface()

        # Otherwise it's a registered op
        displayName = iface.get_operation_display_name(name)
        arguments = iface.get_operation_arguments(name)
        description = iface.get_operation_description(name)
        version = iface.get_operation_version(name)
        author = iface.get_operation_author(name)
        info = {
            "name": name,
            "displayName": displayName,
            "arguments": arguments,
            "description": description,
            "author": author,
            "version": version,
        }

        return info

    def ui_visibility_changed(self, visible):
        """Called if the main ui visibility changes"""
        for widget in self.operation_widgets:
            widget.ui_visibility_changed(visible)

    def mouse_released(self, posX, posY, i, b):
        """Called when the mouse is released"""

        # Reset all drop targets
        for target in self.drop_targets:
            target.style = {"background_color": 0x0}

    def reorder_mouse_hovered(self, over):
        """Called when the mouse enters/exits the reorder button."""

        if over:
            # If the mouse enters, change to a hand cursor to indicate the user can interact
            window_cursor = omni.kit.window.cursor.get_main_window_cursor()
            window_cursor.override_cursor_shape(carb.windowing.CursorStandardShape.HAND)
        elif not self.drag_widget:
            # If the mouse exits, clear the cursor - unless we are dragging. In this we want
            # to retain the hand, and it will be cleared when the drag finishes.
            window_cursor = omni.kit.window.cursor.get_main_window_cursor()
            window_cursor.clear_overridden_cursor_shape()

    def mouse_moved(self, posX, posY, i, b):
        """Called when the mouse is moving, with a button pressed"""

        if not self.stack.dragging:
            return

        if not self.drag_widget:
            return

        # Suppress exception if widget isn't found
        try:
            drag_target_index = self.operation_widgets.index(self.drag_widget)
        except ValueError:  # pragma: no cover
            return

        # Reset drop index since the mouse has moved
        self.drop_index = -1

        # See if we are over a drop target. If so, record it and highlight the target
        for index, target in enumerate(self.drop_targets):

            pos = (target.screen_position_x, target.screen_position_y)
            width = target.computed_width
            height = target.computed_height

            valid = False

            # Use a bit of a buffer around the height of the drop target. This means we
            # don't have to be directly over it so it's a lot easier
            padding = 10

            # Check if we are over this particular drop target.
            if (
                posX > pos[0]
                and posX < pos[0] + width
                and posY > (pos[1] - padding)
                and posY < (pos[1] + height + padding)
            ):

                # If so, is it a valid position to move the widget we are dragging?
                # Essentially valid means "not the drop target immediately before or after
                # the widget"
                if index != drag_target_index and index != drag_target_index + 1:
                    valid = True
                    self.drop_index = index

            # If its valid highlight, otherwise for all rects reset their color.
            if valid:
                target.style = {"background_color": 0xFFF49454}
            else:
                target.style = {"background_color": 0x0}

        return

    def drop_accept(self, mime):
        """Whether to accept a drop."""

        # This is counter-intuitive, but basically we're handling dragging in
        # mouse moved. So just return False here. Otherwise this ends up
        # sometimes swallowing the drop and causing clicks to not register.
        return False

    def drop(self, a, b):
        """Currently unused"""
        return False

    def drag_begin(self, mime, widget):
        """Called when a drag operation begins"""

        # Is this a reorder operation?
        if mime != MIME_TYPE_REORDER:
            return None

        # Record the widget
        self.drag_widget = widget

        # Create the thing that is dragged. For our purpose we will use a collapsed
        # version of the operation. Could do anything here, just create a simple label
        # or have it expanded, or whatever..
        with ui.VStack(width=widget.width()):
            info = self.get_operator_info(widget.name())
            OperationWidget(info, None, True)

        return MIME_TYPE_REORDER

    def drag_ended(self, x, y, i, b):
        """Called when the drag ends.

        I had mixed results using the drop function, drag_ended seemed to be a much more
        reliable place to actually perform the drop.

        We still validate there is a drop index and widget, then do the actual reorder.
        """

        # Reset cursor
        window_cursor = omni.kit.window.cursor.get_main_window_cursor()
        window_cursor.clear_overridden_cursor_shape()

        if self.drop_index == -1:
            return False

        if not self.drag_widget:
            return False

        # Record the original index from widgets so we can remove it later
        original_index = self.operation_widgets.index(self.drag_widget)

        # Copy the widget to the drop location, which because of the drop targets,
        # is always the right place to push it.
        self.operation_widgets.insert(self.drop_index, self.drag_widget)

        # If we inserted before the original index then we need to bump that!
        if self.drop_index < original_index:
            original_index += 1

        # Remove the original
        self.operation_widgets.pop(original_index)

        # Reset, drop is done
        self.drop_index = -1
        self.drag_widget = None

        # Rebuild UI
        self.update_ui()

    def update_ui(self, args=None, collapsed=False):
        """Rebuild the main UI"""

        # Push the update to a subsequent tick.
        # This function can be called within a draw callback, and if that is the case
        # a warning will be printed to the shell while building UI elements.
        asyncio.ensure_future(self._update_ui(args, collapsed))

    async def _update_ui(self, args=None, collapsed=False):
        """Rebuild the main UI"""

        # Always include the primary Operations tab
        tabs = [OperationsTab("Operations", self, collapsed, args)]

        # Add any reports that have been tracked
        for index, report in enumerate(self._reports):
            # See report_tab_closed for an explanation
            if report is None:
                continue
            tabs.append(ReportTab("Report {}".format(index + 1), self._reports[index]))

        # Under the main frame create a tab group with the tabs
        with self.window.frame:
            with ui.ScrollingFrame(width=ui.Percent(100)):
                self.tab_group = TabGroup(tabs)
                self.tab_group.set_closed_fn(self.report_tab_closed)

    def report_tab_closed(self, tab):
        """Callback for when a report tab is closed"""

        # Find the index of the tab that was closed. We clear out the report here
        # by setting it to None. This means if the UI gets rebuilt later (eg a new
        # report is added) we keep the original numbering. Lazier than keeping a
        # static counter..?
        index = self._reports.index(tab.reportPath)
        self._reports[index] = None

    def menu(self, x, y, button, _):
        if button == 0:

            groups = dict()
            operation_display_names = dict()

            iface = get_iface()

            # Get raw list of operation names.
            operation_names = iface.get_operations()

            # First, filter invisible operations, and cache display names.
            for operation in operation_names:

                visible = iface.get_operation_visible(operation)

                if not visible:
                    continue

                group = iface.get_operation_display_group(operation)

                if group not in groups:
                    groups[group] = list()

                groups[group].append(operation)

                display_name = iface.get_operation_display_name(operation)
                operation_display_names[operation] = display_name

            # Clear and rebuild the menu
            self._command_menu.clear()
            with self._command_menu:

                # First add the Configure (executionContext) operation, with a separator
                item = ui.MenuItem("Configure", menu_compatibility=False)
                item.set_triggered_fn(partial(self.add_operation, "executionContext"))
                ui.Separator(menu_compatibility=False)

                # Each group is a submenu
                for group in sorted(groups):

                    menu = ui.Menu(group, menu_compatibility=False)
                    with menu:
                        # Add any registered+visible operations
                        for operation in sorted(groups[group], key=lambda k: operation_display_names[k]):
                            item = ui.MenuItem(operation_display_names[operation], menu_compatibility=False)
                            item.set_triggered_fn(partial(self.add_operation, operation))

            self._command_menu.show()

    def is_valid_operation(self, name):
        """Returns true if the name given represents a valid operation"""

        if name == "executionContext":
            return True

        # If it is not the Configure special-case then check the registered operations
        operations = get_iface().get_operations()
        return name in operations

    def add_operation(self, name, collapsed=False, args={}):
        """Add a new widget to the UI

        @param name Name of operation to add
        @param collapsed Collapsed state of the widget on construction
        @param args can either be default args or args from an existing widget to ensure we maintain any modified values
        when rebuilding the UI.
        """
        # Constants
        rect_height = 3

        # Early out if the name given is not a valid operation.
        if not self.is_valid_operation(name):
            return

        with self.stack:

            # First drop target
            if len(self.drop_targets) == 0:
                target = ui.Rectangle(height=rect_height, style={"background_color": 0x0})
                self.drop_targets.append(target)

            # Create ZStack. We create the button first (at the back). This means it renders
            # underneath the OperationWidget. BUT.. it also means it will actually accept
            # drag/drop operations. So what we do is put it underneath and wire it up to do
            # the drag. Then in the OperationWidget custom header we put a fake button over
            # the top that doesn't do anything - but serves as the "visual" part of this.
            #
            # Yes. I know.
            stack = ui.ZStack()

            # Due to a change in behaviour zstack by default now does not send mouse events
            # to the back. This is actually one of the benefits of using it in this case,
            # thankfully we can override this. It means the reorder button will get the drag
            # functions called on it when clicking it.
            stack.send_mouse_events_to_back = True

            with stack:

                # Create a button with the name drag, so it inherits its style.
                button = ui.Button(
                    " ",
                    width=30,
                    height=40,
                    name="drag",
                    style=DRAG_BUTTON_STYLE,
                    tooltip_fn=partial(show_tooltip, "Grab this handle and drag to reorder operations"),
                )

                # Create the actual operation widget next.
                info = self.get_operator_info(name)
                widget = OperationWidget(info, self.delete, collapsed, args=args)
                widget.set_execute_fn(self._widget_executed)
                self.operation_widgets.append(widget)

                # Now set the drag functions (passing a reference to the widget)
                button.set_drag_fn(partial(self.drag_begin, MIME_TYPE_REORDER, widget))
                button.set_mouse_released_fn(self.drag_ended)
                button.set_mouse_hovered_fn(self.reorder_mouse_hovered)

            # Add drop target after the widget also
            target = ui.Rectangle(height=rect_height, style={"background_color": 0x0})
            self.drop_targets.append(target)

    def clear(self, *arg):
        """Confirm whether the user actually wants to clear all the processes"""

        if len(self.operation_widgets) == 0:
            return None

        # Show message with an Ok handler. Do nothing on cancel.
        dialog = MessageDialog(
            title="Confirm Clear", message="Are you sure you want to clear all processes?", ok_handler=self._do_clear
        )
        dialog.show()
        return dialog

    def add_report_path(self, value):
        """Add the report path and update the UI accordingly"""
        if value is None:
            return

        self._reports.append(value)
        self.update_ui()

    def _widget_executed(self, args, context):
        """Called after an individual operation is executed"""

        # Add the report path, if there was one.
        self.add_report_path(context.reportPath)

    def _do_clear(self, dialog=None):
        """Clear all the processes"""

        # Hide the dialog.
        if dialog:
            dialog.hide()

        # Remove all the widgets/drop targets and refresh the UI.
        self.operation_widgets = []
        self.drop_targets = []
        self.update_ui()

    def execute(self, *arg):
        """Execute all of the operations in the operation stack"""
        # Populate the execution context
        context = get_default_execution_context()
        stage = omni.usd.get_context().get_stage()
        if stage is not None:
            stage_id = UsdUtils.StageCache().Get().Insert(stage).ToLongInt()
            context.usdStageId = stage_id

        captureStats = False if context.captureStats == 0 else True
        operationCount = 0

        # Need to find out whether captureStats is enabled, prior to executing any
        # operations.
        for operation_widget in self.operation_widgets:
            name = operation_widget.name()
            if name == "executionContext":
                args = operation_widget.get_args()
                if "captureStats" in args:
                    if int(args["captureStats"]) == 0:
                        captureStats = False

        # If stats are enabled then run before processing any other operation.
        if captureStats:
            omni.kit.commands.execute("SceneOptimizerOperation", operation="printStats", context=context)

        # Execute each operation in series
        for operation_widget in self.operation_widgets:

            name = operation_widget.name()

            # Special-case the execution context, which just sets values on the context prior
            # to executing the operation with it.
            if name == "executionContext":
                args = operation_widget.get_args()
                for key, value in args.items():
                    if key in ["debug", "singleThreaded", "verbose", "generateReport", "captureStats"]:
                        setattr(context, key, int(value))
            else:
                args = operation_widget.get_args_serialized()
                omni.kit.commands.execute("SceneOptimizerOperation", operation=name, args=args, context=context)
                operationCount += 1

        # If captureStats was enabled, AND there was some other operation, then include the
        # after stats. If there were no other operations this means captureStats would run
        # just the once - nothing would change, so that's all we need.
        if captureStats and operationCount:
            omni.kit.commands.execute("SceneOptimizerOperation", operation="printStats", context=context)

        # Add the report path from the context.
        # If one is found, this will trigger a new tab to be created for the report.
        self.add_report_path(context.reportPath)

    def delete(self, widget, x, y, i, b):
        """Delete the specified widget.

        This has extra args due to being from mouse_pressed, rather than clicked,
        because of CollapsableFrame madness.
        """
        self.operation_widgets.remove(widget)
        self.update_ui()

    def on_filter_item(self, dialog: FilePickerDialog, item: FileBrowserItem) -> bool:
        if not item or item.is_folder:
            return True
        if dialog.current_filter_option == 0:
            _, ext = os.path.splitext(item.path)
            if ext in [".json"]:
                return True
            else:
                return False
        else:
            return True

    def file_dialog(self, on_click_fn, label, *arg):
        dialog = FilePickerDialog(
            label + " Definition",
            apply_button_label=label,
            click_apply_handler=lambda filename, dirname: on_click_fn(dialog, filename, dirname),
            item_filter_options=["JSON files (*.json)", "All files (*)"],
            item_filter_fn=lambda item: self.on_filter_item(dialog, item),
        )
        dialog.show(path=self.filepath)
        return dialog

    def get_preset_with_name(self, name):
        """Get the name of the preset"""
        presets = get_preset_info_for_execution_context()
        for preset in presets:
            if preset["name"] == name:
                return preset
        return None

    def add_preset(self, *args):
        """Add JSON configs to load as a base preset"""
        preset_name = args[0]
        preset = self.get_preset_with_name(preset_name)
        if preset is None:
            print(f"Invalid preset name: {preset_name}")
            return

        if isinstance(preset, dict) and "arguments" in preset:
            self.proceed_update_ui(args=preset["arguments"], collapsed=True)
        else:
            print(f"Invalid preset: {preset}")

    def save_recent_preset(self):
        """Save the last chosen preset to the recently used list"""

        # Get the recently used list (or default to an empty list if it doesn't
        # exist)
        recent = self._settings.get(SCENE_OPTIMIZER_RECENT_PRESETS) or list()

        # We want to store the most recently used preset first. If it already
        # exists, remove, then either way it will be first.
        while self.filepath in recent:
            recent.remove(self.filepath)

        # Add as the most recent entry
        recent.insert(0, self.filepath)

        # Clamp to MAX entries
        recent = recent[0:SCENE_OPTIMIZER_MAX_RECENT_PRESETS]

        self._settings.set_string_array(SCENE_OPTIMIZER_RECENT_PRESETS, recent)

    def load_preset(self, x, y, button, _):
        if button == 0:
            self._preset_menu.clear()
            with self._preset_menu:
                presets = get_preset_info_for_execution_context()

                # First add the Load from file menu with a separator
                item = ui.MenuItem("Load JSON File", menu_compatibility=False)
                item.set_triggered_fn(partial(self.file_dialog, self.load_definition, "Load"))

                # Then add the other presets
                ui.Separator("Presets", menu_compatibility=False)
                for preset in presets:
                    item = ui.MenuItem(preset["displayName"], menu_compatibility=False)
                    item.set_triggered_fn(partial(self.add_preset, preset["name"]))

                # Check if there are any "recently used" presets, and add them
                recents = self._settings.get(SCENE_OPTIMIZER_RECENT_PRESETS)
                if recents and len(recents) > 0:
                    ui.Separator("Recently Used", menu_compatibility=False)

                    # Check the item is either an omniverse link or the file
                    # still exists
                    for recent in recents:
                        if recent.startswith("omniverse:") or os.path.isfile(recent):
                            item = ui.MenuItem(recent, menu_compatibility=False)
                            item.set_triggered_fn(
                                partial(self.load_definition, None, os.path.basename(recent), os.path.dirname(recent))
                            )

            self._preset_menu.show()

    def load_definition(self, dialog: FilePickerDialog, filename: str, dirname: str):
        if filename.split(".")[-1].lower() == "json":
            self.filepath = posixpath.join(dirname, filename)

            if dialog:
                dialog.hide()

            if len(self.operation_widgets):
                self.open_popup_dialog(
                    "Load",
                    "Do you want to discard the current stack of commands ?",
                    self.proceed_load_definition,
                    self.close_popup_dialog,
                )
            else:
                self.proceed_load_definition()

    def proceed_load_definition(self):
        self.close_popup_dialog()
        protocol = self.filepath.split(":")[0].lower()

        # Load file from nucleus server and store content to be accessible for json loading
        if protocol == "omniverse":
            result, read_str, read_content = omni.client.read_file(self.filepath)
            if result is not None and read_content != "":
                json_data = memoryview(read_content).tobytes()
                args = json.loads(json_data)

        else:
            # Read the JSON config file from local disk
            f = open(self.filepath)
            args = json.load(f)
            f.close()

        # Save the preset location in the list of recently used ones
        self.save_recent_preset()

        # Map the configuration. This ensures an older config is updated to handle any
        # renamed operations or arguments - necessary as the UI is built based on the
        # latest.
        iface = get_iface()
        args = json.loads(iface.map_config(json.dumps(args)))

        # Due to security concerns we need to inform the user of any python scripts in operations in stacks when a
        # config is loaded from disk. This ensures that we have done everything within reason to avoid a user executing
        # code that they do not know the behavior of.
        hasPython = any([x.get("operation", "") == "pythonScript" for x in args])
        if hasPython:

            # Build a partial to continue with the config loading on warning confirmation
            # We set "collapsed=False" here so that the code to be reviewed is visible.
            confirm_fn = partial(self.proceed_update_ui, args=args, collapsed=False)

            # We do not reuse the "open_popup_dialog" function here as the reuse of variables causes crashes when the
            # two dialogs are displayed in sequence. I suspect a threading issue.

            # Popup the security warning dialog.
            self.open_security_warning_dialog(
                "Security Warning",
                [
                    "This config contains executable python code.",
                    "Please review the code before executing the operations",
                ],
                confirm_fn,
                self.close_security_warning_dialog,
            )
            # Early out so that we only update the widgets if the security warning is accepted.
            return

        # Update the UI widgets to reflect the loaded config.
        self.proceed_update_ui(args=args, collapsed=True)

    def proceed_update_ui(self, args=None, collapsed=True):
        self.close_security_warning_dialog()
        self.update_ui(args=args, collapsed=collapsed)

    def save_definition(self, dialog: FilePickerDialog, filename: str, dirname: str):

        if not filename.split(".")[-1].lower() == "json":
            filename += ".json"
        self.filepath = posixpath.join(dirname, filename)

        if dialog:
            dialog.hide()

        if len(self.operation_widgets):
            if self.filepath.startswith("omniverse:"):
                self.proceed_save_definition_omniverse()
            else:
                if os.path.isfile(self.filepath):
                    self.open_popup_dialog(
                        "Save",
                        "File already exists, do you want to overwrite it ?",
                        self.proceed_save_definition,
                        self.close_popup_dialog,
                    )
                else:
                    self.proceed_save_definition()

    def proceed_save_definition_omniverse(self):
        """Save a JSON config to an omniverse URL"""
        self.close_popup_dialog()

        # Dump to JSON then encode to bytes
        data = json.dumps([w.get_args() for w in self.operation_widgets], indent=4)
        payload = bytes(data.encode("utf-8"))

        # Write to omniverse
        result = omni.client.write_file(self.filepath, payload)
        if result != omni.client.Result.OK:
            carb.log_warn(f"Cannot write {self.filepath}, error code: {result}.")
        else:
            self.save_recent_preset()

    def proceed_save_definition(self):
        self.close_popup_dialog()

        with suppress():
            f = open(self.filepath, "w")
            json.dump([w.get_args() for w in self.operation_widgets], f, indent=4)
            f.close()
            self.save_recent_preset()

    def open_popup_dialog(self, title, message, on_proceed_fn, on_cancel_fn):
        flags = ui.WINDOW_FLAGS_NO_RESIZE
        flags |= ui.WINDOW_FLAGS_NO_SCROLLBAR
        flags |= ui.WINDOW_FLAGS_MODAL
        self._popup_dialog = ui.Window("Confirm " + title, width=500, height=100, flags=flags)
        with self._popup_dialog.frame:
            with ui.VStack(name="root", style={"VStack::root": {"margin": 10}}, height=0, spacing=20):
                ui.Label("", alignment=ui.Alignment.CENTER).text = message
                with ui.HStack():
                    ui.Spacer()
                    self._popup_dialog_ok = ui.Button("Ok", clicked_fn=on_proceed_fn)
                    ui.Button("Cancel", clicked_fn=on_cancel_fn)
                    ui.Spacer()

    def close_popup_dialog(self):
        if self._popup_dialog:
            self._popup_dialog.visible = False

    def open_security_warning_dialog(self, title, message, on_proceed_fn, on_cancel_fn):
        """Open the security warning popup dialog"""
        flags = ui.WINDOW_FLAGS_NO_RESIZE
        flags |= ui.WINDOW_FLAGS_NO_SCROLLBAR
        flags |= ui.WINDOW_FLAGS_MODAL

        # Create the dialog window
        self._security_warning_dialog = ui.Window("Confirm " + title, width=500, height=100, flags=flags)
        with self._security_warning_dialog.frame:
            with ui.VStack(margin=10, height=0, spacing=10):

                # Create a stack of the lines in the message as centered labels.
                with ui.VStack(height=0, spacing=0):
                    for line in message:
                        ui.Label("", height=12, alignment=ui.Alignment.CENTER).text = line

                # Add confirm and cancel buttons with appropriate bound functions
                with ui.HStack():
                    ui.Spacer()
                    ui.Button("Ok", clicked_fn=on_proceed_fn)
                    ui.Button("Cancel", clicked_fn=on_cancel_fn)
                    ui.Spacer()

    def close_security_warning_dialog(self):
        """Close the security warning popup dialog"""
        if self._security_warning_dialog is not None:
            self._security_warning_dialog.visible = False


class SceneOptimizerUI:
    """Manager class for the Scene Optimizer UI extension"""

    def __init__(self):
        """Called on extension start up"""

        self._panel = SceneOptimizerPanel()
        self._panel.window.visible = False
        self._panel.window.set_visibility_changed_fn(self._panel_visibility_changed_fn)

        registry = omni.kit.actions.core.get_action_registry()

        # If the action already exists, deregister and we will create a new one
        # that uses this instance
        action = registry.get_action("omni.scene.optimizer.ui", "togglePanel")
        if action:
            registry.deregister_action(action)

        # Create an action that calls a function on this class
        self._action_toggle_panel = omni.kit.actions.core.Action(
            "omni.scene.optimizer.ui",
            "togglePanel",
            self._toggle_panel,
            display_name="Scene Optimizer UI>Toggle Panel",
            description="Toggle the Scene Optimizer UI.",
        )

        registry.register_action(self._action_toggle_panel)

        # Create the actual menu
        self._menu = MenuItemDescription(
            name="Scene Optimizer",
            ticked=True,
            ticked_fn=self._ticked_fn,
            onclick_action=("omni.scene.optimizer.ui", "togglePanel"),
        )

        # Menu list with the parent submenu
        self._menu_list = [
            MenuItemDescription(
                name="Utilities",
                glyph=None,
                sub_menu=[self._menu],
            )
        ]

        # Add to the Window menu
        omni.kit.menu.utils.add_menu_items(self._menu_list, "Window")

    def shutdown(self):
        """Called on extension shut down"""
        # Ensure we release references to the UI widgets owned by the extension.
        if self._panel is not None:
            del self._panel.window
        self._panel = None

        # Remove the menu
        omni.kit.menu.utils.remove_menu_items(self._menu_list, "Window")

        # Deregister action
        registry = omni.kit.actions.core.get_action_registry()
        registry.deregister_all_actions_for_extension("omni.scene.optimizer.ui")

        self._menu = None
        self._menu_list = None

        # Clean up plugin interface
        release_iface()

    def _ticked_fn(self):
        """Callback for menu to know whether the menu item should be checked"""

        if self._panel and self._panel.window.visible:
            return True

        return False

    def _toggle_panel(self):
        """Called when the menu item is clicked"""

        # Trigger refresh of the menu, to ensure the ticked state is correct
        # next time someone looks at it
        omni.kit.menu.utils.refresh_menu_items(SCENE_OPTIMIZER_MENU)

        async def show_windows():
            if self._panel and self._panel.window.visible:
                if self._panel is not None:
                    self._panel.window.visible = False
            else:
                self._panel.window.visible = True

        asyncio.ensure_future(show_windows())

    def _panel_visibility_changed_fn(self, visible):

        # Trigger menu refresh
        omni.kit.menu.utils.refresh_menu_items(SCENE_OPTIMIZER_MENU)

        """Called when visibility of the panel window changes"""
        if self._panel:
            self._panel.ui_visibility_changed(visible)
