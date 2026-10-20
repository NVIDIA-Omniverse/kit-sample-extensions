# SPDX-FileCopyrightText: Copyright (c) 2022-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
__all__ = ["TimelineMinibarScene"]

import carb.dictionary
import omni.timeline
import omni.ui as ui

from .live_session import TimelineLiveSession
from .minibar import TimelineMinibar
from .style import MINIBAR_HEIGHT, MINIBAR_MAX_WIDTH, MINIBAR_MIN_WIDTH, MINIBAR_WIDTH

# this settings use for hide minibar while capturing moving
TIMELINE_DISPLAY_SETTINGS_PATH = "/app/viewport/TimelineMinibar"
MINIBAR_TOGGLE_BY_HOVER_PATH = "/exts/omni.kit.timeline.minibar/toggleByHover"
MINIBAR_VISIBLE_PATH = "/exts/omni.kit.timeline.minibar/visible"
MINIBAR_BOTTOM_SETTINGS_PATH = "/exts/omni.kit.timeline.minibar/offsetBottom"
MINIBAR_SCALE_WITH_NAVBAR = "/exts/omni.kit.timeline.minibar/scale_with_nav_bar"
TOOL_OFFSET_SETTINGS_PATH = "/app/viewport/offsets/navBottom"
MODAL_TOOL_ACTIVE_PATH = "/app/tools/modal_tool_active"

NAVBAR_WIDTH_PATH = "/exts/omni.kit.viewport.navigation.core/computed_width"


class TimelineMinibarScene:
    def __init__(self, vp_args: dict):
        self.__root = None
        self._minibar = None
        self._visible_before = None
        self._frame = None

        self._viewport_api = vp_args.get("viewport_api")
        if not self._viewport_api:
            raise RuntimeError("Cannot create timeline minibar scene without a viewport_api")

        # legacy viewport have timeline bar internal
        if hasattr(self._viewport_api, "legacy_window"):
            return

        settings = carb.settings.get_settings()
        settings.set_default_bool(TIMELINE_DISPLAY_SETTINGS_PATH, True)
        settings.set_default_bool(MINIBAR_TOGGLE_BY_HOVER_PATH, True)
        settings.set_default_bool(MINIBAR_VISIBLE_PATH, False)
        settings.set_default_int(MINIBAR_BOTTOM_SETTINGS_PATH, 30)
        settings.set_default_bool(MINIBAR_SCALE_WITH_NAVBAR, False)
        self.__register_display_setting()
        self._minibar_setting_sub = omni.kit.app.SettingChangeSubscription(
            TIMELINE_DISPLAY_SETTINGS_PATH, self._on_visible_setting_changed
        )
        self._visible_toggle_sub = omni.kit.app.SettingChangeSubscription(
            MINIBAR_VISIBLE_PATH, self._on_visible_changed
        )
        self._modal_setting_sub = omni.kit.app.SettingChangeSubscription(
            MODAL_TOOL_ACTIVE_PATH, self._on_modal_setting_changed
        )

        self._auto_scale_setting_sub = omni.kit.app.SettingChangeSubscription(
            MINIBAR_SCALE_WITH_NAVBAR, self._on_scaling_changed
        )

        auto_scale = settings.get_as_bool(MINIBAR_SCALE_WITH_NAVBAR)
        if auto_scale:
            self._toggle_auto_scale(auto_scale)

        self._live_session = TimelineLiveSession()
        self._build_window()

    def __del__(self):
        self.destroy()

    def destroy(self):  # pragma: no cover
        self._minibar_setting_sub = None
        self._visible_toggle_sub = None
        self._modal_setting_sub = None
        self._auto_scale_setting_sub = None
        self._navbar_width_sub = None
        self._viewport_api = None
        self._visible_before = None
        self._live_session = None
        self.__deregister_display_setting()
        if self._minibar:
            self._minibar.destroy()
            self._minibar = None
        if self._frame:
            self._frame.destroy()
            self._frame = None
        if self.__root:
            self.__root.clear()
            self.__root.destroy()
            self.__root = None

    def _build_window(self):
        settings = carb.settings.get_settings()
        display = settings.get_as_bool(TIMELINE_DISPLAY_SETTINGS_PATH)
        bottom_offset = settings.get_as_int(MINIBAR_BOTTOM_SETTINGS_PATH)

        self.__root = ui.Stack(ui.Direction.BOTTOM_TO_TOP, visible=display)
        with self.__root:
            ui.Spacer(height=bottom_offset)
            self._frame = ui.Frame(build_fn=self._rebuild)
            ui.Spacer()

        visible = settings.get_as_bool(MINIBAR_VISIBLE_PATH)
        if visible:
            self._push_tools(True)

    def _rebuild(self) -> None:
        with ui.HStack(height=0):
            width = MINIBAR_WIDTH
            if self._on_watched_width_changed is not None:  # auto-scaling is on
                settings = carb.settings.get_settings()
                target_width = settings.get(NAVBAR_WIDTH_PATH)
                if target_width is not None:
                    width = min(max(target_width, MINIBAR_MIN_WIDTH), MINIBAR_MAX_WIDTH)
            ui.Spacer()
            with ui.ZStack(
                height=MINIBAR_HEIGHT, width=width, mouse_hovered_fn=self._on_hovered, name="timeline_minibar_frame"
            ):
                self._minibar = TimelineMinibar(self._live_session)
            ui.Spacer()

        visible = settings.get_as_bool(MINIBAR_VISIBLE_PATH)
        self._minibar.visible = visible

    @property
    def visible(self):
        return self.__root.visible

    @visible.setter
    def visible(self, value: bool):
        if self.__root.visible == value:
            return
        self.__root.visible = value

    def _on_visible_setting_changed(self, item, event_type) -> None:
        dict = carb.dictionary.get_dictionary()
        visible = dict.get_as_bool(item)
        self.visible = visible

    def _on_visible_changed(self, item, event_type) -> None:
        dict = carb.dictionary.get_dictionary()
        visible = dict.get_as_bool(item)
        if self._minibar and self._minibar.visible != visible:
            self._minibar.visible = visible
            self._push_tools(visible)

    def _on_scaling_changed(self, item, event_type) -> None:
        dict = carb.dictionary.get_dictionary()
        auto_scale = dict.get_as_bool(item)
        self._toggle_auto_scale(auto_scale)

    def _toggle_auto_scale(self, enabled: bool) -> None:
        if enabled:
            self._navbar_width_sub = omni.kit.app.SettingChangeSubscription(
                NAVBAR_WIDTH_PATH, self._on_watched_width_changed
            )
            if self._frame:
                self._frame.rebuild()
        else:
            self._navbar_width_sub = None

    def _on_watched_width_changed(self, item, event_type) -> None:
        if self._frame:
            self._frame.rebuild()

    def _on_modal_setting_changed(self, item, event_type) -> None:
        timeline = omni.timeline.get_timeline_interface()
        settings = carb.settings.get_settings()
        if settings.get_as_bool(MODAL_TOOL_ACTIVE_PATH):
            if timeline.is_playing():
                timeline.pause()
            self._save_state(settings)
            visible = settings.get_as_bool(MINIBAR_VISIBLE_PATH)
            if visible:
                settings.set_bool(MINIBAR_VISIBLE_PATH, False)
        else:
            self._restore_state(settings)

    def _save_state(self, settings) -> None:
        self._visible_before = settings.get_as_bool(MINIBAR_VISIBLE_PATH)

    def _restore_state(self, settings) -> None:
        if self._visible_before:
            settings.set_bool(MINIBAR_VISIBLE_PATH, True)
            self._visible_before = None

    def _push_tools(self, visible):
        settings = carb.settings.get_settings()
        current_offset = settings.get(TOOL_OFFSET_SETTINGS_PATH)
        current_offset = current_offset if current_offset is not None else 0
        sign = 1 if visible else -1
        settings.set(TOOL_OFFSET_SETTINGS_PATH, current_offset + sign * MINIBAR_HEIGHT)

    def _on_hovered(self, hovered: bool):
        if self._minibar:
            settings = carb.settings.get_settings()
            show_by_hover = settings.get_as_bool(MINIBAR_TOGGLE_BY_HOVER_PATH)
            if not show_by_hover:
                return

            timeline = omni.timeline.get_timeline_interface()
            self._minibar.visible = hovered or timeline.is_playing()

    def __register_display_setting(self):  # pragma: no cover
        try:
            from omni.kit.viewport.menubar.display import get_instance as get_display_instance

            inst = get_display_instance()
            inst.register_custom_setting("Timeline", TIMELINE_DISPLAY_SETTINGS_PATH)  # type: ignore
        except ImportError:
            pass
        pass

    def __deregister_display_setting(self):  # pragma: no cover
        try:
            from omni.kit.viewport.menubar.display import get_instance as get_display_instance

            inst = get_display_instance()
            inst.deregister_custom_setting("Timeline")  # type: ignore
        except ImportError:
            pass
        pass
