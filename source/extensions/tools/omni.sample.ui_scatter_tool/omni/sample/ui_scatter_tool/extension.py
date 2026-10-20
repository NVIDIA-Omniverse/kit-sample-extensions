# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

"""
ScatterWindowExtension main entry point.

This module provides the extension class that manages the lifecycle of the Scatter Window,
including menu registration, window creation, and visibility management.
"""

import asyncio
from functools import partial

import omni.ext
import omni.kit.menu.utils
import omni.ui as ui
from omni.kit.menu.utils import MenuItemDescription

from . import commands  # Import commands to register them
from .window import ScatterWindow


class ScatterWindowExtension(omni.ext.IExt):
    """The entry point for Scatter Window"""

    WINDOW_NAME = "Scatter Window"
    MENU_PATH = f"Window/{WINDOW_NAME}"

    def on_startup(self):
        # The ability to show up the window if the system requires it. We use it
        # in QuickLayout.
        ui.Workspace.set_show_window_fn(ScatterWindowExtension.WINDOW_NAME, partial(self.show_window, None))

        # Put the new menu
        self._menu_items = [
            MenuItemDescription(
                name=ScatterWindowExtension.WINDOW_NAME,
                ticked=True,
                ticked_fn=lambda: self._window.visible if hasattr(self, "_window") and self._window else False,
                onclick_fn=lambda *args: (
                    self.show_window(None, True)
                    if not (hasattr(self, "_window") and self._window and self._window.visible)
                    else self.show_window(None, False)
                ),
            )
        ]
        omni.kit.menu.utils.add_menu_items(self._menu_items, "Window")

        # Show the window. It will call `self.show_window`
        ui.Workspace.show_window(ScatterWindowExtension.WINDOW_NAME)

    def on_shutdown(self):
        if hasattr(self, "_menu_items"):
            omni.kit.menu.utils.remove_menu_items(self._menu_items, "Window")
            self._menu_items = None
        if hasattr(self, "_window") and self._window:
            self._window.destroy()
            self._window = None

        # Deregister the function that shows the window from omni.ui
        ui.Workspace.set_show_window_fn(ScatterWindowExtension.WINDOW_NAME, None)

    def _set_menu(self, value):
        """Set the menu to create this window on and off"""
        # Refresh the menu to update the ticked state
        if hasattr(self, "_menu_items"):
            omni.kit.menu.utils.refresh_menu_items("Window")

    async def _destroy_window_async(self):
        # wait one frame, this is due to the one frame defer
        # in Window::_moveToMainOSWindow()
        await omni.kit.app.get_app().next_update_async()
        if self._window:
            self._window.destroy()
            self._window = None

    def _visibility_changed_fn(self, visible):
        # Called when the user pressed "X"
        self._set_menu(visible)
        if not visible:
            # Destroy the window, since we are creating new window
            # in show_window
            asyncio.ensure_future(self._destroy_window_async())

    def show_window(self, menu, value):
        if value:
            self._window = ScatterWindow(ScatterWindowExtension.WINDOW_NAME, width=270, height=570)
            self._window.set_visibility_changed_fn(self._visibility_changed_fn)
        elif self._window:
            self._window.visible = False
