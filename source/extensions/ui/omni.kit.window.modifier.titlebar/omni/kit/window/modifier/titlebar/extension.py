import sys
from pathlib import Path

import carb.settings
import carb.tokens
import carb.windowing
import omni.appwindow
import omni.ext

from .settings import *

kWINDOW_SHOW_FILE_FULL_PATH = "/exts/omni.kit.window.modifier.titlebar/showFileFullPath"
kRESPOND_ON_MOUSE_UP_PATH = "/exts/omni.kit.window.modifier.titlebar/respondOnMouseUp"
kCHANGE_WINDOW_REGION_PATH = "/exts/omni.kit.window.modifier.titlebar/changeWindowRegion"
kWINDOW_FONT_NAME_PATH = "/exts/omni.kit.window.modifier.titlebar/defaultFont/name"
kWINDOW_FONT_SIZE_PATH = "/exts/omni.kit.window.modifier.titlebar/defaultFont/size"
kWINDOW_FONT_COLOR_PATH = "/exts/omni.kit.window.modifier.titlebar/defaultFont/color"
kWINDOW_BOARDER_PATH = "/exts/omni.kit.window.modifier.titlebar/windowBorder"
kWINDOW_SEPARATOR_PATH = "/exts/omni.kit.window.modifier.titlebar/separator"
kWINDOW_COLORS_PATH = "/exts/omni.kit.window.modifier.titlebar/colors"
kWINDOW_TITLE_FORMAT_PATH = "/exts/omni.kit.window.modifier.titlebar/titleFormatString"


class ModifierTitleBarExtension(omni.ext.IExt):
    __singleton = None

    @staticmethod
    def get_instance():
        return ModifierTitleBarExtension.__singleton

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._initialized = False

    def on_startup(self, _):
        self.startup()
        ModifierTitleBarExtension.__singleton = self

    def on_shutdown(self):
        self.shutdown()
        ModifierTitleBarExtension.__singleton = None

    def startup(self):
        if self._initialized:
            return

        self._initialized = True
        self._settings = carb.settings.get_settings()
        self._subs = []
        self._modifier = None

        # skip modifier if we are testing in no-window mode
        if "--no-window" in sys.argv:
            return

        if sys.platform != "win32":
            carb.log_info("omni.kit.window.modifier.titlebar: no-op on this platform (Windows-only functionality)")
            return

        from .bindings._modifier import Modifier  # Windows-only native module

        self._setup_default_settings_value()
        self._modifier = Modifier()

        # Apply font settings
        font_size = self._settings.get_as_int(kWINDOW_FONT_SIZE_PATH)
        font_name = self._settings.get_as_string(kWINDOW_FONT_NAME_PATH)
        font_color = self._settings.get_as_int(kWINDOW_FONT_COLOR_PATH)
        self._modifier.setDefaultFont(font_name, font_size, font_color)

        self._subscribe_settings()

        app_window = omni.appwindow.get_default_app_window()
        windowing_interface = carb.windowing.acquire_windowing_interface()
        native_window = windowing_interface.get_native_window(app_window.get_window())

        self._modifier.start(native_window)

    def shutdown(self):
        if not self._initialized:
            return

        self._initialized = False
        self._settings = None

        for sub in self._subs:
            sub.destroy()
        self._subs.clear()

        if self._modifier:
            del self._modifier
            self._modifier = None

    def _subscribe_settings(self):
        self._subs.append(SettingBorder(kWINDOW_BOARDER_PATH, self._modifier))
        self._subs.append(SettingSeparator(kWINDOW_SEPARATOR_PATH, self._modifier))
        self._subs.append(SettingColor(kWINDOW_COLORS_PATH, self._modifier))
        self._subs.append(SettingTitleFormat(kWINDOW_TITLE_FORMAT_PATH, self._modifier))
        self._subs.append(SettingBool(kWINDOW_SHOW_FILE_FULL_PATH, self._modifier.setShowFullPath))
        self._subs.append(SettingBool(kRESPOND_ON_MOUSE_UP_PATH, self._modifier.setRespondOnMouseUp))
        self._subs.append(SettingBool(kCHANGE_WINDOW_REGION_PATH, self._modifier.setChangeWindowRegion))

    def _setup_default_settings_value(self):
        self._settings.set_default(kWINDOW_SHOW_FILE_FULL_PATH, True)
        self._settings.set_default(kRESPOND_ON_MOUSE_UP_PATH, False)
        self._settings.set_default(kCHANGE_WINDOW_REGION_PATH, True)
        self._settings.set_default(kWINDOW_FONT_NAME_PATH, "Arial")
        self._settings.set_default(kWINDOW_FONT_SIZE_PATH, 18)
        self._settings.set_default(kWINDOW_FONT_COLOR_PATH, 0x00606060)
