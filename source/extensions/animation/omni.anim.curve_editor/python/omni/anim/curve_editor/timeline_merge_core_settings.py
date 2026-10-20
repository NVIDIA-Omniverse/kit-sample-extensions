import weakref

import carb
import carb.settings
from omni import ui


class SettingsManager:
    def __init__(self):
        self._settings = carb.settings.get_settings()

    def get_int_setting(self, key: str, default_value: int):
        self._settings.set_default(key, default_value)
        value = self._settings.get_as_int(key)
        # carb.log_warn(f"Getting int key={key} value={value} default={default_value}")
        if value == None:
            return default_value
        return value

    def get_float_setting(self, key: str, default_value: float):
        self._settings.set_default(key, default_value)
        value = self._settings.get_as_float(key)
        # carb.log_warn(f"Getting float key={key} value={value} default={default_value}")
        if value == None:
            return default_value
        return value

    def get_setting(self, key, default_value):
        self._settings.set_default(key, default_value)
        value = self._settings.get(key)
        # carb.log_warn(f"Getting key={key} value={value} default={default_value}")
        if value == None:
            return default_value
        return value

    def set_setting(self, key: str, new_value):
        self._settings.set(key, new_value)


SNAP_TO_FRAME_KEY = "/persistent/exts/omni.anim.curve_editor/snapToFrame"
BEGIN_RANGE_KEY = "/persistent/exts/omni.anim.curve_editor/timelineBeginRange"
END_RANGE_KEY = "/persistent/exts/omni.anim.curve_editor/timelineEndRange"

# TODO relam -- First, we're going to just save and load everything on demand... if this
# yields poor performance, it should be relatively easy to cache/flush this system as
# needed.  But then, we'd want to tie in to the save/load stage functionality to ensure
# we persist at the appropriate time.
g_singleton = None


class TimelineMergeCoreSettings(SettingsManager):
    def __init__(self):
        super().__init__()

    # TODO relam -- Figure out if there is a better, more "macro" way to do this...
    # All this typing is prone to error... something with a table would be preferable

    @property
    def snap_to_frame(self):
        return self.get_setting(SNAP_TO_FRAME_KEY, True)

    @snap_to_frame.setter
    def snap_to_frame(self, snap):
        self.set_setting(SNAP_TO_FRAME_KEY, snap)

    @property
    def range_begin(self):
        return self.get_float_setting(BEGIN_RANGE_KEY, 0)

    @range_begin.setter
    def range_begin(self, range_begin):
        self.set_setting(BEGIN_RANGE_KEY, range_begin)

    @property
    def range_end(self):
        return self.get_float_setting(END_RANGE_KEY, 100)

    @range_end.setter
    def range_end(self, range_end):
        self.set_setting(END_RANGE_KEY, range_end)

    # -----------------------------------------
    @staticmethod
    def get_instance():
        global g_singleton
        if g_singleton == None:
            g_singleton = TimelineMergeCoreSettings()
        return weakref.proxy(g_singleton)

    # must call before extension unload GC
    @staticmethod
    def destroy():
        global g_singleton
        g_singleton = None
