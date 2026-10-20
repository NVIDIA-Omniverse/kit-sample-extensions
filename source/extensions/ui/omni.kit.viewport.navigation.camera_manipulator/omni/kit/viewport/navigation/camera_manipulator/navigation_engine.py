import asyncio
import time
from enum import IntEnum

import carb
import carb.input
import carb.windowing
import omni.appwindow
import omni.kit.app
import omni.kit.imgui_renderer
import omni.kit.viewport.utility as vp_util
import omni.kit.window.cursor
import omni.usd
from carb.eventdispatcher import get_eventdispatcher
from omni import ui
from omni.kit.viewport.navigation.core import NAVIGATION_TOOL_OPERATION_ACTIVE
from pxr import Usd

from .common import *
from .orbit_target import OrbitTarget
from .utils import get_icon_path, navigation_frame

CURRENT_TOOL_SETTING = "/app/viewport/currentTool"


class OpSettings:
    MODE_SETTING = [
        "/app/transform/operation",
        # "/persistent/app/viewport/pickingMode",
        # "/app/transform/moveMode",
        # "/app/transform/rotateMode",
        # "/app/viewport/snapEnabled",
    ]

    def __init__(self):
        self._subscrptions = {}
        self.handle = carb.settings.get_settings()

    def subscribe_change(self, on_changed: callable):
        for setting_path in OpSettings.MODE_SETTING:
            sub = self.handle.subscribe_to_node_change_events(setting_path, on_changed)
            if sub:
                self._subscrptions[setting_path] = sub

    def remove_subscrition(self):
        for setting_path in self._subscrptions:
            sub = self._subscrptions[setting_path]
            self.handle.unsubscribe_to_change_events(sub)
        self._subscrptions = {}


class NavigationEngine:
    NAVIGATION_NAMES = ["dolly", "pan", "look", "orbit", "frame", "none"]

    @classmethod
    def get_name_list(cls):
        return cls.NAVIGATION_NAMES[:-1]

    def __init__(self, button_manager: "ButtonManager"):
        self._settings = carb.settings.get_settings()
        self._button_manager = button_manager

        self._current_navigation_name = ""
        app_window = omni.appwindow.get_default_app_window()
        self._key_board = app_window.get_keyboard()

        self._cursor = omni.kit.window.cursor.get_main_window_cursor()
        self._imgui_renderer = omni.kit.imgui_renderer.acquire_imgui_renderer_interface()

        self._op_setting = OpSettings()
        self._op_setting.subscribe_change(self._on_operation_changed)

        self._input = carb.input.acquire_input_interface()
        self._input_sub_id = None
        self.subscribe_input()
        self._active_operation_setting_sub = omni.kit.app.SettingChangeSubscription(
            NAVIGATION_TOOL_OPERATION_ACTIVE, lambda *_: self._on_operation_active_changed()
        )
        self._app_ready_sub = get_eventdispatcher().observe_event(
            event_name=omni.kit.app.GLOBAL_EVENT_APP_READY,
            on_event=self._on_app_ready,
            observer_name="omni.kit.viewport.navigation.camera_manipulator",
        )
        self._current_tool_setting_sub = self._settings.subscribe_to_node_change_events(
            CURRENT_TOOL_SETTING, self._on_current_tool_changed
        )
        self._orbit_target = OrbitTarget()
        self._on_operation_active_changed()
        default_operation = self._settings.get(NAVIGATION_TOOL_DEFAULT_OPERATION)
        self._orbit_auto_center = self._settings.get(NAVIGATION_TOOL_ORBIT_AUTO_CENTER)
        if default_operation:
            self._orbit_default = default_operation == "orbit"
            self.set_operation(default_operation)
        self._quit_when_key_pressed = self._settings.get(NAVIGATION_TOOL_QUIT_WHEN_KEY_PRESSED)
        self._always_on = self._settings.get(NAVIGATION_TOOL_ALWAYS_ON)

    def destroy(self):  # pragma: no cover
        self.set_operation("none")
        self._active_operation_setting_sub = None
        if self._current_tool_setting_sub is not None:
            self._settings.unsubscribe_to_change_events(self._current_tool_setting_sub)
            self._current_tool_setting_sub = None

        self.unsubscribe_input()
        self._orbit_target.destroy()
        self._cursor = None
        self._op_setting.remove_subscrition()

        if self._imgui_renderer:
            self._imgui_renderer.unregister_cursor_shape_extend(EXTEND_CURSOR_ORBIT)

        self._imgui_renderer = None
        self._app_ready_sub = None

    def _on_app_ready(self, event):
        if self._imgui_renderer:
            file_path = get_icon_path(EXTEND_CURSOR_ORBIT_FILE)
            self._imgui_renderer.register_cursor_shape_extend(EXTEND_CURSOR_ORBIT, file_path)

    def _on_operation_changed(self, item: carb.dictionary.Item, change_event_type: carb.settings.ChangeEventType):
        dict = carb.dictionary.get_dictionary()
        new_value = dict.get(item)
        # OM-53057: forbid the panel move when in move or rotate op
        if new_value in ["move", "rotate"]:
            # TODO: need find a way to reimplement this
            pass
            # self._panel.draggable = False
        else:
            pass
            # self._panel.draggable = True

    def _on_current_tool_changed(self, item, *_):
        dict = carb.dictionary.get_dictionary()
        value = dict.get(item)
        if value == "navigation":
            return
        self.set_operation("none")

    @property
    def operation(self) -> str:
        return self._current_navigation_name

    @operation.setter
    def operation(self, name: str) -> None:
        self.set_operation(name)

    def set_enabled_picking(self, enabled: bool):
        try:
            import omni.kit.viewport_legacy

            viewport_window = omni.kit.viewport_legacy.get_viewport_interface().get_viewport_window()
            if viewport_window:
                viewport_window.set_enabled_picking(enabled)
                return
        except ImportError:
            # TODO: add enable picking for vp2 here
            pass

    def set_operation(self, operation_name):
        self._settings.set(NAVIGATION_TOOL_OPERATION_ACTIVE, operation_name)

    def set_operation_internal(self, operation_name):
        self._button_manager.set_button_state(operation_name, True)
        if operation_name not in NavigationEngine.NAVIGATION_NAMES:
            self._orbit_target.enabled = False
            return
        # OM-53156: clean up teleport/pan/orbit/dolly/look switch status
        self._current_navigation_name = operation_name
        if operation_name == "none":
            if self._cursor is not None:
                self._cursor.override_cursor_shape_extend(CURSOR_DEFAULT)
                self._cursor.clear_overridden_cursor_shape()
            self.set_enabled_picking(True)
            self._orbit_target.enabled = False
        else:
            self._settings.set(CURRENT_TOOL_SETTING, "navigation")
            # OM-37884 Orbit should autoframe if there is a selection
            if operation_name == "orbit":
                select_paths = omni.usd.get_context().get_selection().get_selected_prim_paths()
                # Brian had mentioned getting some weird model jumping when using the orbit tool in view.
                # Not 100% sure if this is atually where the issue was happening, as I was unable to reproduce the issue.
                # If this doesn't clean up his issue I'll keep digging.
                # This setting is only disabled in view, by default this is True at the extension level - Bob.
                if len(select_paths) > 0 and self._settings.get_as_bool(NAVIGATION_TOOL_ORBIT_AUTO_FRAME_SELECTED):
                    # OMFP-3550: Avoid moving camera when guide prim of other tools is selected, e.g. Xform from Section tool
                    def is_hidden_in_stage_window(prim):
                        if prim.IsValid():
                            meta = prim.GetMetadata("hide_in_stage_window")
                            if meta is not None:
                                if meta is True:
                                    return True

                            return is_hidden_in_stage_window(prim.GetParent())

                        return False

                    stage = omni.usd.get_context().get_stage()
                    if stage:
                        for selected_path in select_paths:
                            selected_prim = stage.GetPrimAtPath(selected_path)

                            if not is_hidden_in_stage_window(selected_prim):
                                navigation_frame()
                                break

                elif self._settings.get(NAVIGATION_TOOL_ORBIT_AUTO_CENTER):
                    self._orbit_target.set_world_center()

                self._orbit_target.enabled = True
            else:
                self._orbit_target.enabled = False

            if operation_name != "frame":
                self.set_enabled_picking(False)
            if operation_name == "select":
                self.set_enabled_picking(True)
            # if not operation_name == "orbit" or not self._orbit_default:
            self._cursor.override_cursor_shape_extend(EXTEND_CURSOR_ORBIT)

    def subscribe_input(self):
        self._input_sub_id = self._input.subscribe_to_input_events(self._on_input_event, order=0)

    def unsubscribe_input(self):
        if self._input_sub_id:
            self._input.unsubscribe_to_input_events(self._input_sub_id)
            self._input_sub_id = None

    def _on_input_event(self, event: carb.input.InputEvent, *_):
        if event.deviceType == carb.input.DeviceType.KEYBOARD:
            return self._on_keyboard_event(event.event)
        else:
            return True

    def _on_keyboard_event(self, event, *args, **kwargs):
        if (
            event.input != carb.input.KeyboardInput.F
            and event.input != carb.input.KeyboardInput.W
            and event.input != carb.input.KeyboardInput.A
            and event.input != carb.input.KeyboardInput.S
            and event.input != carb.input.KeyboardInput.D
            and event.input != carb.input.KeyboardInput.Y
            and event.input != carb.input.KeyboardInput.H
            and event.input != carb.input.KeyboardInput.I
        ):
            if event.type == carb.input.KeyboardEventType.KEY_PRESS:
                if self._quit_when_key_pressed:
                    self.set_operation("none")

        return True

    def _on_operation_active_changed(self):
        active_operation = self._settings.get(NAVIGATION_TOOL_OPERATION_ACTIVE)
        self.set_operation_internal(active_operation)
