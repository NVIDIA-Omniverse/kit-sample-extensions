# Copyright (c) 2022, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

__all__ = ["Extension", "get_instance"]

from functools import partial
from typing import Optional

import omni.ext
import omni.ui as ui
from carb import log_error
from omni.kit.menu.utils import MenuItemDescription, add_menu_items, remove_menu_items
from omni.kit.viewport.utility import get_active_viewport_window

from .common import (
    EXTENSION_NAME,
    MEASURE_WINDOW_VISIBLE_CONTEXT,
    SETTINGS_MEASURE_NEXT_SNAP_HOTKEY,
    SETTINGS_MEASURE_NEXT_TOOL_HOTKEY,
    SETTINGS_MEASURE_OPEN_HOTKEY,
    SETTINGS_MEASURE_PREVIOUS_TOOL_HOTKEY,
    VISIBILITY_PATH,
    MeasureMode,
    UserSettings,
    commands,
)
from .interface import MeasurementPropertyWidget, MeasurePanel
from .manager import Hotkey, HotkeyManager, MeasurementManager, ReferenceManager, SelectionStateManager, StateMachine
from .viewport import MeasureScene
from .viewport.snap.attribute_value_cache import AttributeValueCache
from .viewport.tools.viewport_mode_model import CameraManipModeWatcher


class Extension(omni.ext.IExt):

    def __new__(cls, *args, **kwargs):
        if not hasattr(cls, "_instance"):
            cls._instance = super().__new__(cls, *args, **kwargs)
        return cls._instance

    @property
    def panel(self) -> Optional[MeasurePanel]:
        return self._measure_panel or None

    @property
    def viewport(self) -> Optional[MeasureScene]:
        return self._viewport or None

    @property
    def measurements_visible(self) -> bool:
        return self._viewport.measurements_visible if self._viewport else True

    def set_measurements_visible(self, visible: bool) -> None:
        """Public API: transiently show/hide all completed measurement drawings.

        This does NOT mutate the persistent Display-menu visibility preference
        (``VISIBILITY_PATH``) or the per-measurement USD payloads, so the user's
        own visibility choices are preserved and nothing is persisted. Intended
        for external UI (e.g. the navigation-bar Measure button) to couple
        measurement visibility to tool activation on an opt-in basis.
        """
        if self._viewport:
            self._viewport.set_measurements_visible(visible)

    def on_startup(self, ext_id) -> None:
        sections = ext_id.split("-")
        self._ext_name = sections[0]

        # Register commands
        commands.register()

        # Regiseter Property Widget
        self.__register_property_widget()

        # Initialize User Settings, Reference Manager, and Measurement Manager and Hotkey Manager
        UserSettings()
        ReferenceManager()
        MeasurementManager()
        AttributeValueCache()
        HotkeyManager()

        # Initialize Editor Window
        self._measure_panel: Optional[MeasurePanel] = MeasurePanel()
        ui.Workspace.set_show_window_fn(EXTENSION_NAME, partial(self._show_window, None))
        self._visibility_sub = ui.Workspace.set_window_visibility_changed_callback(self._on_visibility_changed)

        self._menu_entry = [
            MenuItemDescription(
                name=EXTENSION_NAME,
                ticked=False,
                ticked_fn=self._is_visible,
                onclick_fn=self._toggle_window,
            )
        ]

        add_menu_items(self._menu_entry, name="Tools")

        # Create the Viewport Scene Window
        viewport_window = get_active_viewport_window()
        if not viewport_window:
            log_error(f"No Viewport Window to add {ext_id} scene to.")
            return

        ReferenceManager().selection_state = SelectionStateManager(viewport_window)

        self._viewport: Optional[MeasureScene] = MeasureScene(viewport_window, ext_id)

        # For hot reloading
        MeasurementManager()._populate_model_from_stage()

        # Register menubar
        self.__register_display_setting()

        # Add hotkeys
        self._register_hotkeys(self._ext_name)

    def on_shutdown(self) -> None:
        ui.Workspace.set_show_window_fn(EXTENSION_NAME, None)
        if self._visibility_sub is not None:
            ui.Workspace.remove_window_visibility_changed_callback(self._visibility_sub)
            self._visibility_sub = None

        remove_menu_items(self._menu_entry, name="Tools")
        self._menu_entry = None
        ui.Workspace.set_show_window_fn(EXTENSION_NAME, None)

        # Ensure selection state is restored
        ReferenceManager().selection_state.restore()

        # Clear out the Measurement Manager model
        MeasurementManager()._model.clear()
        MeasurementManager.deinit()

        # Ensure that the mode is set to None before shutting down the extension. Must happen after MeasurementManager.
        StateMachine().deinit()

        AttributeValueCache.deinit()

        HotkeyManager.deinit()

        # Unregister Commands
        commands.unregister()

        # Unregister property widget
        self.__unregister_property_widget()

        # Unregister Menubar
        self.__unregister_display_setting()

        # Save settings to user's extension user.config.json
        UserSettings().serialize()
        # Unregiseter Preferences
        UserSettings().unregister_preferences()

        UserSettings.deinit()

        # Viewport Cleanup
        if self._viewport:
            self._viewport.destroy()
            self._viewport = None

        self._menu = None
        if self._measure_panel:
            self._measure_panel.destroy()
            self._measure_panel = None

        CameraManipModeWatcher.delete_instance()

        Extension._instance = None  # Clear the instance of the extension on shutdown

    def _is_visible(self) -> bool:
        return False if self._measure_panel is None else self._measure_panel.visible

    def _show_window(self, menu: Optional[str], value: bool):
        if self._measure_panel:
            self._measure_panel.visible = value
            if not value:
                StateMachine().reset_state_to_default(is_current_tool=False)

    def _toggle_window(self):
        if self._measure_panel:
            self._show_window(None, not self._measure_panel.visible)

    def _on_visibility_changed(self, name: str, value: bool) -> None:
        if name == EXTENSION_NAME and value:
            if UserSettings().session.startup_tool != MeasureMode.NONE and UserSettings().session.startup_enabled:
                StateMachine().set_creation_state(UserSettings().session.startup_tool)

    def __register_display_setting(self):
        try:
            from omni.kit.viewport.menubar.core import CategoryStateItem
            from omni.kit.viewport.menubar.display import get_instance as get_display_instance

            self._category_item = CategoryStateItem("Measurements", setting_path=VISIBILITY_PATH)
            get_display_instance().register_custom_category_item("Show By Type", self._category_item)

        except ImportError as e:
            log_error(e)

    def __unregister_display_setting(self):
        try:
            from omni.kit.viewport.menubar.display import get_instance as get_display_instance

            get_display_instance().deregister_custom_category_item("Show By Type", self._category_item)
        except ImportError as e:
            log_error(e)

    def __register_property_widget(self):
        try:
            from omni.kit.window.property import get_window as get_property_window

            p_window = get_property_window()
            if p_window:
                p_window.register_widget("prim", "measurement", MeasurementPropertyWidget())
        except ImportError as e:
            log_error(e)

    def __unregister_property_widget(self):
        try:
            from omni.kit.window.property import get_window as get_property_window

            p_window = get_property_window()
            if p_window:
                p_window.unregister_widget("prim", "measurement")
        except ImportError as e:
            log_error(e)

    def _register_hotkeys(self, ext_name: str):
        HotkeyManager().extension_name = ext_name
        key = HotkeyManager().get_key(SETTINGS_MEASURE_OPEN_HOTKEY, default=None)  # No default
        if key:
            HotkeyManager().add_hotkey(Hotkey("open", self._open_window, key))
        key = HotkeyManager().get_key(SETTINGS_MEASURE_NEXT_TOOL_HOTKEY, default="PAGE_UP")
        HotkeyManager().add_hotkey(Hotkey("next-tool", self._next_tool, key, MEASURE_WINDOW_VISIBLE_CONTEXT))
        key = HotkeyManager().get_key(SETTINGS_MEASURE_PREVIOUS_TOOL_HOTKEY, default="PAGE_DOWN")
        HotkeyManager().add_hotkey(Hotkey("previous-tool", self._previous_tool, key, MEASURE_WINDOW_VISIBLE_CONTEXT))
        key = HotkeyManager().get_key(SETTINGS_MEASURE_NEXT_SNAP_HOTKEY, default="ALT + S")
        HotkeyManager().add_hotkey(Hotkey("next-snap", self._next_snap, key, MEASURE_WINDOW_VISIBLE_CONTEXT))

    def _open_window(self) -> None:
        if not self.panel.visible:
            self.panel.visible = True

    def _next_tool(self) -> None:
        sm = StateMachine()
        if sm:
            sm.set_next_creation_state()
            self._refresh_window()

    def _previous_tool(self) -> None:
        sm = StateMachine()
        if sm:
            sm.set_previous_creation_state()
            self._refresh_window()

    def _next_snap(self) -> None:
        rm = ReferenceManager()
        if rm:
            placement_panel = rm.ui_placement_panel
            if placement_panel:
                snap_group = placement_panel.snap_group
                snap_group.set_next_snap()
                self._refresh_window()

    def _refresh_window(self) -> None:
        window = ui.Workspace.get_window(EXTENSION_NAME)
        if window:
            window.frame.invalidate_raster()


def get_instance() -> Extension:
    return Extension()
