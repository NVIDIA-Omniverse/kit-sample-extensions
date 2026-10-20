# Copyright (c) 2022, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#
from functools import partial
from typing import Optional

import carb.dictionary
import carb.settings
import omni.ext
import omni.ui as ui
import omni.usd
from carb.eventdispatcher import get_eventdispatcher
from omni.kit.menu.utils import MenuHelperExtension
from pxr import Gf, Usd

from .common import CURRENT_TOOL_PATH, SETTING_SECTION_ENABLED, WINDOW_NAME
from .common.section_manager import SectionManager
from .tool import SectionTool
from .ui import SectionToolWindow

g_singleton = None


# Any class derived from `omni.ext.IExt` in top level module (defined in `python.modules` of `extension.toml`) will be
# instantiated when extension gets enabled and `on_startup(ext_id)` will be called. Later when extension gets disabled
# on_shutdown() is called.
class SectionToolExtension(omni.ext.IExt, MenuHelperExtension):
    # ext_id is current extension id. It can be used with extension manager to query additional information, like where
    # this extension is located on filesystem.
    SETTING_MENU_PATH = "/exts/omni.kit.window.section/menuPath"
    VIEW_TOOLBAR_ID = "section"

    def on_startup(self, ext_id):
        self._ext_id = ext_id
        # The ability to show up the window if the system requires it. We use it
        # in QuickLayout.
        self._window = None

        self._section_manager = None

        ui.Workspace.set_show_window_fn(WINDOW_NAME, partial(self.show_window, None))
        self._toggle_id = ui.Workspace.set_window_visibility_changed_callback(self._visibility_changed_fn)

        # Put the new menu
        settings = carb.settings.get_settings()
        self._menu_path = settings.get(SectionToolExtension.SETTING_MENU_PATH)
        menu_name = self._menu_path.split("/")[-1]
        menu_group = "/".join(self._menu_path.split("/")[:-1])
        self.menu_startup(WINDOW_NAME, menu_name, menu_group)
        # for View toolbar
        self._viewport_current_tool_changed_sub = settings.subscribe_to_node_change_events(
            CURRENT_TOOL_PATH, self._on_view_current_tool_changed
        )

        self._stage_sub = get_eventdispatcher().observe_event(
            observer_name="omni.kit.window.section.startup",
            event_name=omni.usd.get_context().stage_event_name(omni.usd.StageEventType.OPENED),
            on_event=self._on_stage_opened,
        )

        global g_singleton
        g_singleton = self

    def on_shutdown(self):
        global g_singleton
        g_singleton = None

        self._stage_sub = None
        if self._window:
            self._window.destroy()
            self._window = None

        SectionTool().destroy()

        settings = carb.settings.get_settings()
        settings.unsubscribe_to_change_events(self._viewport_current_tool_changed_sub)
        self.menu_shutdown()
        # Deregister the function that shows the window from omni.ui
        ui.Workspace.set_show_window_fn(WINDOW_NAME, None)
        ui.Workspace.remove_window_visibility_changed_callback(self._toggle_id)

    def _visibility_changed_fn(self, name: str, visible: bool):
        if name == WINDOW_NAME:
            # Called when the user pressed "X"
            self.menu_refresh()

            # OMFP-3552: disable orbit and teleport
            settings = carb.settings.get_settings()
            TOOL_NAME = WINDOW_NAME
            if visible:
                # avoid turning off other tools such as Measure
                if settings.get_as_string(CURRENT_TOOL_PATH) == "navigation":
                    settings.set_string(CURRENT_TOOL_PATH, TOOL_NAME)
            elif settings.get_as_string(CURRENT_TOOL_PATH) == TOOL_NAME:
                settings.set_string(CURRENT_TOOL_PATH, "navigation")

    def show_window(self, menu, value):
        if value:
            if not self._window:
                self._window = SectionToolWindow(WINDOW_NAME, self._ext_id)
            else:
                self._window.show(True)
        elif self._window:
            self._window.show(False)

    def _on_view_current_tool_changed(self, item, *_):
        current_tool = carb.dictionary.get_dictionary().get(item)
        visible = current_tool == SectionToolExtension.VIEW_TOOLBAR_ID
        if visible:
            self.show_window(None, visible)
        elif current_tool is None or str(current_tool).lower() == "none":
            # "none" means we hide everything
            self.show_window(None, False)

    def get_section_widget_prim(self, create_if_not_exist: bool = False) -> Optional[Usd.Prim]:
        """Get the section widget prim from the current USD stage.

        Args:
            create_if_not_exist (bool): If True, creates the section widget prim
                when it does not already exist on the stage. Defaults to False.

        Returns:
            Usd.Prim or None: The section widget prim, or None if it does not
                exist and create_if_not_exist is False.
        """
        return self.__get_section_manager().get_section_widget_prim(create_if_not_exist)

    def set_widget_position(self, position: Gf.Vec3d) -> None:
        """Set the translation position of the section widget.

        Args:
            position (Gf.Vec3d): The new position to apply to the section widget transform.
        """
        self.__get_section_manager().set_widget_position(position)

    def _on_stage_opened(self, stage_event):
        # Should disable section when stage opened, make render faster
        settings = carb.settings.get_settings()
        if settings.get_as_bool(SETTING_SECTION_ENABLED):
            settings.set_bool(SETTING_SECTION_ENABLED, False)
            # OM-79609: Do not make stage dirty
            omni.usd.get_context().set_pending_edit(False)

    def __get_section_manager(self) -> SectionManager:
        if self._section_manager is None:
            self._section_manager = SectionManager()
        return self._section_manager


def get_instance() -> SectionToolExtension:
    """Return the singleton instance of SectionToolExtension for extension omni.kit.window.section.

    Returns:
        SectionToolExtension: Instance of SectionToolExtension or None if not available.
    """
    return g_singleton
