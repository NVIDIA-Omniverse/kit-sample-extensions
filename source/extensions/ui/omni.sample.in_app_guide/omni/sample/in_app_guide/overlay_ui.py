# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

"""Overlay window implementation for the In-App Guide.

This module provides an overlay window that covers the entire application and
highlights specific UI elements while blocking mouse input to the underlying UI.
The overlay works in conjunction with the step UI to visually guide users.
"""

import asyncio
from typing import Optional

import carb
import omni.appwindow
import omni.kit.app
import omni.ui as ui
from omni.ui_query import OmniUIQuery

from . import style
from .model import GuideStep


class OverlayWindow(ui.Window):
    """Window that provides an overlay for highlighting UI elements.

    This window covers the entire application and can highlight specific UI elements
    while blocking mouse input to the underlying UI.
    """

    def __init__(self, name: str, step_ui_window_name: str):
        """Initialize the overlay window.

        Args:
            name: Name of the window.
            step_ui_window_name: Name of the associated guide step window.
        """
        super().__init__(
            name,
            dockPreference=ui.DockPreference.DISABLED,
            flags=(
                ui.WINDOW_FLAGS_NO_COLLAPSE
                | ui.WINDOW_FLAGS_NO_RESIZE
                | ui.WINDOW_FLAGS_NO_SCROLLBAR
                | ui.WINDOW_FLAGS_NO_RESIZE
                | ui.WINDOW_FLAGS_NO_MOVE
                | ui.WINDOW_FLAGS_NO_TITLE_BAR
                | ui.WINDOW_FLAGS_NO_BACKGROUND
            ),
            auto_resize=True,
            padding_x=0,
            padding_y=0,
            position_x=0,
            position_y=0,
            width=ui.Workspace.get_main_window_width(),
            height=ui.Workspace.get_main_window_height(),
            raster_policy=ui.RasterPolicy.NEVER,  # Ensure UI is updated even if window is not in focus
        )
        self._step_ui_window_name: str = step_ui_window_name
        self._current_step: Optional[GuideStep] = None

        self.frame.set_style(style.overlay_ui)

        with self.frame:
            with ui.ZStack():
                self._mouse_blocker = ui.Rectangle(name="mouse_blocker")
                self._mouse_blocker.set_mouse_pressed_fn(self._on_mouse_handler)
                self._mouse_blocker.set_mouse_released_fn(self._on_mouse_handler)
                self._placer = ui.Placer()
                with self._placer:
                    self._highlight = ui.Rectangle(name="highlight", visible=False)
                    self._highlight.set_mouse_pressed_fn(self._on_mouse_handler)
                    self._highlight.set_mouse_released_fn(self._on_mouse_handler)

        # Register handler for when the application window is resized
        event_dispatcher = carb.eventdispatcher.get_eventdispatcher()
        self._app_window_resize_sub = event_dispatcher.observe_event(
            observer_name="omni.sample.in_app_guide.OverlayWindow",
            event_name=omni.appwindow.GLOBAL_EVENT_WINDOW_RESIZE,
            on_event=self._on_app_window_resized,
        )

        # Update UI based on model
        asyncio.ensure_future(self._update_ui())

    def _on_mouse_handler(self, *args, **kwargs):
        """Handle mouse events by refocusing the guide step window.

        When a user clicks on any of the contents of this window we need to reset
        the focus back to the step_ui Window.
        """
        asyncio.ensure_future(self._set_step_ui_focus())

    async def _set_step_ui_focus(self):
        """Reset the focus back to the guide step window."""
        app = omni.kit.app.get_app()
        for _ in range(5):
            await app.next_update_async()

        # Get In-App Guide window
        window = ui.Workspace.get_window(self._step_ui_window_name)
        if window is not None:
            window.focus()

    def _on_app_window_resized(self, event):
        """Handle application window resize events.

        Args:
            event: The resize event.
        """
        # Ensure this window covers the entire application screen
        self.width = ui.Workspace.get_main_window_width()
        self.height = ui.Workspace.get_main_window_height()
        # Update UI in case target UI moved or resized.
        asyncio.ensure_future(self._update_ui())

    async def _update_ui(self):
        """Update the overlay UI based on the current step."""
        # Allow target ui to become visible
        app = omni.kit.app.get_app()
        for _ in range(5):
            await app.next_update_async()

        if self.current_step is None:
            self._highlight.visible = False
            return

        # Ensure this window is positioned at (0. 0) in the main window.
        self.position_x = 0
        self.position_y = 0

        if self.current_step.ui_type == "window":
            window = ui.Workspace.get_window(self.current_step.target_ui_path)
            if window is None:
                return
            self._placer.offset_x = window.position_x + 2
            self._placer.offset_y = window.position_y + 2
            self._highlight.visible = True
            self._highlight.width = ui.Pixel(window.width - 4)
            self._highlight.height = ui.Pixel(window.height - 4)
            return

        if self.current_step.ui_type == "widget":
            widget = OmniUIQuery.find_widget(self.current_step.target_ui_path)
            if widget is None:
                return
            self._highlight.width = ui.Pixel(widget.computed_width - 4)
            self._highlight.height = ui.Pixel(widget.computed_height - 4)
            self._highlight.visible = True
            self._placer.offset_x = widget.screen_position_x + 2
            self._placer.offset_y = widget.screen_position_y + 2

        if self.current_step.ui_type == "menu":
            menu_bar = OmniUIQuery.find_menu_item(self.current_step.target_ui_path)  # Finds the menu bar
            menu_item = None
            for widget in OmniUIQuery.find_widgets("*", [menu_bar]):
                if isinstance(widget, ui.Menu) or isinstance(widget, ui.MenuItem):
                    if widget.text == self.current_step.menu_item_text:
                        menu_item = widget
                        break
            if menu_item is None:
                self._highlight.visible = False
                return
            self._highlight.width = ui.Pixel(menu_item.computed_width - 4)
            self._highlight.height = ui.Pixel(menu_item.computed_height - 4)
            self._highlight.visible = True
            self._placer.offset_x = menu_item.screen_position_x + 2
            self._placer.offset_y = menu_item.screen_position_y + 2

    def block_mouse_inputs(self, block: bool = True):
        """Enable or disable mouse input blocking.

        Args:
            block: Whether to block mouse inputs.
        """
        if block:
            self.flags &= ~ui.WINDOW_FLAGS_NO_MOUSE_INPUTS  # Remove flag
        else:
            self.flags |= ui.WINDOW_FLAGS_NO_MOUSE_INPUTS  # Add flag

    def destroy(self):
        """Clean up the window and its resources."""
        super().destroy()
        self._app_window_resize_sub = None
        self._placer = None
        self._highlight = None
        self._current_step = None

    @property
    def current_step(self) -> Optional[GuideStep]:
        """Get the current step being highlighted."""
        return self._current_step

    @current_step.setter
    def current_step(self, value: Optional[GuideStep]):
        """Set the current step to highlight.

        Args:
            value: The step to highlight.
        """
        if self._current_step == value:
            return
        self._current_step = value
        asyncio.ensure_future(self._update_ui())
