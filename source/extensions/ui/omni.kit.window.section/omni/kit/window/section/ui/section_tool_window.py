# Copyright (c) 2018-2021, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#
import asyncio
import copy
from typing import Optional

import carb
import carb.settings
import omni.kit.app
import omni.usd
from carb.eventdispatcher import get_eventdispatcher
from omni import ui
from omni.kit.widget.settings.settings_model import SettingModel
from omni.kit.widgets.custom import DefaultWidgetStyle, get_ui_style
from pxr import Tf, Usd

from ..common import (
    DEFAULT_SECTION_TOP,
    SETTING_SECTION_ALWAYS_DISPLAY,
    SETTING_SECTION_DIRECTION,
    SETTING_SECTION_ENABLED,
    SETTING_SECTION_MANIPULATOR,
    SectionManager,
)
from ..tool import SectionTool
from .constant import PANEL_PADDING_INNER_X, UI_STYLE
from .options_panel import OptionsPanel
from .quick_move_panel import QuickMovePanel
from .switch import Switch

SAVE_NORMAL_IMAGE = "Save_Small.svg"
SAVE_DIRTY_IMAGE = "Save_Small_blue.svg"
TRANSFORM_OP_SETTING = "/app/transform/operation"


class SectionToolWindow(ui.Window):
    def __init__(self, title: str, ext_id: str):
        super().__init__(title, resizable=True, padding_x=8, padding_y=8, auto_resize=True)

        self._ext_id = ext_id

        self._settings = carb.settings.get_settings()
        self._section_enabled = self._settings.get_as_bool(SETTING_SECTION_ENABLED)
        self._manipulator_visible = self._settings.get_as_bool(SETTING_SECTION_MANIPULATOR)
        self._always_display_model = SettingModel(SETTING_SECTION_ALWAYS_DISPLAY)

        self._usd_context = omni.usd.get_context()
        self._stage_subs = [
            get_eventdispatcher().observe_event(
                observer_name="omni.kit.window.section.startup",
                event_name=self._usd_context.stage_event_name(e),
                on_event=trigger_fn,
            )
            for e, trigger_fn in [
                (omni.usd.StageEventType.OPENED, self._on_stage_opened),
                (omni.usd.StageEventType.CLOSING, self._on_stage_closing),
            ]
        ]
        self.__stage_listener = Tf.Notice.Register(
            Usd.Notice.ObjectsChanged, self.__on_stage_objects_changed, omni.usd.get_context().get_stage()
        )
        self._always_display_switch: Optional[Switch] = None

        SectionManager().refresh()
        self._start_dirty_listen()

        # UI style
        ui_style = get_ui_style()
        style = copy.copy(DefaultWidgetStyle.get_style(ui_style))
        style.update(UI_STYLE)
        self.frame.set_style(style)

        self.frame.set_build_fn(self._build_ui)
        self.set_visibility_changed_fn(self._on_visibility_changed)

        # Dock
        self.deferred_dock_in("Stage", ui.DockPolicy.CURRENT_WINDOW_IS_ACTIVE)
        self.set_docked_changed_fn(self._on_dock_changed)

    def __on_stage_objects_changed(self, notice, stage):
        if not notice:  # pragma: no cover
            return
        for path in notice.GetResyncedPaths():
            prim_path = path.GetPrimPath()
            if prim_path in ["/SectionTools", "/SectionTools/Section_Tool_Object"]:
                if not omni.usd.get_context().get_stage().GetPrimAtPath(prim_path):
                    # OMFP-752: Disable section when delete from stage panel
                    self.set_active(False)
                    self.show(False)
                    SectionManager().clear()
                    SectionTool().set_visibility(False, self._ext_id)

    def destroy(self):
        self.visible = False
        SectionManager().set_added_section_callback(None)
        self._stop_dirty_listen()
        self._stage_subs.clear()
        self._stage_subs = None
        self._options_panel = None
        self._quickmove_panel = None
        self._usd_context = None
        self._settings = None
        if self._always_display_switch:
            self._always_display_switch.destroy()
            self._always_display_switch = None
        super().destroy()

    def dock(self, window_name: str, ratio: float = 0.311, position=ui.DockPosition.SAME):
        if not self.docked:  # pragma: no cover
            window = ui.Workspace.get_window(window_name)
            if window:
                self.dock_in(window, position, ratio)
        return self.docked

    def _on_dock_changed(self, docked: bool):
        self.auto_resize = docked

    def is_visible(self) -> bool:
        return self.visible

    def _on_visibility_changed(self, visible: bool) -> None:
        # OMFP-2189: hide section only when dialog closed and not always display
        if visible:
            self.frame.rebuild()
            self.enable_section(True)
            self._on_show_gizmo()
        else:
            if not self._always_display_model.as_bool:
                self.enable_section(False)
            SectionTool().show_section_gizmo(False)

    def show(self, visible, *_):
        self.visible = visible

    def set_active(self, active: bool):
        if self._section_enabled != active:
            self._section_enabled = active
            self._settings.set_bool(SETTING_SECTION_ENABLED, active)

    def get_active(self):
        return self._section_enabled

    def enable_section(self, enable: bool) -> None:
        # Enable/Disable section slice
        self.set_active(enable)

        # Enable/Disable section manipulator
        if enable != self._manipulator_visible:
            self._settings.set(SETTING_SECTION_MANIPULATOR, enable)

    def _on_section_enabled(self):
        self._section_enabled = self._settings.get_as_bool(SETTING_SECTION_ENABLED)
        # add a section if no section exist
        if SectionManager().section_count == 0:
            SectionManager().add_section()
            self._on_show_gizmo()

        self._on_section_visibility_changed()

    def _on_section_visibility_changed(self):
        self._manipulator_visible = self._settings.get_as_bool(SETTING_SECTION_MANIPULATOR)
        SectionTool().set_visibility(self._manipulator_visible, self._ext_id)

    def _build_ui(self):
        def generate():
            with ui.VStack(spacing=10):
                with ui.HStack(height=0):
                    ui.Spacer()
                    ui.Label("Always Display Section", width=0)
                    ui.Spacer(width=16)
                    self._always_display_switch = Switch(self._always_display_model)
                    ui.Spacer(width=PANEL_PADDING_INNER_X)
                self._options_panel = OptionsPanel()
                self._quickmove_panel = QuickMovePanel()

        # No idea why we need to do this to draw the correct size.
        with self.frame:
            scrolling_frame = ui.ScrollingFrame(build_fn=generate)
        scrolling_frame.call_build_fn()

        self._on_section_enabled()

    def _on_stage_closing(self, _):
        # Hide window
        self.visible = False
        # Disable section
        self.enable_section(False)
        self._stop_dirty_listen()

    def _on_stage_opened(self, _):
        SectionTool().set_visibility(False, self._ext_id)
        SectionManager().refresh()
        SectionTool().reset()
        self._start_dirty_listen()

    def _update_section_cut_direction(self):
        section_direction_top = bool(self._settings.get(SETTING_SECTION_DIRECTION) == DEFAULT_SECTION_TOP)
        SectionManager().set_direction(section_direction_top)

    def _start_dirty_listen(self):
        self._stop_dirty_listen()

        self._cut_direction_setting_tp = omni.kit.app.SettingChangeSubscription(
            SETTING_SECTION_DIRECTION, lambda *_: self._update_section_cut_direction()
        )
        self._update_setting_tp = omni.kit.app.SettingChangeSubscription(
            SETTING_SECTION_ENABLED, lambda *_: self._on_section_enabled()
        )
        self._manipulator_visibility_setting_tp = omni.kit.app.SettingChangeSubscription(
            SETTING_SECTION_MANIPULATOR, lambda *_: self._on_section_visibility_changed()
        )

    def _stop_dirty_listen(self):
        self._update_setting_tp = None
        self._cut_direction_setting_tp = None
        self._manipulator_visibility_setting_tp = None

    def _on_show_gizmo(self):
        self._settings.set(TRANSFORM_OP_SETTING, "move")
        # OM-33610: when user select widget, make sure widget is displayed
        self.enable_section(True)
        asyncio.ensure_future(self.wait_section_widget())

    async def wait_section_widget(self):
        for i in range(3):
            await omni.kit.app.get_app().next_update_async()

        SectionTool().show_section_gizmo(True)
