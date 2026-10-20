from typing import Optional

import carb.settings
import omni.appwindow
import omni.ext
import omni.kit.app
from carb.eventdispatcher import get_eventdispatcher
from omni import ui
from omni.kit.mainwindow import get_main_window
from omni.kit.menu.utils import MenuAlignment, MenuItemDescription, add_menu_items, rebuild_menus, remove_menu_items

from .ui.controls import ApplicationModeControl, RenderModeControl
from .ui.file_menu import FileMenu

EXTENSION_NAME = "USD Explorer UI/UX Menu Bar"
EXTENSION_DESCRPITION = "Custom Menubar for USD Explorer, Factory Explorer, and possibly other OV apps."
APPLICAITON_MODE_WIDGET_NAME = "Application Mode Widget"
CENTER_WIDGET_OFFSET = 505
NO_RENDER_MODE_OFFSET = 220
NO_FILE_MENU_OFFSET = 140
SETTINGS_INCLUDE_RENDER_MODES_PATH = "exts/omni.kit.usd_explorer.main.menubar/include_render_modes"
SETTINGS_INCLUDE_APPLICATION_MODES_PATH = "exts/omni.kit.usd_explorer.main.menubar/include_application_modes"
SETTINGS_INCLUDE_FILE_MENU_PATH = "exts/omni.kit.usd_explorer.main.menubar/include_file_menu"


class MenubarDelegate(ui.MenuDelegate):
    STYLE = {
        "Label::menubar": {"color": 0xFF444444},
        "Menu.Window:hovered": {"background_selected_color": 0x0},
        "Menu.Window:pressed": {"background_selected_color": 0x0},
    }

    def __init__(self) -> None:
        super().__init__()
        self.__menu_bar_offset = 0  # width of all the menu items before this widget
        self.spacer_width = (ui.Workspace.get_main_window_width() * 0.5) - CENTER_WIDGET_OFFSET
        self.__rmc: Optional[RenderModeControl] = None
        self.__amc: Optional[ApplicationModeControl] = None
        self.__fm: Optional[FileMenu] = None
        self.__amc_frame: Optional[ui.Frame] = None

    @property
    def render_control(self) -> Optional[RenderModeControl]:
        return self.__rmc

    @property
    def application_control(self) -> Optional[ApplicationModeControl]:
        return self.__amc

    @property
    def file_menu(self) -> Optional[FileMenu]:
        return self.__fm

    def build_item(self, menu: ui.MenuHelper) -> None:
        # OMFP-2744: only use style for new menus but keep default system menus no changes
        menu.style = MenubarDelegate.STYLE

        hstack = ui.HStack(content_clipping=1)
        # listen for hstack screen position change so that it's always centered regardless of menu entires in front of it
        hstack.set_computed_content_size_changed_fn(lambda hstack=hstack: self._changed(hstack))
        with hstack:
            draw_render_controls = carb.settings.get_settings().get_as_bool(SETTINGS_INCLUDE_RENDER_MODES_PATH) or False
            draw_file_menu = carb.settings.get_settings().get_as_bool(SETTINGS_INCLUDE_FILE_MENU_PATH) or False

            if draw_file_menu:
                self.__fm = FileMenu()

            if draw_render_controls:
                self.__rmc = RenderModeControl()

            if not draw_file_menu:
                ui.Spacer(width=NO_FILE_MENU_OFFSET)

            if not draw_render_controls:
                ui.Spacer(width=NO_RENDER_MODE_OFFSET)

            def build_frame():
                if carb.settings.get_settings().get_as_bool(SETTINGS_INCLUDE_APPLICATION_MODES_PATH):
                    with ui.HStack():
                        ui.Spacer(width=self.spacer_width - self.__menu_bar_offset)
                        self.__amc = ApplicationModeControl()

            self.__amc_frame = ui.Frame(build_fn=build_frame)
            with self.__amc_frame:
                build_frame()
            ui.Spacer(width=5)

    def get_menu_alignment(self) -> int:
        return MenuAlignment.DEFAULT

    def _changed(self, hstack):
        if self.__menu_bar_offset != hstack.screen_position_x:
            self.__menu_bar_offset = hstack.screen_position_x

        if self.__amc_frame:
            self.__amc_frame.rebuild()


class usd_explorerUIMainMenuBarExtension(omni.ext.IExt):
    def __init__(self) -> None:
        self._menu_list = []
        self._delegate = MenubarDelegate()
        super().__init__()

    def _on_app_window_resized(self, _e) -> None:
        if self._delegate and hasattr(self._delegate, "spacer_width"):
            self._delegate.spacer_width = (ui.Workspace.get_main_window_width() * 0.5) - CENTER_WIDGET_OFFSET
            rebuild_menus()

    def on_startup(self, _ext_id: str) -> None:
        main_window = get_main_window()
        if not main_window:
            return
        self._menu_list = [MenuItemDescription(name="application modes", show_fn=lambda: False)]
        add_menu_items(self._menu_list, name=APPLICAITON_MODE_WIDGET_NAME, delegate=self._delegate, menu_index=103)

        self._app_window_resize_sub = get_eventdispatcher().observe_event(
            observer_name="omni.kit.usd_explorer.main.menubar:Extension",
            event_name=omni.appwindow.GLOBAL_EVENT_WINDOW_RESIZE,
            on_event=self._on_app_window_resized,
        )

    def on_shutdown(self) -> None:
        self._app_window_resize_sub = None
        ApplicationModeControl.shutdown()
        remove_menu_items(self._menu_list, name=APPLICAITON_MODE_WIDGET_NAME)
        self._menu_list.clear()
        self._delegate = None
