import carb.settings
import omni.ext
from carb.input import KeyboardInput as Key
from omni.kit.viewport.menubar.core import get_instance as get_menubar_instance

from .constant import (
    NAVIGATION_HOTKEYS_ENABLED,
    NAVIGATION_NEXT_OPERATION,
    NAVIGATION_NEXT_OPERATION_HOTKEY,
    NAVIGATION_TOOL_OPERATION_ACTIVE,
    SETTINGS_ROOT,
)
from .navigation_bar import NavigationBar

__all__ = ["Extension", "get_navigation_bar_name", "get_navigation_bar"]


class Extension(omni.ext.IExt):
    NAVIGATION_BAR_NAME = None

    # ext_id is current extension id. It can be used with extension manager to query additional information, like where
    # this extension is located on filesystem.
    def on_startup(self, ext_id):
        sections = ext_id.split("-")
        self._ext_name = sections[0]

        settings = carb.settings.get_settings()
        bar_name = settings.get_as_string(SETTINGS_ROOT + "barName")
        Extension.NAVIGATION_BAR_NAME = bar_name

        spacing = settings.get_as_int(SETTINGS_ROOT + "spacing")
        self._navigaiton_bar = NavigationBar(bar_name, spacing)

        self.register_hotkeys()

    def on_shutdown(self):
        self._navigaiton_bar.destroy()
        self._navigaiton_bar = None
        self.deregister_hotkeys()

    def register_hotkeys(self):
        self._next_operation_action = None
        self._hotkey_reg = None
        self._action_reg = None
        settings = carb.settings.get_settings()
        enabled = settings.get_as_bool(NAVIGATION_HOTKEYS_ENABLED) or False
        if enabled:
            try:
                import omni.kit.actions.core
                import omni.kit.hotkeys.core

                self._hotkey_reg = omni.kit.hotkeys.core.get_hotkey_registry()
                self._action_reg = omni.kit.actions.core.get_action_registry()

                action = self._ext_name + "-next-operation"
                self._next_operation_action = self._action_reg.register_action(self._ext_name, action, _next_operation)
                hotkey = settings.get_as_string(NAVIGATION_NEXT_OPERATION_HOTKEY)
                if hotkey is None or hotkey == "" or hotkey.lower() == "space":
                    hotkey = omni.kit.hotkeys.core.KeyCombination("SPACE")
                self._hotkey_reg.register_hotkey(self._ext_name, hotkey, self._ext_name, action)
            except:  # pragma: no cover
                carb.log_error("Failed to register hotkeys")

    def deregister_hotkeys(self):
        if self._action_reg and self._hotkey_reg and self._next_operation_action and self._ext_name is not None:
            self._action_reg.deregister_action(self._next_operation_action)
            self._hotkey_reg.deregister_all_hotkeys_for_extension(self._ext_name)
            self._action_reg = None
            self._hotkey_reg = None
            self._next_operation_action = None


def get_navigation_bar_name():
    """Get the navigation bar name if there is an instance of navigation bar"""
    return Extension.NAVIGATION_BAR_NAME


def get_navigation_bar():
    """Get the navigation bar"""
    return get_menubar_instance().get_menubar(Extension.NAVIGATION_BAR_NAME)


def _next_operation():
    settings = carb.settings.get_settings()
    op_map_str = settings.get_as_string(NAVIGATION_NEXT_OPERATION)
    if op_map_str is None and op_map_str != "":
        return
    op_map = op_map_str.split(",")
    current_operation = settings.get_as_string(NAVIGATION_TOOL_OPERATION_ACTIVE)
    if current_operation is not None:
        for op_pair in op_map:
            if op_pair.startswith(current_operation):
                s = op_pair.split("|")
                if len(s) == 2:
                    settings.set(NAVIGATION_TOOL_OPERATION_ACTIVE, s[1])
                return
