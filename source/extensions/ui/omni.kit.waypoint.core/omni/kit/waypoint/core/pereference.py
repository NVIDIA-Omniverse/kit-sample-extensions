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
from typing import Any, Dict, List

import carb.settings
import omni.kit.app
from omni import ui
from omni.kit.widget.settings import SettingsWidgetBuilder

from .common import SETTINGS_WAYPOINT_ROOT
from .settings import AbstractWaypointSetting, CameraSetting, PrimVisibilitySetting, RendererSetting, SunstudySetting
from .style import PEREFERENCE_WINDOW_STYLE

COLUMN_WIDTHS = [110, 50, 50, 20]

SETTINGS_PERSISTENT_ROOT = "/persistent"
SETTINGS_WAYPOINT_CAPTURE_DISABLED = SETTINGS_WAYPOINT_ROOT + "capture/disabled_settings"
SETTINGS_WAYPOINT_RECALL_DISABLED = SETTINGS_WAYPOINT_ROOT + "recall/disabled_settings"
SETTINGS_WAYPOINT_OMIT_PRIM_VISIBILITY = SETTINGS_WAYPOINT_ROOT + "omit_prim_visibility_feature"


class WaypointPereference(SettingsWidgetBuilder):
    @classmethod
    def get_capture_disable_settings(cls):
        return cls._get_settings(SETTINGS_WAYPOINT_CAPTURE_DISABLED)

    @classmethod
    def get_recall_disable_settings(cls):
        return cls._get_settings(SETTINGS_WAYPOINT_RECALL_DISABLED)

    @classmethod
    def _restore_defaults(cls, path: str, button: ui.Widget = None) -> None:
        settings = carb.settings.get_settings()
        default_capture_disabled_settings = settings.get(SETTINGS_WAYPOINT_CAPTURE_DISABLED)
        default_recall_disabled_settings = settings.get(SETTINGS_WAYPOINT_RECALL_DISABLED)
        cls._set_setting_with_key(
            SETTINGS_WAYPOINT_CAPTURE_DISABLED, path, not (path in default_capture_disabled_settings)
        )
        cls._set_setting_with_key(
            SETTINGS_WAYPOINT_RECALL_DISABLED, path, not (path in default_recall_disabled_settings)
        )
        if button:
            button.visible = False

    @classmethod
    def _set_setting_with_key(cls, path: str, key: str, value: bool) -> None:
        values = cls._get_settings(path)
        if value:
            # Remove from disable settings
            if key in values:
                values.remove(key)

        else:
            # Add to disable settings
            if key not in values:
                values.append(key)

        carb.settings.get_settings().set(SETTINGS_PERSISTENT_ROOT + path, ",".join(values))

    @classmethod
    def _get_settings(cls, path: str) -> List[str]:
        if not path.startswith(SETTINGS_PERSISTENT_ROOT):
            path = SETTINGS_PERSISTENT_ROOT + path
        settings = carb.settings.get_settings()
        value = settings.get(path)
        if value is None:
            path = path[len(SETTINGS_PERSISTENT_ROOT) :]
            value = settings.get(path)
        if value is None or value == "":
            return []
        else:
            return value.split(",")


class WaypointPerefenceWindow(ui.Window):
    def __init__(self):
        flags = (
            ui.WINDOW_FLAGS_NO_TITLE_BAR
            | ui.WINDOW_FLAGS_NO_RESIZE
            # | ui.WINDOW_FLAGS_POPUP
            | ui.WINDOW_FLAGS_NO_DOCKING
            | ui.WINDOW_FLAGS_NO_CLOSE
            | ui.WINDOW_FLAGS_NO_SCROLLBAR
        )
        super().__init__("Waypoint Settings", width=0, height=0, padding_x=0, padding_y=0, flags=flags)
        self._capture_checkboxes: Dict[str, ui.CheeckBox] = {}
        self._recall_checkboxes: Dict[str, ui.ChekcBox] = {}
        self._reset_button: Dict[str, ui.Widget] = {}

        self._settings = carb.settings.get_settings()
        self._capture_setting_changed_sub = self._settings.subscribe_to_node_change_events(
            SETTINGS_PERSISTENT_ROOT + SETTINGS_WAYPOINT_CAPTURE_DISABLED, self._on_capture_setting_changed
        )
        self._recall_setting_changed_sub = self._settings.subscribe_to_node_change_events(
            SETTINGS_PERSISTENT_ROOT + SETTINGS_WAYPOINT_RECALL_DISABLED, self._on_recall_setting_changed
        )

        self.frame.set_build_fn(self._build_ui)
        self.frame.set_style(PEREFERENCE_WINDOW_STYLE)

    def destroy(self):
        self.visible = False
        super().destroy()

    @property
    def capture_disabled_settings(self) -> List[str]:
        return WaypointPereference._get_settings(SETTINGS_WAYPOINT_CAPTURE_DISABLED)

    @property
    def recall_disabled_settings(self) -> List[str]:
        return WaypointPereference._get_settings(SETTINGS_WAYPOINT_RECALL_DISABLED)

    def show(self, x: float, y: float) -> None:
        self.visible = True

        async def __update_position():
            await omni.kit.app.get_app().next_update_async()

            self.position_x = x - self.frame.computed_width
            self.position_y = y

        asyncio.ensure_future(__update_position())

    def hide(self):
        self._on_close_window()

    def _build_ui(self):
        waypoint_settings: List[AbstractWaypointSetting] = [
            CameraSetting(None),
            RendererSetting(None),
            SunstudySetting(None),
        ]
        if not self._settings.get(SETTINGS_WAYPOINT_OMIT_PRIM_VISIBILITY):  # pragma: no cover
            # Caution: OMFP-3172 visibility handling is extremely slow
            waypoint_settings.append(PrimVisibilitySetting(None))

        capture_disabled_settings = self.capture_disabled_settings
        recall_disabled_settings = self.recall_disabled_settings
        default_capture_disabled_settings = self._settings.get(SETTINGS_WAYPOINT_CAPTURE_DISABLED)
        default_recall_disabled_settings = self._settings.get(SETTINGS_WAYPOINT_RECALL_DISABLED)
        with self.frame:
            with ui.VStack(width=0):
                self._build_title()
                ui.Spacer(height=5)
                with ui.HStack():
                    ui.Spacer(width=10)
                    with ui.VStack(spacing=5):
                        with ui.HStack(spacing=20):
                            ui.Spacer(width=COLUMN_WIDTHS[0])
                            ui.Label("Capture", width=COLUMN_WIDTHS[1], alignment=ui.Alignment.CENTER, name="key")
                            ui.Label("Recall", width=COLUMN_WIDTHS[2], alignment=ui.Alignment.CENTER, name="key")
                            ui.Spacer(width=COLUMN_WIDTHS[3])
                        for setting in waypoint_settings:
                            name = setting.get_name()
                            capture_enabled = not (name in capture_disabled_settings)
                            recalled_enabled = not (name in recall_disabled_settings)
                            default_capture_enabled = not (name in default_capture_disabled_settings)
                            default_recalled_enabled = not (name in default_recall_disabled_settings)

                            with ui.HStack(spacing=20):
                                ui.Label(name, width=COLUMN_WIDTHS[0], alignment=ui.Alignment.LEFT, name="key")
                                with ui.HStack(width=COLUMN_WIDTHS[1]):
                                    ui.Spacer()
                                    self._capture_checkboxes[name] = ui.CheckBox(name=name + " Capture Checkbox")
                                    ui.Spacer()
                                with ui.HStack(width=COLUMN_WIDTHS[2]):
                                    ui.Spacer()
                                    self._recall_checkboxes[name] = ui.CheckBox(name=name + " Recall Checkbox")
                                    ui.Spacer()
                                with ui.HStack(width=COLUMN_WIDTHS[3], spacing=10):
                                    # ui.Line()
                                    self._reset_button[name] = WaypointPereference._build_reset_button(name)

                            if name == CameraSetting(None).get_name():
                                # Camera should be minimum required for waypoint
                                self._capture_checkboxes[name].enabled = False
                            self._capture_checkboxes[name].model.set_value(capture_enabled)
                            self._recall_checkboxes[name].model.set_value(recalled_enabled)
                            self._capture_checkboxes[name].model.add_value_changed_fn(
                                lambda model, key=name: self._update_setting(
                                    SETTINGS_WAYPOINT_CAPTURE_DISABLED, key, model.get_value_as_bool()
                                )
                            )
                            self._recall_checkboxes[name].model.add_value_changed_fn(
                                lambda model, key=name: self._update_setting(
                                    SETTINGS_WAYPOINT_RECALL_DISABLED, key, model.get_value_as_bool()
                                )
                            )

                            self._reset_button[name].visible = (capture_enabled != default_capture_enabled) or (
                                recalled_enabled != default_recalled_enabled
                            )
                    ui.Spacer(width=10)
                ui.Spacer(height=5)

    def _build_title(self):
        # Same as tear-off menubar
        with ui.ZStack(height=14):
            ui.Rectangle(style_type_name_override="Menu.Title")
            with ui.HStack():
                ui.Spacer(width=14)
                ui.Line(style_type_name_override="Menu.Title.Line")
                with ui.Frame(width=14):
                    ui.Image(
                        name="close_window",
                        style_type_name_override="Menu.Item.CloseMark",
                        mouse_pressed_fn=lambda x, y, b, a: self._on_close_window(),
                    )

    def _on_close_window(self):
        self.visible = False

        from .extension import get_instance

        ext = get_instance()
        if ext:
            ext._reset_current_tool()

    def _update_setting(self, setting_path: str, key: str, value: bool) -> None:
        WaypointPereference._set_setting_with_key(setting_path, key, value)
        settings = carb.settings.get_settings()
        default_capture_disabled_settings = settings.get(SETTINGS_WAYPOINT_CAPTURE_DISABLED)
        default_recall_disabled_settings = settings.get(SETTINGS_WAYPOINT_RECALL_DISABLED)
        capture_changed = (key in default_capture_disabled_settings) != (key in self.capture_disabled_settings)
        recall_changed = (key in default_recall_disabled_settings) != (key in self.recall_disabled_settings)
        self._reset_button[key].visible = capture_changed or recall_changed

    def _on_capture_setting_changed(self, item, event_type) -> None:
        capture_disable_settings = self.capture_disabled_settings
        for key in self._capture_checkboxes:
            if key in capture_disable_settings:
                if self._capture_checkboxes[key].model.get_value_as_bool():
                    self._capture_checkboxes[key].model.set_value(False)
            else:
                if not self._capture_checkboxes[key].model.get_value_as_bool():
                    self._capture_checkboxes[key].model.set_value(True)

    def _on_recall_setting_changed(self, item, event_type) -> None:
        recall_disable_settings = self.recall_disabled_settings
        for key in self._recall_checkboxes:
            if key in recall_disable_settings:
                if self._recall_checkboxes[key].model.get_value_as_bool():
                    self._recall_checkboxes[key].model.set_value(False)
            else:
                if not self._recall_checkboxes[key].model.get_value_as_bool():
                    self._recall_checkboxes[key].model.set_value(True)
