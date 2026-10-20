# Copyright (c) 2021-2022, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

__all__ = ["WaypointMenuContainer"]

from typing import Optional

import carb
import carb.settings
import omni.ui as ui
from omni.kit.viewport.menubar.core import ViewportButtonItem
from omni.kit.waypoint.core.widgets.list_window import WaypointListWindow

from .style import UI_STYLE

WINDOW_TITLE = "Waypoints"
LIST_WINDOW_VIS_PATH = "/exts/omni.kit.viewport.menubar.waypoint/list_window_visible"


class WaypointMenuContainer(ViewportButtonItem):
    """The button for waypoint"""

    def __init__(self):
        self._settings = carb.settings.get_settings()
        self._list_window_instance: Optional[WaypointListWindow] = None

        super().__init__(
            name="Waypoint",
            visible_setting_path="/exts/omni.kit.viewport.menubar.waypoint/visible",
            order_setting_path="/exts/omni.kit.viewport.menubar.waypoint/order",
            onclick_fn=self._on_click,
            style=UI_STYLE,
            alignment=ui.Alignment.LEFT_TOP,
        )

        def window_vis_changed(title: str, state: bool) -> None:
            self._list_window_instance = ui.Workspace.get_window(WINDOW_TITLE)
            if self._list_window_instance and self._list_window_instance.title == title:
                self._settings.set_bool(LIST_WINDOW_VIS_PATH, state)
                self.checked = state

        ui.Workspace.set_show_window_fn(WINDOW_TITLE, self._show_window)
        self._window_vis_changed_id = ui.Workspace.set_window_visibility_changed_callback(window_vis_changed)

    def _on_click(self) -> None:
        state = not self.checked
        self._show_window(state)

    def _show_window(self, state: bool) -> None:
        if not self._list_window_instance:
            # if ui.Workspace check is None it will make and use WaypointListWindow()
            self._list_window_instance = ui.Workspace.get_window(WINDOW_TITLE) or WaypointListWindow()
        self._list_window_instance.visible = state

    def destroy(self):  # pragma: no cover
        ui.Workspace.set_show_window_fn(WINDOW_TITLE, lambda *x: None)
        ui.Workspace.remove_window_visibility_changed_callback(self._window_vis_changed_id)
        super().destroy()
