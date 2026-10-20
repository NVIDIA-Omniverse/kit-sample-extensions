# Copyright (c) 2022, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

import asyncio
from typing import Optional

import omni.kit.app
import omni.kit.menu.utils

# from omni.kit.ui import get_editor_menu
import omni.usd as ou
from carb import log_warn
from omni import ui
from omni.kit.viewport.utility import get_active_viewport_window
from pxr import UsdGeom

from ..common import EXTENSION_NAME, MEASURE_WINDOW_VISIBLE_CONTEXT, DistanceType, MeasureMode, MeasureState
from ..manager import HotkeyManager, MeasurementManager, ReferenceManager, StateMachine
from ..system import MeasurePayload
from ._widgets import *
from .style import *
from .sub_panel import DisplayPanel, GlobalPanel, ManagePanel, PlacementPanel


class MeasurePanel(ui.Window):
    WINDOW_WIDTH = 465
    WINDOW_HEIGHT = 800
    VIEWPORT_MAIN_MENUBAR_HEIGHT = 32
    VIEWPORT_BOTTOM_MENUBAR_HEIGHT = 64
    SPACING = 9

    def __init__(self):
        self._pn_global: Optional[GlobalPanel] = None
        self._pn_placement: Optional[PlacementPanel] = None
        self._pn_display: Optional[DisplayPanel] = None
        self._pn_manage: Optional[ManagePanel] = None

        super().__init__(
            EXTENSION_NAME,
            width=MeasurePanel.WINDOW_WIDTH,
            height=MeasurePanel.WINDOW_HEIGHT,
            dockPreference=ui.DockPreference.DISABLED,
            resizable=True,
            padding_x=4,
            padding_y=12,
            flags=ui.WINDOW_FLAGS_NO_SCROLLBAR,
            visible=False,  # Initial state
        )
        self.deferred_dock_in("Stage", ui.DockPolicy.CURRENT_WINDOW_IS_ACTIVE)

        self._build_content()

        self._undocked_width = self.width
        self._undocked_height = self.height

        # Subscriptions
        self.set_visibility_changed_fn(self.__on_panel_visibility_changed)
        self.set_focused_changed_fn(self.__on_focused_changed)
        self.set_selected_in_dock_changed_fn(self.__on_panel_selected_changed)
        self.set_docked_changed_fn(self._dock_changed)
        self.set_width_changed_fn(self._width_changed)
        self.set_height_changed_fn(self._height_changed)

        StateMachine().add_tool_state_changed_fn(self._on_tool_state_changed)

        self._viewport_handle = get_active_viewport_window()
        if self._viewport_handle:
            self._viewport_handle.set_height_changed_fn(self._on_viewport_size_changed)
            self._viewport_handle.set_width_changed_fn(self._on_viewport_size_changed)
            self._viewport_handle.set_position_x_changed_fn(self._on_viewport_size_changed)
            self._viewport_handle.set_position_y_changed_fn(self._on_viewport_size_changed)

        # Assign itself and sub panels to the reference manager
        ReferenceManager().ui_panel = self

        self._window_updated = False

    # ------ UI ------
    def _build_content(self):
        with self.frame:
            with ui.ScrollingFrame(style={"ScrollingFrame": {"background_color": 0}}):
                with ui.VStack(spacing=12, height=0):
                    self._pn_global = GlobalPanel()
                    self._pn_placement = PlacementPanel()
                    self._pn_placement.visible = False  # only occurs on app startup
                    self._pn_display = DisplayPanel()
                    self._pn_manage = ManagePanel()

        # Attach to global callbacks
        self._pn_global.add_measure_selected_fn(self._on_measure_selected)

    # ------ Global Tool Callbacks ------
    def _on_measure_selected(self) -> None:
        """
        Callback for when pressing measure selected button.
        """
        if any([self._pn_global, self._pn_display, self._pn_manage]) is None:
            return

        paths = ou.get_context().get_selection().get_selected_prim_paths()
        if len(paths) < 2:
            log_warn("Incorrect number of objects selected to create a measurement. Requires two(2).")
            return

        # Grab the first two XFormable items of the list
        stage = ou.get_context().get_stage()
        xformable_paths = [path for path in paths if stage.GetPrimAtPath(path).IsA(UsdGeom.Xformable)]

        if len(xformable_paths) < 2:
            log_warn("Incorrect number of Xformable objects in selection to make a measurement. Requires two(2).")
            return

        payload = MeasurePayload()
        payload.prim_paths = xformable_paths[:2]
        payload.points = []
        payload.tool_mode = MeasureMode.SELECTED
        payload.tool_sub_mode = self._pn_global.distance.value
        payload.axis_display = self._pn_display.display_axis
        payload.unit_type = self._pn_display.unit
        payload.precision = self._pn_display.precision
        payload.label_size = self._pn_display.text_size
        payload.label_color = self._pn_display.color
        MeasurementManager().create(payload)
        return

    def _on_tool_state_changed(self, state: MeasureState, mode: MeasureMode) -> None:
        self._pn_placement.visible = state != MeasureState.NONE and mode not in [MeasureMode.NONE, MeasureMode.SELECTED]

    # ------ Listeners / Notifiers ------
    def __on_panel_visibility_changed(self, visible: bool):
        omni.kit.menu.utils.refresh_menu_items("Tools")

        if not visible:
            StateMachine().reset_state_to_default(is_current_tool=False)
            HotkeyManager().remove_hotkey_context(MEASURE_WINDOW_VISIBLE_CONTEXT)
        else:
            # Delay a frame because the panel may have been docked, then we don't need to set its position
            async def __delay_re_position():
                await omni.kit.app.get_app().next_update_async()
                await omni.kit.app.get_app().next_update_async()
                self._update_window_position()
                HotkeyManager().hotkey_context.push(MEASURE_WINDOW_VISIBLE_CONTEXT)

            asyncio.ensure_future(__delay_re_position())

    def __on_focused_changed(self, focused: bool):
        if focused:
            if HotkeyManager().hotkey_context.get() != MEASURE_WINDOW_VISIBLE_CONTEXT:
                HotkeyManager().hotkey_context.push(MEASURE_WINDOW_VISIBLE_CONTEXT)
        elif not self.visible:
            HotkeyManager().remove_hotkey_context(MEASURE_WINDOW_VISIBLE_CONTEXT)

    def __on_panel_selected_changed(self, selected: bool):
        if not selected:
            StateMachine().reset_state_to_default()

    def _on_objects_changed(self, notice, sender) -> None:
        """
        Objects Changed Listener Callback

        Args:
            notice: Notice
            sender: Sender
        """
        pass

    def _update_window_position(self, *_):
        if not self.visible or self.docked or self._window_updated:
            return

        self._window_updated = True

        vp = get_active_viewport_window()
        right = vp.position_x + vp.width
        x = right - self.width - MeasurePanel.SPACING
        y = vp.position_y + MeasurePanel.VIEWPORT_MAIN_MENUBAR_HEIGHT + MeasurePanel.SPACING

        if vp.docked and vp.dock_tab_bar_visible:
            y += 18

        self.setPosition(x, y)

        height = min(
            vp.height
            - MeasurePanel.VIEWPORT_MAIN_MENUBAR_HEIGHT
            - MeasurePanel.VIEWPORT_BOTTOM_MENUBAR_HEIGHT
            - MeasurePanel.SPACING,
            MeasurePanel.WINDOW_HEIGHT,
        )
        self.height = height

    def _on_viewport_size_changed(self, *_):
        # When viewport size changed, we need to update placement of measure panel when it's opened next time
        self._window_updated = False

    def _width_changed(self, width: float):
        if not self.docked:
            self._undocked_width = width

    def _height_changed(self, height: float):
        if not self.docked:
            self._undocked_height = height

    def _dock_changed(self, docked: bool):
        if not docked:
            self.width = self._undocked_width
            self.height = self._undocked_height
