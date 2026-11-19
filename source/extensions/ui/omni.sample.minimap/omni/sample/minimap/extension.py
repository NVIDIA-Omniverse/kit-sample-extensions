# SPDX-FileCopyrightText: Copyright (c) 2024 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

"""
Minimap Extension for Omniverse Kit.

This extension provides a minimap window that can be docked in the Omniverse Kit interface.
It allows users to visualize and navigate through render products in a miniature view.
"""

__all__ = ["MinimapExt"]

import logging
import os

import carb
import carb.eventdispatcher
import omni.ext
import omni.kit.app
import omni.ui as ui
import omni.usd
from omni.kit.menu.utils import MenuHelperExtension, MenuItemDescription

from . import constants as c
from .settings import S_PATH
from .waypoints import WaypointsLayer
from .window import MinimapWindow

logger = logging.getLogger(__name__)


class MinimapExt(omni.ext.IExt, MenuHelperExtension):
    """
    Main extension class for Minimap.

    Handles the creation and management of the minimap window, including:
    - Window visibility and docking
    - Menu integration
    - Stage event handling

    Attributes:
        WINDOW_NAME (str): Display name for the minimap window
        MENU_GROUP (str): Menu group where the minimap toggle appears
    """

    WINDOW_NAME = "Minimap"
    MENU_GROUP = "Window"

    def on_startup(self, ext_id):
        """
        Initialize the extension during startup.

        Args:
            ext_id: Extension identifier used to query additional information
        """
        # Retrieve the extension name for logging and event naming
        ext_name = omni.ext.get_extension_name(ext_id)

        # Retrieve the extension path for resource access (e.g., icons)
        ext_path = omni.kit.app.get_app().get_extension_manager().get_extension_path(ext_id)
        c.ICON_PATH = os.path.join(ext_path, "icons")

        # Initialize instance variables
        self._window = None
        self._menu_entry = None
        self._waypoints = WaypointsLayer()
        self._settings = carb.settings.get_settings()
        self._open = self._settings.get(S_PATH.OPEN_ON_STARTUP)

        # Register a function to toggle the minimap window in the workspace
        ui.Workspace.set_show_window_fn(MinimapExt.WINDOW_NAME, self.toggle_window)

        # Create a menu item for toggling the minimap window from the UI menu
        self._menu = [
            MenuItemDescription(
                name=MinimapExt.WINDOW_NAME,
                ticked=self._open,
                ticked_fn=self._is_visible,
                onclick_fn=self._menu_toggle_window,
            )
        ]

        # Register the menu item in the specified menu group
        try:
            self.menu_startup(MinimapExt.WINDOW_NAME, MinimapExt.WINDOW_NAME, MinimapExt.MENU_GROUP)
        except Exception as e:
            logger.warning(f"Failed to register menu item: {e}")

        # Subscribe to the application ready event to ensure proper window docking
        self._app_ready_sub = carb.eventdispatcher.get_eventdispatcher().observe_event(
            event_name=omni.kit.app.GLOBAL_EVENT_APP_READY,
            on_event=self._app_started,
            observer_name=f"{ext_name} app start trigger",
        )

        # Subscribe to stage OPENED event to handle USD stage changes
        self._stage_event_sub = carb.eventdispatcher.get_eventdispatcher().observe_event(
            event_name=omni.usd.get_context().stage_event_name(omni.usd.StageEventType.OPENED),
            on_event=self._on_stage_opened,
            observer_name=f"{ext_name} stage event",
        )

        # Open the minimap window on startup if stage exists
        if omni.usd.get_context().get_stage():
            self.toggle_window(self._open, startup=True)

    def _app_started(self, payload):
        """
        Callback executed when the UI finishes building.
        Ensures proper window docking on application startup.

        Args:
            payload: Event payload from app ready event
        """
        # Only open window if there's a valid stage, or if open_on_startup is enabled
        # This prevents creating implicit dirty states when app starts with no stage
        stage = omni.usd.get_context().get_stage()
        if stage or self._open:
            self.toggle_window(self._open, True)

    def _is_visible(self) -> bool:
        """
        Check if the minimap window is currently visible.

        Returns:
            bool: True if window exists and is visible, False otherwise
        """
        window = ui.Workspace.get_window(MinimapExt.WINDOW_NAME)
        if window is None:
            return False
        visible = window.visible
        if self._open != visible:
            self._open = visible
        return visible

    def _menu_toggle_window(self):
        """Toggle the minimap window visibility through menu interaction."""
        self.toggle_window(False if self._is_visible() else True)

    def _visibility_changed_fn(self, visible):
        """
        Handle window visibility changes and update preferences.

        Args:
            visible (bool): New visibility state
        """
        self._open = visible
        # Refresh menu item checked state (via self._is_visible)
        self.menu_refresh()
        # Update the setting to remember window visibility on app start
        carb.settings.get_settings().set(S_PATH.OPEN_ON_STARTUP, visible)

    def toggle_window(self, toggled: bool, startup=False):
        """
        Toggle the minimap window visibility.

        Args:
            toggled (bool): Desired visibility state
            startup (bool): Whether this is being called during application startup
        """
        # If window already initialized, just toggle visibility
        if self._window:
            self._window.set_visible(toggled)
            self._window.set_visibility_changed_fn(self._visibility_changed_fn)
        else:
            # Create the window if it doesn't exist
            self._window = MinimapWindow(MinimapExt.WINDOW_NAME)
            self._window.dockPreference = ui.DockPreference.RIGHT_BOTTOM
            self._window.set_visibility_changed_fn(self._visibility_changed_fn)
            # Determine where the window docks when creating
            self._window.dock_order = 1
            dock_policy = ui.DockPolicy.CURRENT_WINDOW_IS_ACTIVE if startup else ui.DockPolicy.DO_NOTHING
            self._window.deferred_dock_in("Property", dock_policy)
            # Save setting to remember window visibility on app start
            if not startup:
                self._settings.set(S_PATH.OPEN_ON_STARTUP, toggled)
        # Update menu item checked state
        self.menu_refresh()

    def _on_stage_opened(self, e=None):
        """Rebuild the minimap UI when a new stage is opened."""
        if self._window and self._window.visible:
            self._window.rebuild_ui()

    def on_shutdown(self):
        """Clean up resources when the extension is shutting down."""
        # Clean up subscriptions
        self._app_ready_sub = None
        self._stage_event_sub = None

        # Clean up menu and workspace
        try:
            self.menu_shutdown()
        except Exception as e:
            logger.warning(f"Error during menu shutdown: {e}")

        try:
            ui.Workspace.set_show_window_fn(MinimapExt.WINDOW_NAME, None)
        except Exception as e:
            logger.warning(f"Error clearing workspace window function: {e}")

        # Clean up waypoints layer
        if self._waypoints:
            try:
                self._waypoints.destroy()
            except Exception as e:
                logger.warning(f"Error destroying waypoints: {e}")
            self._waypoints = None

        # Clean up window
        if self._window:
            try:
                self._window.destroy()
            except Exception as e:
                logger.warning(f"Error destroying window: {e}")
            self._window = None

        # Final cleanup
        self._settings = None
