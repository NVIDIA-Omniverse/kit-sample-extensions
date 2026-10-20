# SPDX-FileCopyrightText: Copyright (c) 2023-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

from typing import Sequence

from carb.eventdispatcher import get_eventdispatcher
from omni.kit.manipulator.camera import LookGesture
from omni.kit.window.cursor import get_main_window_cursor

from .teleport import TELE_ENABLED_GLOBAL_EVENT
from .utils import get_icon_path

DEFALT_CURROR = "Arrow"
EXTEND_CURSOR_TELEPORT = "Teleport"
EXTEND_CURSOR_GRAB_CLOSE = "Grab_close"
EXTEND_CURSOR_TELEPORT_FILE = "cursorTeleport.png"


def reset_cursor():
    cursor = get_main_window_cursor()
    if cursor:
        cursor.override_cursor_shape_extend(DEFALT_CURROR)
        cursor.clear_overridden_cursor_shape()


class TeleportCursor:  # pragma: no cover -- currently unused
    def __init__(self):
        try:
            import omni.appwindow
            import omni.kit.imgui_renderer

            self._imgui_renderer = omni.kit.imgui_renderer.acquire_imgui_renderer_interface()
            self._app_window = omni.appwindow.get_default_app_window()
        except Exception:
            # Currently need both of these for further API usage, which can't happen now; so clear them both out
            self._imgui_renderer, self._app_window = None, None
            return

        self._teleport_sub = get_eventdispatcher().observe_event(
            event_name=TELE_ENABLED_GLOBAL_EVENT, on_event=self._on_teleport_evt
        )
        self._cur_cursor = self._imgui_renderer.get_cursor_shape_override_extend(self._app_window)
        self._app_ready_sub = get_eventdispatcher().observe_event(
            event_name=omni.kit.app.EVENT_APP_READY,
            on_event=self._on_app_ready,
            observer_name="TeleportCursor",
        )

    def __del__(self):
        self.destroy()

    def destroy(self):
        if self._imgui_renderer:
            self._imgui_renderer.unregister_cursor_shape_extend(EXTEND_CURSOR_TELEPORT)

        self._imgui_renderer = None
        self._app_window = None
        self._teleport_sub = None
        self._app_ready_sub = None

    def _on_app_ready(self, event):
        if self._imgui_renderer:
            file_path = get_icon_path(EXTEND_CURSOR_TELEPORT_FILE)
            self._imgui_renderer.register_cursor_shape_extend(EXTEND_CURSOR_TELEPORT, file_path)

    def show_teleport_cursor(self, show: bool):
        self._set_cursor(EXTEND_CURSOR_TELEPORT if show else DEFALT_CURROR)

    def _on_teleport_evt(self, event):
        self.show_teleport_cursor(event["enabled"])

    def _set_cursor(self, cursor_name: str):
        if self._imgui_renderer and not (self._cur_cursor == cursor_name):
            self._imgui_renderer.set_cursor_shape_override_extend(self._app_window, cursor_name)
            self._cur_cursor = cursor_name
            if self._cur_cursor == DEFALT_CURROR:
                self._imgui_renderer.clear_cursor_shape_override(self._app_window)


class CursorLookGesture(LookGesture):
    def __init__(self, model, configure_model=None, name: str = None, *args, **kwargs):
        super().__init__(model, configure_model, *args, **kwargs)
        self._cursor = get_main_window_cursor()
        self._changed = False

    def destroy(self):
        self._cursor = None
        super().destroy()

    def on_changed(self, mouse: Sequence[float] = None):
        if self._cursor and not self._changed:
            self._cursor.override_cursor_shape_extend(EXTEND_CURSOR_GRAB_CLOSE)
            self._changed = True
        return super().on_changed(mouse)

    def on_ended(self):
        if self._cursor and self._changed:
            self._cursor.override_cursor_shape_extend(DEFALT_CURROR)
            self._cursor.clear_overridden_cursor_shape()
            self._changed = False
        return super().on_ended()
