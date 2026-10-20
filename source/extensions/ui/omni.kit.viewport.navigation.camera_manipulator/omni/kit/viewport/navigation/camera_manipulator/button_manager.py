from typing import Dict

import carb
import carb.events
from omni import ui
from omni.kit.viewport.navigation.core import (
    NAVIGATION_TOOL_OPERATION_ACTIVE,
    ViewportNavigationButton,
    ViewportNavigationTooltip,
)

from .common import *
from .icons import Icons
from .utils import navigation_frame


class ButtonManager:
    def __init__(self):
        self._settings = carb.settings.get_settings()
        self._dict = carb.dictionary.get_dictionary()
        self._tooltips_default_on = True  # self._settings.get(NAVIGATION_TOOL_TOOLTIPS_DEFAULT_ON)
        self._always_on = self._settings.get(NAVIGATION_TOOL_ALWAYS_ON)
        self._button_map: Dict[str, ViewportNavigationButton] = {}
        self._button_clicked_fn = None
        self._current_navigation_name = "orbit"

    def show_teleport(self):
        return self._show_teleport

    def destroy(self):  # pragma: no cover
        for btn in self._button_map:
            self._button_map[btn].destroy()
            self._button_map[btn] = None
        self._button_map = {}

    def add_button(self, button_name: str, button: "ViewportNavigationButtton"):
        if self._settings.get_as_bool(f"{BUTTON_VISIBLILITY_PATH}{button_name}_visible"):
            self._button_map[button_name] = button

    def on_button_clicked(self, operation_name, state):
        if self._current_navigation_name == operation_name:
            if self._always_on:
                self.set_button_state(operation_name, True)
            else:
                self.set_operation("none")
            return
        self.set_operation(operation_name)

        if operation_name == "frame":
            navigation_frame()
            self.set_operation("none")

    def set_operation(self, operation_name):
        self._settings.set(NAVIGATION_TOOL_OPERATION_ACTIVE, operation_name)
        self._current_navigation_name = operation_name

    def set_button_state(self, btn_name, state):
        if state:
            # OM-81855: the btn_name may not in button map (teleport etc.)
            # set it to current here to avoid click twice back from teleport
            self._current_navigation_name = btn_name
            # Switch other buttons off if any
            for name in self._button_map:
                button = self._button_map[name]
                if name != btn_name and button.state:
                    self._button_map[name].set_state(False)

        if btn_name in self._button_map:
            self._button_map[btn_name].set_state(state)

    def get_button(self, btn_name):
        if btn_name in self._button_map:
            return self._button_map[btn_name]

        return None

    def _build_dolly_tooltip(self):
        if not self._tooltips_default_on:
            return (0, 0)
        TOOLTIP_SIDE_SPACE = 5
        boundary = 7
        with ui.VStack():
            ui.Spacer(height=TOOLTIP_SIDE_SPACE)
            with ui.HStack(height=0):
                ui.Spacer(width=TOOLTIP_SIDE_SPACE)
                ui.Image(Icons().get("mouseTip_middle_dark"), width=25, height=25)
                ui.Image(Icons().get("add_tip_dark"), width=14, height=25)
                ui.Spacer(width=TOOLTIP_SIDE_SPACE)
                ui.Label("Scroll", alignment=ui.Alignment.CENTER, name="shortcut")
                ui.Spacer(width=TOOLTIP_SIDE_SPACE)
        return (90, 32)

    def _build_pan_tooltip(self):
        if not self._tooltips_default_on:
            return (0, 0)
        TOOLTIP_SIDE_SPACE = 5
        boundary = 7
        with ui.VStack():
            ui.Spacer(height=TOOLTIP_SIDE_SPACE)
            with ui.HStack(height=0):
                ui.Spacer(width=TOOLTIP_SIDE_SPACE)
                ui.Image(Icons().get("mouseTip_middle_dark"), width=25, height=25)
                ui.Image(Icons().get("add_tip_dark"), width=14, height=25)
                ui.Spacer(width=TOOLTIP_SIDE_SPACE)
                ui.Label("Drag", alignment=ui.Alignment.CENTER, name="shortcut")
                ui.Spacer(width=TOOLTIP_SIDE_SPACE)
        return (84, 35)

    def _build_look_tooltip(self):
        if not self._tooltips_default_on:
            return (0, 0)
        TOOLTIP_SIDE_SPACE = 5
        boundary = 7
        with ui.VStack():
            ui.Spacer(height=TOOLTIP_SIDE_SPACE)
            with ui.HStack(height=0):
                ui.Spacer(width=TOOLTIP_SIDE_SPACE)
                ui.Image(Icons().get("mouseTip_rightClick_dark"), width=25, height=25)
                ui.Image(Icons().get("add_tip_dark"), width=14, height=25)
                ui.Spacer(width=TOOLTIP_SIDE_SPACE)
                ui.Label("Drag", alignment=ui.Alignment.CENTER, name="shortcut")
                ui.Spacer(width=TOOLTIP_SIDE_SPACE)
        return (84, 32)

    def _build_orbit_tooltip(self):
        if not self._tooltips_default_on:
            return (0, 0)
        TOOLTIP_SIDE_SPACE = 5
        boundary = 7
        with ui.VStack():
            ui.Spacer(height=TOOLTIP_SIDE_SPACE)
            with ui.HStack(height=0):
                ui.Spacer(width=TOOLTIP_SIDE_SPACE)
                ui.Label("ALT", alignment=ui.Alignment.CENTER, name="shortcut")
                ui.Image(Icons().get("add_tip_dark"), width=14, height=25)
                ui.Image(Icons().get("mouseTip_leftClick_dark"), width=25, height=25)
                ui.Spacer(width=TOOLTIP_SIDE_SPACE)
        return (79, 32)

    def _build_frame_tooltip(self):
        if not self._tooltips_default_on:
            return (0, 0)
        TOOLTIP_SIDE_SPACE = 5
        boundary = 7
        with ui.VStack():
            ui.Spacer(height=boundary)
            with ui.HStack(height=0):
                ui.Spacer(width=boundary)
                ViewportNavigationTooltip._build_shortcut_ui("F", 18)
                ui.Spacer(width=boundary)
        return (32, 32)
