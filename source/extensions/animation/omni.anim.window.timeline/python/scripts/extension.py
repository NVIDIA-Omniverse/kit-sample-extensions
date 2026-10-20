from typing import List

import carb.settings
import omni.ext

from .keyframe_listener import KeyFrameListener
from .timeline_toolbar import TimelineToolbar
from .utils import (
    AUTO_KEY_ALL_XFORM_SETTING,
    COMPENSATE_PLAY_DELAY_IN_SECS_SETTING,
    SNAP_TO_FRAME_SETTING,
    TIME_DISPLAY_SETTING,
    TimeDisplay,
    init_icon_path,
)

g_singleton = None


class TimelineWindowExtension(omni.ext.IExt):

    def on_startup(self, ext_id):
        manager = omni.kit.app.get_app().get_extension_manager()
        extension_path = manager.get_extension_path(ext_id)
        init_icon_path(extension_path)
        settings = carb.settings.get_settings()
        settings.set_default_string(TIME_DISPLAY_SETTING, TimeDisplay.FRAMES)
        settings.set_default_bool(AUTO_KEY_ALL_XFORM_SETTING, False)
        settings.set_default_float(COMPENSATE_PLAY_DELAY_IN_SECS_SETTING, 0.0)
        settings.set_default_bool(SNAP_TO_FRAME_SETTING, False)

        self._keyframe_listener = KeyFrameListener.get_instance()
        self._toolbar = TimelineToolbar(ext_id)

        global g_singleton
        g_singleton = self

    def on_shutdown(self):
        global g_singleton
        g_singleton = None

        self._keyframe_listener = None
        KeyFrameListener.destroy()
        if self._toolbar:
            self._toolbar.destroy()
            self._toolbar = None

    def get_FPS_list(self) -> List[str]:
        if self._toolbar:
            return self._toolbar.get_FPS_list()


def get_instance():
    return g_singleton
