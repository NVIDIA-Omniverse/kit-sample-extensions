import os
import platform
import webbrowser
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import carb
import carb.settings
import carb.tokens
import omni.ext
import omni.ui as ui
from omni.kit.commands import execute
from omni.kit.viewport.menubar.core import ViewportMenuDelegate
from omni.kit.viewport.navigation.core import IMAGE_SIZE, ViewportNavigationButton, get_navigation_bar
from omni.kit.widgets.custom import PreferencesHelper

from .style import MENU_ITEM_STYLE
from .utils import capture_regular

__all__ = ["Extension"]

SETTINGS_ROOT = "/exts/omni.kit.viewport.navigation.capture/"
SCREENSHOTS_PREFERENCES_PAGE_TITLE = "Capture Screenshot"
SETTING_DASHBOARD_ROOT = "/exts/omni.usd_presenter.dashboard/"
SETTING_DASHBOARD_RUN_SCREENSHOT = SETTING_DASHBOARD_ROOT + "runScreenshot"
SETTING_ACTIVE_MARKUP = "/exts/omni.kit.markup.core/active_markup"
SHOT_TYPE_REGULAR = 0


@dataclass
class CaptureType:
    type: Any
    text: str
    icon: str


class CaptureTypes:
    REGULAR = CaptureType(SHOT_TYPE_REGULAR, "Screenshot", "Screenshot")
    MARKUP = CaptureType(-1, "Markup Screenshot", "Screenshot")
    ALL = [REGULAR, MARKUP]


class Extension(omni.ext.IExt):

    _instance = None

    # ext_id is current extension id. It can be used with extension manager to query additional information, like where
    # this extension is located on filesystem.
    def on_startup(self, ext_id):
        if not carb.settings.get_settings().get(SETTINGS_ROOT + "enable"):
            return

        sections = ext_id.split("-")  # [name, version]
        self._ext_name = sections[0]
        self._screenshot_type: CaptureType = CaptureTypes.REGULAR

        navigation_bar = get_navigation_bar()

        tokens = carb.tokens.get_tokens_interface()
        icon_path = tokens.resolve(f"${{{self._ext_name}}}/icons/")
        true_image = icon_path + "navCapture_active_dark.svg"
        false_image = icon_path + "navCapture_dark.svg"
        order_setting = SETTINGS_ROOT + "order"
        visible_setting = SETTINGS_ROOT + "visible"
        name = self._screenshot_type.icon
        style = {
            "Navigation.Button.Image::" + f"{name}": {"image_url": f"{false_image}"},
            "Navigation.Button.Image::" + f"{name}:checked": {"image_url": f"{true_image}"},
            "Menu.Item.Icon::Screenshot": {"image_url": f"{icon_path}screenshot_viewport.svg"},
            "Navigation.Button.Image::Screenshot": {"image_url": f"{false_image}"},
        }

        with navigation_bar:  # type: ignore
            self._button = ViewportNavigationButton(
                name,
                IMAGE_SIZE,
                visible_setting_path=visible_setting,
                order_setting_path=order_setting,
                clicked_fn=self._on_click,
                build_menu_fn=self._build_menu_items,
                has_triangle=True,
                build_tooltip_fn=self._build_tooltip,
                style=style,
            )
            self._button.set_state(False)

        self._settings = carb.settings.get_settings()
        self._markup_active_sub = self._settings.subscribe_to_node_change_events(
            SETTING_ACTIVE_MARKUP, self._on_markup_active
        )

        Extension._instance = self

    @staticmethod
    def get_instance():
        return Extension._instance

    def _build_tooltip(self):
        TOOLTIP_SIDE_SPACE = 5
        with ui.VStack():
            ui.Spacer(height=TOOLTIP_SIDE_SPACE)
            with ui.HStack(height=0):
                ui.Spacer(width=TOOLTIP_SIDE_SPACE)
                ui.Label("Capture", alignment=ui.Alignment.CENTER, name="shortcut")
                ui.Spacer(width=TOOLTIP_SIDE_SPACE)
        return (85, 32)

    def on_shutdown(self):  # pragma: no cover
        if self._button:
            self._button.destroy()
        self._button = None
        self.destroy()
        Extension._instance = None  # TODO: need enough test for coroutines

    def destroy(self):  # pragma: no cover
        self._settings.unsubscribe_to_change_events(self._markup_active_sub)

    def _build_menu_items(self) -> list:
        return [
            ui.MenuItem(
                "View Screenshots",
                delegate=ViewportMenuDelegate(),
                triggered_fn=self._on_view_screenshots,
                style=MENU_ITEM_STYLE,
            ),
        ]

    def _on_markup_active(self, *_):
        # markup status has changed, so we'll need to rebuild the menu on next open.
        self._menu = None
        active_markup = bool(self._settings.get(SETTING_ACTIVE_MARKUP))
        # ensure that the markup-type is enabled or disabled appropriately.
        self._screenshot_type.type = CaptureTypes.MARKUP.type if active_markup else SHOT_TYPE_REGULAR

    def _set_screenshot_type(self, screenshot_type: CaptureType):
        self._screenshot_type = screenshot_type
        if self._button:
            self._button.name = screenshot_type.icon

    def _on_screenshot_settings(self):
        PreferencesHelper.show_page(SCREENSHOTS_PREFERENCES_PAGE_TITLE)

    def _on_view_screenshots(self):
        screenshot_path = Path(self._settings.get_as_string("/persistent/app/captureFrame/path")).absolute()
        if not screenshot_path.exists():
            carb.log_error(f"Screenshot path {screenshot_path} does not exist!")
        else:
            if platform.system() == "Windows":
                os.startfile(str(screenshot_path))
            elif platform.system() == "Linux":
                os.system(f"xdg-open {str(screenshot_path)}")
            else:
                webbrowser.open(str(screenshot_path))

    def _on_click(self, *_):
        if self._screenshot_type.type == SHOT_TYPE_REGULAR:
            capture_regular(self._on_capture_done)
        elif self._screenshot_type.type == CaptureTypes.MARKUP.type:
            # this may cause flaky test failed
            try:
                import omni.kit.markup.core
            except ImportError:
                return
            else:  # pragma: no cover
                # NOTE: the command is a part of omni.kit.markup.core
                execute("TakeMarkupScreenshotCommand")

    def _on_capture_done(self, capture_file: str) -> None:
        if self._button:
            self._button.enabled = True
            self._button.set_state(False)
        self._settings.set_int(SETTING_DASHBOARD_RUN_SCREENSHOT, 0)
