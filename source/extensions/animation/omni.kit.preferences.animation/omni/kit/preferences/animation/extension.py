import omni.ext
import omni.kit.app

from .animation_preferences import AnimationPreferences
from .curve_settings import (
    CURVE_SETTINGS_TITLE,
    build_curve_preferences,
    get_auto_key_all_xform,
    set_auto_key_all_xform,
)
from .frame_rate_setting import FrameRate, get_frame_rate, set_frame_rate
from .playback_settings import (
    PLAYBACK_SETTINGS_TITLE,
    TICKS_PER_FRAME_SETTING_MAX,
    TICKS_PER_FRAME_SETTING_MIN,
    build_playback_preferences,
    get_compensate_play_dely_in_secs,
    get_play_every_frame,
    get_snap_to_frame,
    get_ticks_per_frame,
    get_use_fixed_time_stepping,
    set_compensate_play_dely_in_secs,
    set_play_every_frame,
    set_snap_to_frame,
    set_ticks_per_frame,
    set_use_fixed_time_stepping,
)
from .time_display import TimeDisplay
from .time_settings import (
    TIME_DISPLAY_SETTING,
    TIME_SETTINGS_TITLE,
    build_time_preferences,
    g_time_display_model,
    get_time_code_range,
    get_time_display,
    set_time_code_range,
    set_time_display,
)
from .usdskel_settings import USDSKEL_SETTINGS_TITLE, build_usdskel_preferences


class KitPreferencesAnimationExt(omni.ext.IExt):
    def on_startup(self, ext_id):
        AnimationPreferences.register_preferences_frame(TIME_SETTINGS_TITLE, build_time_preferences)
        AnimationPreferences.register_preferences_frame(PLAYBACK_SETTINGS_TITLE, build_playback_preferences)
        AnimationPreferences.register_preferences_frame(USDSKEL_SETTINGS_TITLE, build_usdskel_preferences)
        AnimationPreferences.register_preferences_frame(CURVE_SETTINGS_TITLE, build_curve_preferences)
        AnimationPreferences.register_preferences()

    def on_shutdown(self):
        AnimationPreferences.unregister_preferences_frame(TIME_SETTINGS_TITLE)
        AnimationPreferences.unregister_preferences_frame(PLAYBACK_SETTINGS_TITLE)
        AnimationPreferences.unregister_preferences_frame(USDSKEL_SETTINGS_TITLE)
        AnimationPreferences.unregister_preferences_frame(CURVE_SETTINGS_TITLE)
        AnimationPreferences.unregister_preferences()
