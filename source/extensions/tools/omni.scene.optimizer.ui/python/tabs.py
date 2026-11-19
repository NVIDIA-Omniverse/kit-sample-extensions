# SPDX-FileCopyrightText: Copyright (c) 2022-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.


"""
Originally based on this library:
https://github.com/mati-nvidia/mc-widget-library

Modified to suit our purposes:
 - removed unused Checkbox stuff
 - tweaked style
 - added close-tab support
"""

import asyncio
from functools import partial
from typing import List

import omni.ui as ui

from . import style
from .utils import get_icon


class BaseTab:
    def __init__(self, name: str, closeable: bool = True):
        self.name = name
        self.closeable = closeable

    def build_fn(self):
        """Builds the contents for the tab.
        You must implement this function with the UI construction code that you want for
        your tab. This is set to be called by a ui.Frame so it must have only a single
        top-level widget.
        """
        raise NotImplementedError("Error: no build_fn")


class TabGroup:
    def __init__(self, tabs: List[BaseTab]):

        self.frame = ui.Frame(build_fn=self._build_widget)
        self._closed_fn = None

        if not tabs:
            raise ValueError("You must provide at least one BaseTab object.")

        self.tabs = tabs

    def set_closed_fn(self, fn):
        """Set a callback function for when a tab is closed"""
        self._closed_fn = fn

    def _build_widget(self, active: int = 0):
        """Main build function

        Rebuilds the main tab interface.

        @param active The tab to select and mark active.
        """

        # Reset the various state
        self.tab_containers = []
        self.tab_headers = []
        self.tab_close_buttons = []
        self.active_tab = active

        with ui.VStack(style=style.TAB_GROUP_STYLE):
            ui.Spacer(height=1)
            with ui.ZStack(height=0, name="TabGroupHeader"):
                ui.Rectangle(name="TabGroupHeader")
                with ui.VStack():
                    ui.Spacer(height=2, style={"color": ui.color(233)})
                    with ui.HStack(height=0, spacing=4):
                        for index, tab in enumerate(self.tabs):
                            tab_header = ui.ZStack(width=0, style=style.TAB_STYLE)
                            self.tab_headers.append(tab_header)
                            with tab_header:

                                rect = ui.Rectangle()
                                rect.set_mouse_pressed_fn(partial(self._tab_clicked, index))
                                rect.set_mouse_hovered_fn(partial(self._tab_hovered, index))

                                with ui.HStack():
                                    ui.Label(tab.name)
                                    if tab.closeable:
                                        stack = ui.VStack(width=22, height=22)
                                        with stack:
                                            ui.Spacer(height=2)
                                            close_button = ui.Button(
                                                image_url=get_icon("remove.svg"),
                                                image_width=16,
                                                image_height=16,
                                                mouse_pressed_fn=partial(self._delete_button_clicked, index),
                                            )
                                            close_button.visible = False
                                            self.tab_close_buttons.append(close_button)
                                    else:
                                        # Otherwise append "None" to keep indexing matching.
                                        self.tab_close_buttons.append(None)

            # Separator line underneath the tab headers
            ui.Rectangle(width=ui.Percent(98), height=1, style={"background_color": ui.color(50)})

            # Iterate back through the tabs creating the tab content and triggering
            # their build functions.
            with ui.ZStack():
                for tabIndex, tab in enumerate(self.tabs):
                    container_frame = ui.Frame(build_fn=tab.build_fn)
                    self.tab_containers.append(container_frame)

                    # Also set whether the tab is visible or not
                    if tabIndex == active:
                        self.tab_containers[tabIndex].visible = True
                        self.tab_headers[tabIndex].selected = True
                    else:
                        self.tab_containers[tabIndex].visible = False
                        self.tab_headers[tabIndex].selected = False

    async def delete_tab(self, index: int, new_index: int = None):
        """Delete the specified tab

        @param index The index of the tab to close
        @param new_index If specified, override the default behavior for choosing
        which tab to select.
        """

        if not self.tabs[index].closeable:
            return

        # Pop the tab
        tab = self.tabs.pop(index)

        # Work out which tab to select. The "next" tab is nicest as it appears under
        # the cursor after deleting. Otherwise, try to open the previous tab (eg after
        # deleting the last one).
        # Eventually we'll just default to zero. Note that this currently doesn't
        # break because Scene Optimizer enforces that you can't close the first
        # tab.
        if new_index is None:
            new_index = 0
            if index < len(self.tabs):
                new_index = index
            elif index > 1:
                new_index = index - 1

        # Rebuild UI
        with self.frame:
            self._build_widget(active=new_index)

        # Notify anything that is interested that a particular tab was closed
        if self._closed_fn:
            self._closed_fn(tab)

    def select_tab(self, index: int):
        """Select a tab

        @param index The index of the tab to select
        """

        # Already selected
        if index == self.active_tab:
            return

        for tabIndex in range(len(self.tabs)):
            if tabIndex == index:
                self.tab_containers[tabIndex].visible = True
                self.tab_headers[tabIndex].selected = True
            else:
                self.tab_containers[tabIndex].visible = False
                self.tab_headers[tabIndex].selected = False

        self.active_tab = index

        # The mouse would already be inside the tab having selected it, so
        # force the hover event to ensure it updates
        self._tab_hovered(index, True)

    def _tab_hovered(self, index: int, over: bool):
        """Triggered when the mouse hovers over a tab

        @param index The index of the tab that was hovered
        @param over Whether the mouse entered or exited
        """
        if index >= len(self.tab_close_buttons):
            return

        # Find the tab close button for this tab index.
        # For a non-closeable tab, this would be None, meaning we can
        # abort.
        button = self.tab_close_buttons[index]

        # If not a closeable button, abort
        if not button:
            return

        # If this is the active tab show the close button.
        # If it is NOT the active tab, always set it invisible.
        if index == self.active_tab:
            button.visible = over
        else:
            button.visible = False

    def _tab_clicked(self, index: int, x, y, button, modifier):
        """Called when a tab is clicked. Select the tab."""
        if button == 0:
            self.select_tab(index)
        elif button == 2:
            # Middle-mouse close. Override the default new selection behavior
            # to maintain the active tab if something else was middle-clicked.
            select_index = self.active_tab
            if index == self.active_tab:
                # But if closing the active tab just use the default behavior
                select_index = None
            elif select_index >= index:
                select_index -= 1

            asyncio.ensure_future(self.delete_tab(index, select_index))

    def _delete_button_clicked(self, index: int, x, y, button, modifier):
        if button == 0:
            asyncio.ensure_future(self.delete_tab(index))

    def destroy(self):
        self.frame.destroy()
