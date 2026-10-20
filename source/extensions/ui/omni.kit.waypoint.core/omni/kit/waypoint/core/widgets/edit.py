# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
import asyncio

import omni.kit.app
from omni import ui

from ..extension import get_instance as get_waypoint_instance
from ..model import WaypointItem
from ..style import ICON_PATH


class WaypointItemEditWidget:
    """A widget for editing a WaypointItem.

    This class constructs a user interface with options to apply changes, add a new waypoint, or cancel an edit. It creates a clear and responsive layout that allows users to interact with a waypoint item based on their editing requirements. The UI components include an apply button to save changes, a new button to create a new waypoint, and a cancel button to discard modifications.

    Args:
        item (WaypointItem): The waypoint item to be edited.
        on_edit_end_fn (callable): An optional callback function that is called when the editing process ends.
    """

    def __init__(self, item: WaypointItem, on_edit_end_fn: callable = None):
        self._on_edit_end_fn = on_edit_end_fn
        self._waypoint_instance = get_waypoint_instance()

        self._build_ui(item)

    def destroy(self):
        """Destroys the widget by clearing its container and resetting its callback and waypoint instance."""
        self._container.clear()
        self._on_edit_end_fn = None
        self._waypoint_instance = None

    @property
    def visible(self) -> bool:
        """Gets the current visible state of the widget container.

        Returns:
            bool: Current visible state of the container.
        """
        return self._container.visible

    @visible.setter
    def visible(self, value: bool) -> None:
        """Sets the visible state of the widget container.

        Args:
            value (bool): New visible state of the container.
        """
        self._container.visible = value

    def _build_ui(self, item: WaypointItem) -> None:
        self._container = ui.ZStack()
        with self._container:
            ui.Rectangle(style_type_name_override="GridView.Edit.Frame")
            with ui.HStack():
                ui.Spacer()
                with ui.VStack(width=18):
                    ui.Spacer(height=5)
                    ui.Image(f"{ICON_PATH}/unlock_dark.svg", width=12, height=12)
                ui.Spacer(width=1)

            with ui.VStack():
                ui.Spacer(height=18)
                with ui.HStack():
                    # It is strange here that clicked_fn cannot be triggered if background image has drag function
                    # Has to use mouse_pressed_fn instead
                    self._apply_button = ui.Button(
                        "Apply",
                        width=ui.Percent(33),
                        name="apply",
                        mouse_pressed_fn=lambda x, y, btn, a, item=item: self._edit_save(btn, item),
                        mouse_hovered_fn=lambda hovered, item=item: self._on_edit_hovered(hovered, item),
                        style_type_name_override="GridView.Edit.Button",
                    )
                    self._new_button = ui.Button(
                        "Add New",
                        width=ui.Percent(33),
                        name="new",
                        mouse_pressed_fn=lambda x, y, btn, a, item=item: self._edit_new(btn, item),
                        mouse_hovered_fn=lambda hovered, item=item: self._on_edit_hovered(hovered, item),
                        style_type_name_override="GridView.Edit.Button",
                    )
                    self._cancel_button = ui.Button(
                        "Cancel",
                        width=ui.Percent(33),
                        name="cancel",
                        mouse_pressed_fn=lambda x, y, btn, a, item=item: self._edit_cancel(btn, item),
                        mouse_hovered_fn=lambda hovered, item=item: self._on_edit_hovered(hovered, item),
                        style_type_name_override="GridView.Edit.Button",
                    )

                ui.Spacer(height=18)

    def _edit_save(self, btn: int, item: WaypointItem):
        if btn == 0:
            self._container.visible = False

            # Here wait a frame to refresh all waypoint widgets due to waypoint changed
            async def __end_edit_async(item: WaypointItem):
                await omni.kit.app.get_app().next_update_async()
                if self._waypoint_instance:
                    self._waypoint_instance.end_edit_waypoint(item.waypoint, True)

                if callable(self._on_edit_end_fn):
                    self._on_edit_end_fn(item)

            asyncio.ensure_future(__end_edit_async(item))

    def _edit_new(self, btn: int, item: WaypointItem):
        if btn == 0:
            if self._waypoint_instance:
                self._waypoint_instance.end_edit_waypoint(item.waypoint, False, create=True)
            self._container.visible = False
            if callable(self._on_edit_end_fn):
                self._on_edit_end_fn(item)

    def _edit_cancel(self, btn: int, item: WaypointItem):
        if btn == 0:
            if self._waypoint_instance:
                self._waypoint_instance.end_edit_waypoint(item.waypoint, False)
            self._container.visible = False
            if callable(self._on_edit_end_fn):
                self._on_edit_end_fn(item)

    def _on_edit_hovered(self, hovered: bool, item: WaypointItem):
        # Clear selected status to show hovered style
        self._apply_button.selected = False
        self._new_button.selected = False
        self._cancel_button.selected = False
