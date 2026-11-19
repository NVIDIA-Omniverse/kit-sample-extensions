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
import base64
import copy
import math
import sys
from functools import partial

import carb
import omni.kit.window.cursor
import omni.ui as ui
import omni.usd
from pxr import Sdf

from .edit_paths import EditPathsPanel
from .style import *
from .utils import ImageAndTextButton, get_icon, show_tooltip


class TextField(ui.ZStack):
    """Extension of the StringField to include placeholder text and clear button"""

    CLEAR_BUTTON_STYLE = {
        "Button": {
            "background_color": 0x0,
        },
        "Button:hovered": {
            "background_color": 0x0,
        },
        "Button:pressed": {
            "background_color": 0x0,
        },
        "Button.Image": {
            "color": 0xFF505050,
        },
    }

    CLEAR_BUTTON_ICON = get_icon("cancel.svg")

    def __init__(self, *args, **kwargs):
        """ """
        # TODO: Some args and kwargs should probably be passed to the ZStack constructor and removed from what is
        # passed to the StringField constructor.
        super().__init__()

        # Public interface.
        self.widget = None
        self.model = None

        # Internal handles to widgets.
        self._button = None
        self._placeholder = None

        # Internal variables.
        self._placeholder_text = ""

        def get_kwarg(kwargs, name, default_value):
            """Get a kwarg value and then delete it, so we don't pass it on"""
            val = default_value
            if name in kwargs:
                val = kwargs[name]
                del kwargs[name]
            return val

        # Config
        height = 30
        button_height = get_kwarg(kwargs, "button_height", 18)
        clear_placeholder = get_kwarg(kwargs, "clear_placeholder", "Clear the list")

        # Check for height, but do not delete - we want to pass the same value
        # on to the string field if it is specified.
        if "height" in kwargs:
            height = kwargs["height"]

        # Within this ZStack construct a string field, placeholder text overlay and clear button.
        with self:

            # Create the String field and expose the model on the instance.
            self.widget = ui.StringField(*args, **kwargs)
            self.model = self.widget.model

            # Create a label that aligns with the string field to hold the placeholder text.
            with ui.HStack(height=height):
                ui.Spacer(width=10)
                self._placeholder = ui.Label("", style={"color": 0xFF3F3D3C}, height=height)
                ui.Spacer(width=10)

            # Create a button that aligns with the right hand side of the string field to clear the string.
            with ui.HStack(height=height):
                ui.Spacer()
                self._button = ui.Button(
                    width=20,
                    image_url=TextField.CLEAR_BUTTON_ICON,
                    image_height=button_height,
                    image_width=16,
                    visible=False,
                    style=TextField.CLEAR_BUTTON_STYLE,
                )

        # Setup callback functions for the placeholder text label.

        # When the user starts editing the text field hide the placeholder.
        self.widget.model.add_begin_edit_fn(self._hide_placeholder)

        # When the user finishes editing the text field or the value is changed directly in the model display the
        # placeholder if the string field is empty.
        self.widget.model.add_end_edit_fn(self._end_edit)
        self.widget.model.add_value_changed_fn(self._update_placeholder)

        # Setup callback functions for the clear button.
        self.widget.set_mouse_hovered_fn(self._mouse_hovered)
        self.widget.set_mouse_pressed_fn(self._mouse_pressed)
        self._button.set_mouse_hovered_fn(self._clear_button_hovered)
        self._button.set_tooltip_fn(partial(show_tooltip, clear_placeholder))

        # Custom callback functions for external access
        self._end_edit_callback = None
        self._clear_button_pressed_callback = None

    def set_placeholder_text(self, value):
        """Set the string that should be displayed in the text field when the value is empty"""
        # Store the text value.
        self._placeholder_text = value
        # Then trigger an update so that the label value will be updated based on the current value of the field.
        self._update_placeholder(self.model)

    def _mouse_hovered(self, over):
        """Called when the widget gains or loses focus"""

        # Make the button visible when the mouse hovers over the string field and hidden when the hover ends.
        # This is done via an async function, as doing it immediately triggers a visual glitch where
        # the button appears to the right and then snaps to the correct location. It does add a tiny bit
        # of lag but it's less bad than the visual glitch..
        async def toggle_button():
            self._button.visible = over

        asyncio.ensure_future(toggle_button())

        # When leaving the actual text field we clear the overridden shape to properly reset it.
        if not over:
            window_cursor = omni.kit.window.cursor.get_main_window_cursor()
            window_cursor.clear_overridden_cursor_shape()

    def _clear_button_hovered(self, over):
        """Called when the cancel button gets/loses hover focus"""
        window_cursor = omni.kit.window.cursor.get_main_window_cursor()

        # If over, set to pointer. If not over, it means we're back over the main text field, so set to IBEAM.
        if over:
            window_cursor.override_cursor_shape(carb.windowing.CursorStandardShape.ARROW)
        else:
            window_cursor.override_cursor_shape(carb.windowing.CursorStandardShape.IBEAM)

    def _hide_placeholder(self, model):
        """Hide the placeholder text"""
        # Set the labels text to an empty string rather than setting visibility so that it holds its width.
        self._placeholder.text = ""

    def _end_edit(self, model):
        # Update placeholder
        self._update_placeholder(model)

        # Check for custom callback
        if self._end_edit_callback:
            self._end_edit_callback(model)

    def _update_placeholder(self, model):
        """ """
        if model.get_value_as_string():
            self._hide_placeholder(model)
        else:
            self._placeholder.text = self._placeholder_text

    def _mouse_pressed(self, posX, posY, i, b):
        """Called when the mouse is pressed inside the widget"""
        # We're inside the widget, so a quick hit-test of where the clear button
        # is being displayed (because zstack, we can't use the clicked_fn on it)
        pos = (self._button.screen_position_x, self._button.screen_position_y)
        width = self._button.computed_width
        height = self._button.computed_height

        if posX > pos[0] and posX < pos[0] + width and posY > pos[1] and posY < pos[1] + height:
            self.model.set_value("")

            # Check for callback
            if self._clear_button_pressed_callback:
                self._clear_button_pressed_callback()


class ArgumentWidget(ui.HStack):
    """
    Base class for a widget representing an Argument to an Operation.

    All Arguments have a label on the left, type specific widgets in the center and a button on the right.
    The right hand button indicates if the value matches the default, and restore the default value on press.
    """

    def __init__(self, info, label=True, indented=False):
        # Construct a Horizontal Stack to hold the argument label and value widget.
        super().__init__(height=0)

        # Store the argument info so that the full dataset it is available to all subclasses.
        self._info = info
        self._control_state_updated_fn = None
        self._state_widget = None
        self._label = label
        self._indented = indented

        self._build()

    def _build(self):

        # Within the scope of the HStack construct the label, type specific widget and control state icon.
        with self:

            # If indented, add a spacer and a line in front of the widget
            if self._indented:
                # Initial indent, line for visual look, then buffer to the main widget
                ui.Spacer(width=15)
                ui.Line(
                    width=5,
                    alignment=ui.Alignment.H_CENTER,
                    style={"border_width": 3, "color": ui.color(0.15, 0.15, 0.15)},
                )
                ui.Spacer(width=2)

            # Add the label.
            # Child widgets that are part of a group won't have a label.
            if self._label:
                # Construct the argument label using the display name.
                label = self._info.get("displayName")
                label_widget = ui.Label(
                    label, width=160, height=26, alignment=ui.Alignment.LEFT_CENTER, style=ARG_STYLE
                )

                # Add the tooltip using a function so that the tooltip style is not inherited from this widget.
                tooltip = self._info.get("description")
                if tooltip is not None:
                    label_widget.set_tooltip_fn(partial(show_tooltip, tooltip))

            # Request that the sub-class constructs any type specific widgets that it needs within an HStack.
            with ui.HStack():
                self._widget = self._construct_widget()

            # Group widgets don't have a stage button, their individual children
            # do so that the values can be reset independently.
            if not isinstance(self, JoinedArgumentWidget):
                # Create the control state button that indicate if an argument is the default value or changed.
                with ui.VStack(width=0):
                    ui.Spacer()
                    self._state_widget = ui.Image(
                        get_icon("default_value.svg"),
                        mouse_pressed_fn=self._control_state_mouse_pressed_fn,
                        width=20,
                        height=12,
                        style=CONTROL_STATE_STYLE,
                    )
                    self._state_widget.set_tooltip_fn(partial(show_tooltip, "Restore default value"))
                    ui.Spacer()

    def _construct_widget(self):  # pragma: no cover
        """Abstract function that will be called on sub classes so they can construct their type specific widgets"""
        # This function should be overridden.
        # It will be called within the context of an HStack and should return the primary widget that it constructs.
        widget = ui.Label("Example widget that should never be constructed")
        return widget

    def is_default_value(self):
        """Returns true if the current value of the argument is the same as the default value"""
        # If there is no default value for the argument then the value can never be the default.
        default_value = self._info.get("defaultValue")
        if default_value is None:
            return False
        # Return True if the current value equals the default value.
        current_value = self.get_value()
        return current_value == default_value

    def restore_default_value(self):
        """Set the current value to the default value"""
        # If there is no default value do nothing.
        default_value = self._info.get("defaultValue")
        if default_value is None:
            return
        # Set the value to the default.
        self.set_value(default_value)

    def get_child_widgets(self):  # pragma: no cover
        """Get any child widgets of this widget."""
        return list()

    def _control_state_mouse_pressed_fn(self, x, y, a, b):
        """Handle mouse press event and restore default value"""
        if self._widget.enabled:
            self.restore_default_value()

    def set_control_state_updated_fn(self, fn):
        """Set the control state callback"""
        self._control_state_updated_fn = fn

    def _update_control_state(self, model):
        """Update the control state icon to reflect the current value"""
        # We only distinguish between the value being the default or not.
        if self.is_default_value():
            self._state_widget.source_url = get_icon("default_value.svg")
        else:
            self._state_widget.source_url = get_icon("changed_value.svg")

        # Also pass on the notification to any registered callbacks
        if self._control_state_updated_fn:
            self._control_state_updated_fn(self._info["name"])

    def tidy_up(self):
        """Called in various situations when a widget should tidy up. For example,
        remove any extra windows.
        """
        pass


class BoolArgumentWidget(ArgumentWidget):
    def _construct_widget(self):
        # Create the type specific widget.
        widget = ui.CheckBox(width=20, style=BOOL_ARG_STYLE)
        widget.model.add_value_changed_fn(self._update_control_state)
        ui.Line(style=LINE_STYLE)
        return widget

    def set_value(self, value):
        # Validate the value data type.
        if not isinstance(value, bool):
            return

        # Set value in data model.
        self._widget.model.set_value(value)

    def get_value(self):
        return self._widget.model.get_value_as_bool()


class IntArgumentWidget(ArgumentWidget):
    def _construct_widget(self):
        # Create the type specific widget.
        widget = ui.IntField(style=ARG_STYLE)
        widget.model.add_value_changed_fn(self._update_control_state)

        meta = self._info["metadata"]

        if "min" in meta or "max" in meta:
            if "min" in meta:
                widget.model.set_min(int(meta["min"]))
            else:
                widget.model.set_min(-sys.maxsize - 1)

            if "max" in meta:
                widget.model.set_max(int(meta["max"]))
            else:
                widget.model.set_max(sys.maxsize)

        return widget

    def set_value(self, value):
        self._widget.model.set_value(value)

    def get_value(self):
        return self._widget.model.get_value_as_int()


class IntSliderArgumentWidget(ArgumentWidget):
    def _construct_widget(self):
        # Create the type specific widget.

        widget = ui.IntDrag(style=ARG_STYLE)
        widget.max = sys.maxsize

        meta = self._info["metadata"]

        if "min" in meta:
            widget.min = int(meta["min"])

        if "max" in meta:
            widget.max = int(meta["max"])

        widget.model.add_value_changed_fn(self._update_control_state)
        return widget

    def set_value(self, value):
        self._widget.model.set_value(value)

    def get_value(self):
        return self._widget.model.get_value_as_int()


class FloatArgumentWidget(ArgumentWidget):
    def _construct_widget(self):
        # Create the type specific widget.
        widget = ui.FloatField(style=ARG_STYLE)
        widget.model.add_value_changed_fn(self._update_control_state)

        # Check for min/max
        meta = self._info["metadata"]

        # The underlying numeric model only supports min/max if there
        # is a max that is larger than the min.
        # In order to support having only say a minimum specified, we have
        # to use inf/-inf in order to satisfy that condition for omni.ui
        # code.
        if "min" in meta or "max" in meta:
            if "min" in meta:
                widget.model.set_min(meta["min"])
            else:
                widget.model.set_min(float("-inf"))

            if "max" in meta:
                widget.model.set_max(meta["max"])
            else:
                widget.model.set_max(float("inf"))

        # For very small numbers, allow adjusting the precision to avoid displaying
        # only "0.0" even though there is an actual (small) value
        if "precision" in self._info["metadata"]:
            widget.precision = self._info["metadata"]["precision"]

        return widget

    def set_value(self, value):
        self._widget.model.set_value(value)

    def get_value(self):
        return self._widget.model.get_value_as_float()


class FloatSliderArgumentWidget(ArgumentWidget):
    def _construct_widget(self):
        # Create the type specific widget.

        widget = ui.FloatDrag(style=ARG_STYLE)
        widget.max = 5

        meta = self._info["metadata"]

        if "min" in meta:
            widget.min = meta["min"]

        if "max" in meta:
            widget.max = meta["max"]

        if "step" in meta:
            widget.step = meta["step"]

        widget.model.add_value_changed_fn(self._update_control_state)
        return widget

    def set_value(self, value):
        self._widget.model.set_value(value)

    def get_value(self):
        return self._widget.model.get_value_as_float()


class EnumArgumentWidget(ArgumentWidget):
    def _construct_widget(self):
        # Store string and int values in the order they should be displayed in the dropdown list.
        self._str_values = []
        self._int_values = []

        for enum in self._info.get("enums"):
            self._str_values.append(enum[0])
            self._int_values.append(enum[1])

        # Create the type specific widget.
        widget = ui.ComboBox(0, *self._str_values, style=ARG_STYLE)
        widget.model.get_item_value_model().add_value_changed_fn(self._update_control_state)
        return widget

    def set_value(self, value):
        # Validate the value data type and that the value has an index in the data model.
        if not isinstance(value, int) or value not in self._int_values:
            return

        # Set the data model to the index that this numeric value represents.
        index = self._int_values.index(value)
        self._widget.model.get_item_value_model().set_value(index)

    def get_value(self):
        # Get the current numeric value from the data model.
        index = self._widget.model.get_item_value_model().get_value_as_int()
        return self._int_values[index]


class TextArgumentWidget(ArgumentWidget):
    def _construct_widget(self):
        # Create the type specific widget.
        widget = ui.StringField(height=75, multiline=True, style=ARG_STYLE)
        widget.model.add_value_changed_fn(self._update_control_state)
        return widget

    def set_value(self, value):
        self._widget.model.set_value(value)

    def get_value(self):
        return self._widget.model.get_value_as_string()


class TextListArgumentWidget(ArgumentWidget):
    def _construct_widget(self):
        # Create the type specific widget.
        widget = TextField(style=ARG_STYLE)
        widget.model.add_value_changed_fn(self._update_control_state)

        placeholder = self._info["metadata"].get("placeholder")
        if placeholder is not None:
            widget.set_placeholder_text(placeholder)

        return widget

    def set_value(self, value):
        # Validate the value data type.
        if not isinstance(value, (list, tuple)):
            return

        # Sanitise items in value then join into a string for the widget.
        raw_value = ", ".join([x for x in value if x])

        # Set value in data model.
        self._widget.model.set_value(raw_value)

    def get_value(self):
        raw_value = self._widget.model.get_value_as_string()

        if not raw_value:
            return list()

        return list(map(str.strip, raw_value.split(",")))


class PrimPathArgumentWidget(ArgumentWidget):
    def _construct_widget(self):
        # Create the type specific widget.
        ImageAndTextButton(
            "Add",
            image_path=get_icon("add.svg"),
            width=70,
            height=30,
            image_width=14,
            image_height=14,
            mouse_pressed_fn=self.add_path,
            tooltip="Use selected prim",
        )

        # Create the type specific widget.
        widget = TextField(style=ARG_STYLE)
        widget.model.add_value_changed_fn(self._update_control_state)

        placeholder = self._info["metadata"].get("placeholder")
        if placeholder is not None:
            widget.set_placeholder_text(placeholder)

        # Configure drag/drop to accept prim path
        widget.set_accept_drop_fn(self.drop_accept)
        widget.set_drop_fn(self.drop)

        return widget

    def drop_accept(self, path):
        """Determine whether to accept a drag event"""

        # Only care about valid path strings
        if Sdf.Path.IsValidPathString(path):
            return True

        return False

    def drop(self, event):
        """Drop handler"""

        path = event.mime_data

        if not Sdf.Path.IsValidPathString(path):
            return

        # Get the current value and append anything that isn't already there
        value = self.get_value()
        if path != value:
            # Set new value
            self.set_value(path)

    def add_path(self, x, y, i, b):
        """ """
        # Early out if nothing is selected
        selected_paths = omni.usd.get_context().get_selection().get_selected_prim_paths()
        if not selected_paths:
            return

        # Update the value based on selection
        value = self.get_value()

        # Use the first selected prim only
        if selected_paths[0] != value:
            # Update the widget
            self.set_value(selected_paths[0])

    def set_value(self, value):
        self._widget.model.set_value(value)

    def get_value(self):
        return self._widget.model.get_value_as_string()


class CodeArgumentWidget(ArgumentWidget):
    def _construct_widget(self):
        # Create the type specific widget.
        widget = ui.StringField(height=75, multiline=True, style=ARG_STYLE)
        widget.model.add_value_changed_fn(self._update_control_state)
        return widget

    def set_value(self, value):
        # The value will be a base64 encoded ascii string.
        # Decode the value before setting the readable value in the widget.
        base64_value = value
        base64_bytes = base64_value.encode("ascii")
        readable_bytes = base64.b64decode(base64_bytes)
        readable_value = readable_bytes.decode("ascii")
        self._widget.model.set_value(readable_value)

    def get_value(self):
        # The value will be a readable string.
        # Encode to ascii bytes, bas64 encode those before decoding to an ascii string.
        readable_value = self._widget.model.get_value_as_string()
        readable_bytes = readable_value.encode("ascii")
        base64_bytes = base64.b64encode(readable_bytes)
        base64_value = base64_bytes.decode("ascii")
        return base64_value


class FloatPresetsArgumentWidget(ArgumentWidget):
    def _construct_widget(self):
        self._float_widget = None
        self._names_widget = None
        # Preset names.
        self._str_values = []
        # Preset values.
        self._float_values = []

        # Initialize the presets.
        for preset in self._info.get("floatPresets"):
            self._str_values.append(preset[0])
            self._float_values.append(preset[1])

        # The last preset is always a placeholder for custom values.
        self._str_values.append("custom")
        self._float_values.append(0.0)

        # The widget is a combo box for the names and a float field
        # for the value, side by side in a horizontal stack.
        stack = ui.HStack()
        with stack:
            self._names_widget = ui.ComboBox(0, *self._str_values, style=ARG_STYLE)
            self._names_widget.model.get_item_value_model().add_value_changed_fn(self._names_value_changed)

            self._float_widget = ui.FloatField(style=ARG_STYLE)
            self._float_widget.model.add_value_changed_fn(self._float_value_changed)

            # For very small numbers, allow adjusting the precision to avoid displaying
            # only "0.0" even though there is an actual (small) value
            if "precision" in self._info["metadata"]:
                self._float_widget.precision = self._info["metadata"]["precision"]

        return stack

    # Return the index of the preset with the given value, using the given
    # tolerance when comparing values.
    def _get_index(self, value, tol=0.000000001):
        idx = 0
        for fv in self._float_values:
            if math.isclose(fv, value, abs_tol=tol):
                return idx
            idx += 1
        return None

    # Return true if the given value is a valid presets index.
    def _is_valid_index(self, index):
        if index is None:
            return False
        return index >= 0 and index < len(self._float_values)

    # Update the names widget to display the name corresponding
    # to the given value.
    def _update_names_widget(self, value):
        # Check the current selected value.
        index = self._names_widget.model.get_item_value_model().get_value_as_int()
        if self._is_valid_index(index) and value == self._float_values[index]:
            # No need to update the name
            return index

        index = self._get_index(value)
        if index is not None:
            # The value matches an existing preset value, so update
            # to display the corresponding name.
            self._names_widget.model.get_item_value_model().set_value(index)
        else:
            # No matching preset found, so this is a custom value, which
            # is always last in the list of names.
            index = len(self._float_values) - 1
            # Record the custom value and update the index.
            self._float_values[index] = value
            self._names_widget.model.get_item_value_model().set_value(index)

        return index

    def _names_value_changed(self, model):
        index = model.get_value_as_int()
        # Update the float field to display the selected preset value.
        if self._is_valid_index(index):
            self._float_widget.model.set_value(self._float_values[index])

        super()._update_control_state(model)

    def _float_value_changed(self, model):
        value = model.get_value_as_float()
        self._update_names_widget(value)

        super()._update_control_state(model)

    def set_value(self, value):
        self._float_widget.model.set_value(value)
        self._update_names_widget(value)

    def get_value(self):
        return self._float_widget.model.get_value_as_float()


class PrimPathsArgumentWidget(ArgumentWidget):

    DELIMITER = ","

    def __init__(self, info, label=True, indented=False):

        self._widget = None
        self._edit_panel = None

        super().__init__(info, label, indented)

    def tidy_up(self):
        """If we have an edit panel open, close it."""
        if self._edit_panel is not None:
            self._edit_panel.window.visible = False

    def _construct_widget(self):
        # Create the type specific widget.
        ImageAndTextButton(
            "Add",
            image_path=get_icon("add.svg"),
            width=70,
            height=30,
            image_width=14,
            image_height=14,
            mouse_pressed_fn=self.add_paths,
            tooltip="Add selected prims to the list",
        )

        widget = TextField(style=ARG_STYLE)
        widget.model.add_value_changed_fn(self._update_control_state)

        placeholder = self._info["metadata"].get("placeholder")
        if placeholder is not None:
            widget.set_placeholder_text(placeholder)

        ui.Button(
            width=20,
            image_url=get_icon("pencil.svg"),
            image_width=24,
            image_height=18,
            clicked_fn=partial(self.edit_paths),
            tooltip_fn=partial(show_tooltip, "Edit the list of prims"),
            style={
                "Button.Image": {
                    "alignment": ui.Alignment.CENTER,
                }
            },
        )

        # Configure drag/drop to accept prim paths
        widget.set_accept_drop_fn(self.drop_accept)
        widget.set_drop_fn(self.drop)

        return widget

    def drop_accept(self, path):
        """Determine whether to accept a drag event"""

        # Only care about valid path strings
        if Sdf.Path.IsValidPathString(path):
            return True

        return False

    def drop(self, event):
        """Drop handler"""

        path = event.mime_data

        if not Sdf.Path.IsValidPathString(path):
            return

        # Valid path, consider adding it
        paths = [path]

        # Dragging from the stage outliner only includes the item that was dragged, but
        # we can use the selection to grab all of paths
        selected_paths = omni.usd.get_context().get_selection().get_selected_prim_paths()
        if path in selected_paths:
            paths = selected_paths

        # Get the current value and append anything that isn't already there
        value = self.get_value()
        for path in paths:
            if path not in value:
                value.append(path)

        # Set new value
        self.set_value(value)

    def set_value(self, value):
        # Validate the value data type.
        if not isinstance(value, (list, tuple)):
            return

        # Sanitise items in value then join into a string for the widget.
        raw_value = self.DELIMITER.join([x for x in value if x])

        # Set value in data model.
        self._widget.model.set_value(raw_value)

    def get_value(self):
        raw_value = self._widget.model.get_value_as_string()
        return [x.strip() for x in raw_value.split(self.DELIMITER) if x]

    def add_paths(self, x, y, i, b):
        """ """
        # Early out if nothing is selected
        selected_paths = omni.usd.get_context().get_selection().get_selected_prim_paths()
        if not selected_paths:
            return

        # Update the value based on selection
        value = self.get_value()
        for selected_path in selected_paths:
            if selected_path not in value:
                value.append(selected_path)

        # Update the widget
        self.set_value(value)

    def edit_paths(self):
        """Show the Edit Paths panel"""
        if self._edit_panel is None:
            self._edit_panel = EditPathsPanel(self.get_value(), accept_fn=self.update_paths)
            self._edit_panel.set_visibility_changed_fn(self.edit_paths_closed)

    def edit_paths_closed(self, closed):
        """Called when the edit paths panel visibility is toggled"""
        # Delete and clear the reference.
        del self._edit_panel
        self._edit_panel = None

    def update_paths(self, paths):
        """Called if the user clicks "Ok" in the edit paths panel"""
        self.set_value(paths)


class JoinedArgumentWidget(ArgumentWidget):
    def __init__(self, info, arguments, indented=False):

        self._arguments = arguments
        self._widgets = {}
        super().__init__(info, indented=indented)

    def _construct_widget(self):
        """Construct widget"""

        # Create a new stack. Append all child widgets to it, then
        # return the stack as the widget.
        stack = ui.HStack()
        with stack:
            for info in self._arguments:
                widget = construct_argument_widget(info, False)
                self._widgets[info["name"]] = widget

        return stack

    def set_value(self, value):  # pragma: no cover
        """Group widgets don't have a value"""
        pass

    def get_value(self):  # pragma: no cover
        """Group widgets don't have a value"""
        return None

    def _update_control_state(self, model):  # pragma: no cover
        """Group widgets don't have a control state"""
        pass

    def get_child_widgets(self):
        """Return the widgets that make up this group"""
        return self._widgets


class GroupedArgumentWidget(ArgumentWidget):

    def __init__(self, info, arguments):

        self._arguments = arguments
        self._widgets = {}
        super().__init__(info, label=False)

    def _build(self):
        with self:
            # Request that the sub-class constructs any type specific widgets that it needs within an HStack.
            with ui.HStack():
                self._widget = self._construct_widget()

    def _construct_widget(self):
        """Construct widget"""

        # Create a new stack. Append all child widgets to it, then
        # return the stack as the widget.
        stack = ui.VStack()
        with stack:
            for info in self._arguments:
                widget = construct_argument_widget(info, indented=True)

                # May be a joined argument
                if isinstance(info, list):
                    for i in info:
                        self._widgets[i["name"]] = widget
                else:
                    self._widgets[info["name"]] = widget

        return stack

    def set_value(self, value):  # pragma: no cover
        """Group widgets don't have a value"""
        pass

    def get_value(self):  # pragma: no cover
        """Group widgets don't have a value"""
        return None

    def _update_control_state(self, model):  # pragma: no cover
        """Group widgets don't have a control state"""
        pass

    def get_child_widgets(self):
        """Return the widgets that make up this group"""
        return self._widgets


class AttributeListArgumentWidget(ArgumentWidget):
    """
    An ArgumentWidget that allows building a list of attributes/namespaces
    in a table like widget.
    """

    def _construct_widget(self):
        """Construct the widget"""

        # Overall core widget is a frame we can rebuild
        self._widget = ui.Frame()
        self._widget.set_build_fn(self._build_widget)

        # Current values
        self._attributes = list()
        self._attribute_fields = list()

        self._placeholder = self._info["metadata"].get("placeholder")

        return self._widget

    def _build_widget(self):
        """(Re)build the main widget"""

        self._attribute_fields.clear()

        with ui.VStack(spacing=0):

            # Small spacer prevents visual jitter when attribute fields are added.
            if len(self._attributes):
                ui.Spacer(height=4)

            # Add text fields for each attribute
            for index, attribute in enumerate(self._attributes):

                style = ATTRIBUTE_STYLE
                kwargs = dict()

                # IsValidNamespacedIdentifier is the best function we have to check
                # if an attribute is valid. However, it doesn't allow a trailing
                # ":" which we support for namespaces. Do a simple removesuffix to
                # remove a single trailing one and then check against the remaining
                # string.
                if not Sdf.Path.IsValidNamespacedIdentifier(attribute.removesuffix(":")):
                    style = copy.deepcopy(ATTRIBUTE_STYLE)
                    style[""]["color"] = ui.color(205, 0, 0)
                    kwargs["tooltip"] = "Invalid attribute/namespace"

                kwargs["style"] = style
                kwargs["clear_placeholder"] = "Remove"
                kwargs["height"] = 14
                kwargs["button_height"] = 10

                text_field = TextField(**kwargs)
                text_field.widget.model.set_value(attribute)
                text_field._end_edit_callback = partial(self._end_edit, index)
                text_field._clear_button_pressed_callback = partial(self._clear_clicked, index)

                self._attribute_fields.append(text_field)

            # Always add the "new entry" text field at the bottom
            self._text_field_new = TextField(style=ARG_STYLE, clear_placeholder="Cancel")
            self._text_field_new._end_edit_callback = self._end_edit_new

            if self._placeholder:
                self._text_field_new.set_placeholder_text(self._placeholder)

        # Update state
        self._update_control_state(None)

    def _clear_clicked(self, index):
        """When the TextField clear button is clicked, delete the entry"""
        del self._attributes[index]
        self._widget.rebuild()

    def _end_edit(self, index, model):
        """Editing of an existing item ended"""

        # If there is no value left, then delete this entry
        # Otherwise update our record of it
        value = model.get_value_as_string()
        if not value:
            del self._attributes[index]
        else:
            self._attributes[index] = value

        # Regardless, rebuild, which will also update control state.
        self._widget.rebuild()

    def _end_edit_new(self, model):
        """Editing of the "new entry" field finished"""

        # If there is a non-empty value, add it to the list
        value = model.get_value_as_string()
        if value:

            # Don't add duplicates, but we will rebuild regardless.
            # This means the new entry field is cleared and life
            # goes on.
            if value not in self._attributes:
                self._attributes.append(value)

            self._widget.rebuild()

            # After adding and rebuilding, focus on the new entry
            # for conveniently adding more.
            asyncio.ensure_future(self.focus_text_field())

    async def focus_text_field(self):
        """Focus the keyboard on the "new entry" text field"""

        # This is awaited - we need to ensure a tick has occurred
        # so that the rebuild took place. Otherwise, text_field is
        # out of date and we will focus on the wrong thing.
        await omni.kit.app.get_app().next_update_async()
        self._text_field_new.widget.focus_keyboard()

    def set_value(self, value):
        """Set the attributes"""

        # This can be passed in directly from metadata so make sure
        # we take a copy, otherwise we're potentially editing the
        # original "default value" metadata.
        self._attributes = value.copy()

        # Update UI
        self._widget.rebuild()

    def get_value(self):
        """Get the current values"""
        return self._attributes


def construct_argument_widget(info, label=True, group=False, indented=False):
    """Factory function for constructing the appropriate ArgumentWidget subclass based on the data defined type"""

    # Grouped widgets
    if group:
        _info = {
            "displayName": "",
            "description": "",
        }

        widget = GroupedArgumentWidget(_info, info)
        return widget

    # Joined widgets (multiple widgets on same line)
    elif isinstance(info, list):
        # Use "joinNext" / "joinNextDescription" to construct
        # the group widget. The rest of the keys don't matter.
        _info = {
            "displayName": info[0]["metadata"]["joinNext"],
            "description": info[0]["metadata"]["joinNextDescription"],
        }

        widget = JoinedArgumentWidget(_info, info, indented)
        return widget

    # Get the UI type from the given argument info.
    ui_type = info.get("displayType")

    # Construct the appropriate argument widget.
    widget = None
    if ui_type == "bool":
        widget = BoolArgumentWidget(info, label, indented)
    elif ui_type == "int":
        widget = IntArgumentWidget(info, label, indented)
    elif ui_type == "intSlider":
        widget = IntSliderArgumentWidget(info, label, indented)
    elif ui_type == "float":
        widget = FloatArgumentWidget(info, label, indented)
    elif ui_type == "floatSlider":
        widget = FloatSliderArgumentWidget(info, label, indented)
    elif ui_type == "enum":
        widget = EnumArgumentWidget(info, label, indented)
    elif ui_type == "attributeList":
        widget = AttributeListArgumentWidget(info, label, indented)
    elif ui_type == "text":
        widget = TextArgumentWidget(info, label, indented)
    elif ui_type == "textList":
        widget = TextListArgumentWidget(info, label, indented)
    elif ui_type == "primPath":
        widget = PrimPathArgumentWidget(info, label, indented)
    elif ui_type == "primPaths":
        widget = PrimPathsArgumentWidget(info, label, indented)
    elif ui_type == "code":
        widget = CodeArgumentWidget(info, label, indented)
    elif ui_type == "floatPresets":
        widget = FloatPresetsArgumentWidget(info, label, indented)

    # Early out if a widget could not be constructed because the UI type was not defined or not supported.
    if widget is None:
        return None

    # Set the value of the argument to the default value if one is specified in the data.
    default_value = info.get("defaultValue")
    if default_value is not None:
        widget.set_value(default_value)

    # Set the visibility of the widget if the argument is meant to be hidden.
    # Hiding the widget ensures that the argument value is defined and passed to the command but cannot
    # be seen or edited by the user. The argument will also be stored in the JSON document.
    arg_hidden = info.get("hidden", False)
    if arg_hidden:
        widget.visible = False

    # Return the newly constructed widget.
    return widget
