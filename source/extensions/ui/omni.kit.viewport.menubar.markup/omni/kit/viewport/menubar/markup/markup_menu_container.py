# Copyright (c) 2021-2022, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

__all__ = ["MarkupMenuContainer"]

from typing import Optional

import carb
import carb.settings
import omni.ui as ui
from omni.kit.viewport.menubar.core import ViewportButtonItem

from .markup_window import MarkupListWindow
from .style import UI_STYLE

WINDOW_TITLE = "Markups"
LIST_WINDOW_VIS_PATH = "/exts/omni.kit.viewport.menubar.markup/list_window_visible"


class MarkupMenuContainer(ViewportButtonItem):
    """The button for markup"""

    def __init__(self):
        self._settings = carb.settings.get_settings()
        self._list_window_instance: Optional[MarkupListWindow] = None

        super().__init__(
            name="Markup",
            visible_setting_path="/exts/omni.kit.viewport.menubar.markup/visible",
            order_setting_path="/exts/omni.kit.viewport.menubar.markup/order",
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
            # if ui.Workspace check is None it will make and use MarkupListWindow()
            self._list_window_instance = ui.Workspace.get_window(WINDOW_TITLE) or MarkupListWindow()
        self._list_window_instance.visible = state

    def destroy(self):
        ui.Workspace.set_show_window_fn(WINDOW_TITLE, lambda *x: None)
        ui.Workspace.remove_window_visibility_changed_callback(self._window_vis_changed_id)
        super().destroy()
