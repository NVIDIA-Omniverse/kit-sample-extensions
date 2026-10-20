from typing import Any

import carb.dictionary
import carb.settings
import omni.ext
import omni.kit.app
import omni.ui as ui
from omni.kit.viewport.menubar.core import ViewportMenuItem
from omni.kit.viewport.navigation.core import NAVIGATION_IS_LARGE, ViewportNavigationSeparator, get_navigation_bar

__all__ = ["Extension"]

SETTINGS_ROOT = "/exts/omni.kit.viewport.navigation.usd_explorer.bundle/"
SPVISIBLE_SETTINGS_ROOT = "/exts/omni.kit.viewport.navigation"
CURRENT_TOOL_PATH = "/app/viewport/currentTool"
SETTING_NAVIGATION_ROOT = "/exts/omni.kit.tool.navigation/"
NAVIGATION_BAR_VISIBLE_PATH = "/exts/omni.kit.viewport.navigation.core/isVisible"
TOOLS_HIDE_NAVIGATION_BAR_PATH = "/exts/omni.kit.viewport.navigation.usd_explorer.bundle/toolHideNavBar"


class NavigationTailBlank(ViewportMenuItem):
    """A simple spacer with fixed width"""

    def __init__(self, order_setting_path: str) -> None:
        self._WIDTH: int = 12
        super().__init__(order_setting_path=order_setting_path)

    def build_fn(self, _f: Any) -> None:
        ui.Rectangle(name="window_dimension", width=self._WIDTH)

    @property
    def computed_width(self) -> float:
        return self._WIDTH

    @property
    def width(self) -> float:
        return self._WIDTH


class Extension(omni.ext.IExt):
    NAVIGATION_BAR_NAME = None

    # ext_id is current extension id. It can be used with extension manager to query additional information, like where
    # this extension is located on filesystem.
    def on_startup(self, ext_id):
        self._settings = carb.settings.get_settings()
        self._navigation_bar = get_navigation_bar()
        self.separators = {}

        # Insert vertical separators.
        button_names = self._settings.get(f"{SETTINGS_ROOT}separator_button_names")
        with self._navigation_bar:  # type: ignore
            for bn in button_names:  # type: ignore
                sep = ViewportNavigationSeparator(
                    appear_after=bn,
                    order_setting_path=f"{SETTINGS_ROOT}separator_{bn}",
                    visible_setting_path=f"{SPVISIBLE_SETTINGS_ROOT}.{bn}/spvisible",
                )
                self.separators.update({bn: sep})

            NavigationTailBlank(order_setting_path=f"{SETTINGS_ROOT}tail_blank_order")

        self._last_operation = "none"
        self._panel_visible = True
        if self._settings.get_as_bool(NAVIGATION_BAR_VISIBLE_PATH):
            self._navigation_bar.show()  # type: ignore
        self._settings.set(CURRENT_TOOL_PATH, "navigation")
        self._viewport_current_tool_changed_sub = self._settings.subscribe_to_node_change_events(
            CURRENT_TOOL_PATH, self._on_viewport_current_tool_changed
        )

    def _on_viewport_current_tool_changed(self, item, *_) -> None:
        current_tool = carb.dictionary.get_dictionary().get(item)
        if self._panel_visible == bool(current_tool == "navigation"):
            return

        tools_hide_navbar = self._settings.get_as_bool(TOOLS_HIDE_NAVIGATION_BAR_PATH) or False
        if current_tool == "navigation":
            self._panel_visible = True
            self._settings.set_bool(NAVIGATION_BAR_VISIBLE_PATH, True)
        elif tools_hide_navbar:
            self._panel_visible = False
            self._settings.set_bool(NAVIGATION_BAR_VISIBLE_PATH, False)

    def on_size_change(self, is_big: bool) -> None:
        carb.settings.get_settings().set(NAVIGATION_IS_LARGE, is_big)
        self._navigation_bar.rebuild()  # type: ignore

    def on_shutdown(self) -> None:
        for sep in self.separators.values():
            sep.destroy()

        self.separators.clear()

        self._navigation_bar = None
        if self._viewport_current_tool_changed_sub is not None:
            self._settings.unsubscribe_to_change_events(self._viewport_current_tool_changed_sub)
            self._viewport_current_tool_changed_sub = None

        self._last_operation = None
