import carb.dictionary
import carb.settings
import omni.ext

from .window import SettingsWindow

WINDOW_NAME = "Debug Settings"
STARTUP_VIS = carb.settings.get_settings().get_as_bool("/exts/omni/kit/debug/settings/visible_at_startup")
VIS_CHANGED_SETTINGS_PATH = "/exts/omni/kit/debug/settings/visibility"


class SettingsWindowExtension(omni.ext.IExt):
    def on_startup(self):
        self._window = SettingsWindow()

        self._settings = carb.settings.get_settings()
        self._change_id = self._settings.subscribe_to_node_change_events(
            VIS_CHANGED_SETTINGS_PATH, self._on_visibility_changed
        )
        self._window.visible = STARTUP_VIS
        self._window.set_visibility_changed_fn(self._debug_settings_visibility_changed)

    def _on_visibility_changed(self, item: carb.dictionary.Item, event_type: carb.settings.ChangeEventType):
        if event_type == carb.settings.ChangeEventType.CHANGED:
            if item.get_dict() == True:
                self._window.visible = True
            else:
                self._window.visible = False

    def _debug_settings_visibility_changed(self, v):
        carb.settings.get_settings().set(VIS_CHANGED_SETTINGS_PATH, v)

    def on_shutdown(self):
        if self._window:
            self._window.destroy()
            self._window = None
        self._settings.unsubscribe_to_change_events(self._change_id)
        del self._settings
