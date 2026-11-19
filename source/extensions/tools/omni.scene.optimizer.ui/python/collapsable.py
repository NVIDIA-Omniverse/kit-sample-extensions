# SPDX-FileCopyrightText: Copyright (c) 2023-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.


from functools import partial

import omni.ui as ui

from .style import FRAME_STYLE, IMAGE_COLOR
from .utils import get_icon, show_tooltip


class CollapsibleWidget:
    """Widget that has a header and can collapse its content."""

    def __init__(self, label, build_fn, delete_fn=None, collapsed=False, draggable=True):

        # Internal config
        self._frame = None
        self._label = label
        self._build_fn = build_fn
        self._delete_fn = delete_fn
        self._draggable = draggable

        # Public state
        self.collapsed = collapsed

        # Build this widget
        self._build_widget()

    def _build_header(self, collapsed, title):
        """Build a custom header for the CollapsableFrame.

        We want to build a custom header so we can shift the collapse triangle
        in slightly. This is so we can add a button (via ZStack) over the top
        later, like an "Accessory view". That will be the drag handle to reorder.
        This is only if draggable is enabled.
        """

        # This is pretty much a poor-mans version of the C++ implementation.
        hstack = ui.HStack()
        with hstack:

            hstack.name = "header"

            if self._draggable:
                ui.Spacer(width=ui.Pixel(20))

            triangle_size = 8.0

            ui.Spacer(width=ui.Length(triangle_size))

            triangle_center = ui.VStack()
            triangle_center.width = ui.Pixel(triangle_size)

            with triangle_center:
                ui.Spacer()
                triangle = ui.Triangle(style={"background_color": 0xCCFFFFFF})
                triangle.height = ui.Pixel(triangle_size)
                triangle.alignment = ui.Alignment.RIGHT_CENTER if collapsed else ui.Alignment.CENTER_BOTTOM
                ui.Spacer()

            ui.Spacer(width=ui.Length(triangle_size))
            label = ui.Label(title)
            ui.Spacer(width=ui.Length(triangle_size))

            # Only specify a tooltip function if there is a tooltip
            if self.get_tooltip() != "":
                label.set_tooltip_fn(self._show_label_tooltip)

    def _show_label_tooltip(self):
        """Show the widget tooltip"""
        if self.get_tooltip() != "":
            show_tooltip(self.get_tooltip())

    def _build_widget(self):
        """Build the UI"""

        # Soooo... clicks will get blocked by widgets. Meaning we can't just add
        # buttons to the collapsable frame and have both the collapse and the
        # buttons (or drag) work. Throw everything in a ZStack, which means we
        # can hijack this behavior by adding our own buttons over the top.
        with ui.ZStack(width=ui.Percent(100)):

            self._frame = ui.CollapsableFrame(self._label, width=ui.Percent(100), height=0, style=FRAME_STYLE)
            self._frame.set_build_header_fn(self._build_header)
            self._frame.set_collapsed_changed_fn(self.on_collapsed_state_change)
            self._frame.collapsed = self.collapsed

            # Call the build function
            with self._frame:
                self._build_fn()

            # If draggable/deletable, add the extra required elements
            if self._draggable or self._delete_fn:

                # On top of the CollapsableFrame we can do this funky dance that summons
                # some kind of spirit, and also has the side effect of giving us a clickable
                # delete button. We also use mouse_pressed_fn rather than clicked_fn..
                with ui.HStack(width=ui.Percent(100), height=30):

                    if self._draggable:
                        # Here be dragons.
                        #
                        # Image to fake being a button. The real button is actually underneath.
                        # See add() for more info.
                        ui.Spacer(width=ui.Pixel(5))
                        with ui.VStack(width=0):
                            ui.Spacer(height=10)
                            ui.Image(
                                get_icon("drag.svg"),
                                width=20,
                                height=20,
                                style={"Image": {"padding": 0, "color": IMAGE_COLOR}},
                            )

                    if self._delete_fn:
                        ui.Spacer(width=ui.Fraction(0.7))
                        with ui.VStack(width=0):
                            ui.Spacer(height=8)
                            ui.Button(
                                image_url=get_icon("remove.svg"),
                                image_width=20,
                                image_height=20,
                                mouse_pressed_fn=partial(self._delete_fn, self),
                                style={"padding": 0},
                                tooltip_fn=partial(show_tooltip, "Remove this process"),
                            )
                        ui.Spacer(width=5)

    def on_collapsed_state_change(self, *arg):
        """Callback when the collapsed state is toggled"""
        self.collapsed = self._frame.collapsed

    def width(self):
        """Return the current computed width of this widget"""
        return self._frame.computed_width

    def height(self):
        """Return the current computed height of this widget"""
        return self._frame.computed_height

    def pos(self):
        """Return the position of this widget"""
        return (self._frame.screen_position_x, self._frame.screen_position_y)

    def get_tooltip(self):
        return ""
