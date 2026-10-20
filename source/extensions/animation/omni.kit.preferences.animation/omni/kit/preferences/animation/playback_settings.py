from functools import partial

import carb.settings
import omni.kit.app
from omni import ui
from omni.kit.window.preferences import PERSISTENT_SETTINGS_PREFIX, PreferenceBuilder, SettingType

PLAYBACK_SETTINGS_TITLE = "Playback Settings"

USE_FIXED_TIME_STEPPING_SETTING = f"/app/player/useFixedTimeStepping"
USE_FIXED_TIME_STEPPING_SETTING_DEFAULT = True
USE_FIXED_TIME_STEPPING_TOOLTIP = "This is ideal to make simulation and animation completely synchronized.\n\
It may also limit the frame rate (see Play Every Frame) such that the elapsed wall clock time matches with \n\
the frame's delta time. When the system runs slower than this, animation playback may slow down \n\
(see Wall Clock Time Delay Compenstation)."
COMPENSATE_PLAY_DELAY_IN_SECS_SETTING = f"/app/player/CompensatePlayDelayInSecs"
COMPENSATE_PLAY_DELAY_IN_SECS_SETTING_DEFAULT = 0.0
COMPENSATE_PLAY_DELAY_IN_SECS_TOOLTIP = 'This is an advanced setting. Only effective when Fixed Time Step is on. \n\
It can compensate for frames that take longer to compute than what is derived from the frame\'s fixed delta \n\
time, by temporarily speeding up playback. The meaning of this parameter is the length of these "faster" \n\
playback periods, which means that it must be larger than the fixed frame time to take effect but setting a \n\
large value results in long fast playback after a huge lag spike.'
PLAY_EVERY_FRAME_SETTING = f"/app/player/useFastMode"
PLAY_EVERY_FRAME_SETTING_DEFAULT = False
PLAY_EVERY_FRAME_TOOLTIP = "Only effective when Fixed Time Step is on. When it is on, no frames are skipped \n\
and in every frame time advances by the reciprocal of Timeline's frame rate (or TimeCodesPerSecond). Thus, \n\
simulation is usually faster than real-time and processing is only limited by the frame rate of the runloop. \n\
This is useful for recording."
TICKS_PER_FRAME_SETTING = f"/app/player/timelineSubsampleRate"
TICKS_PER_FRAME_SETTING_DEFAULT = 1
TICKS_PER_FRAME_SETTING_MIN = 1
TICKS_PER_FRAME_SETTING_MAX = 30
TICKS_PER_FRAME_TOOLTIP = "Steps per Frame, also known as Sub-Stepping, controls the oversampling rate of the timeline\n\
s, i.e. how many times updates are called (update events are dispatched) each frame."

SNAP_TO_FRAME_SETTING = f"{PERSISTENT_SETTINGS_PREFIX}/app/anim/snapToFrame"
SNAP_TO_FRAME_SETTING_DEFAULT = True

_g_settings = carb.settings.get_settings()


def build_playback_preferences(pref_builder: PreferenceBuilder):
    with ui.VStack():
        if _g_settings.get(USE_FIXED_TIME_STEPPING_SETTING) is None:
            _g_settings.set_default_bool(USE_FIXED_TIME_STEPPING_SETTING, USE_FIXED_TIME_STEPPING_SETTING_DEFAULT)
        pref_builder.create_setting_widget(
            "Fixed Time Step",
            USE_FIXED_TIME_STEPPING_SETTING,
            SettingType.BOOL,
            tooltip=USE_FIXED_TIME_STEPPING_TOOLTIP,
        )
        if _g_settings.get(PLAY_EVERY_FRAME_SETTING) is None:
            _g_settings.set_default_bool(PLAY_EVERY_FRAME_SETTING, PLAY_EVERY_FRAME_SETTING_DEFAULT)
        pref_builder.create_setting_widget(
            "Play Every Frame", PLAY_EVERY_FRAME_SETTING, SettingType.BOOL, tooltip=PLAY_EVERY_FRAME_TOOLTIP
        )
        if _g_settings.get(COMPENSATE_PLAY_DELAY_IN_SECS_SETTING) is None:
            _g_settings.set_default_float(
                COMPENSATE_PLAY_DELAY_IN_SECS_SETTING, COMPENSATE_PLAY_DELAY_IN_SECS_SETTING_DEFAULT
            )
        pref_builder.create_setting_widget(
            "Wall Clock Time Delay Compensation",
            COMPENSATE_PLAY_DELAY_IN_SECS_SETTING,
            SettingType.FLOAT,
            range_from=0,
            range_to=100,
            tooltip=COMPENSATE_PLAY_DELAY_IN_SECS_TOOLTIP,
        )
        if _g_settings.get(TICKS_PER_FRAME_SETTING) is None:
            _g_settings.set_default_int(TICKS_PER_FRAME_SETTING, TICKS_PER_FRAME_SETTING_DEFAULT)
        pref_builder.create_setting_widget(
            "Steps Per Frame",
            TICKS_PER_FRAME_SETTING,
            SettingType.INT,
            range_from=TICKS_PER_FRAME_SETTING_MIN,
            range_to=TICKS_PER_FRAME_SETTING_MAX,
            tooltip=TICKS_PER_FRAME_TOOLTIP,
        )
        if _g_settings.get(SNAP_TO_FRAME_SETTING) is None:
            _g_settings.set_default_bool(SNAP_TO_FRAME_SETTING, SNAP_TO_FRAME_SETTING_DEFAULT)
        pref_builder.create_setting_widget(
            "Snap Timeslider to Frame",
            SNAP_TO_FRAME_SETTING,
            SettingType.BOOL,
            tooltip="Always snap to whole frame at the moment",
        )


def get_use_fixed_time_stepping() -> bool:
    use_fixed_time_stepping = _g_settings.get_as_bool(USE_FIXED_TIME_STEPPING_SETTING)
    if use_fixed_time_stepping == None:
        # fallback to default if setting not found
        use_fixed_time_stepping = USE_FIXED_TIME_STEPPING_SETTING_DEFAULT

    return use_fixed_time_stepping


def set_use_fixed_time_stepping(value: bool):
    return _g_settings.set(USE_FIXED_TIME_STEPPING_SETTING, value)


def get_compensate_play_dely_in_secs() -> float:
    compensate_play_dely_in_secs = _g_settings.get_as_float(COMPENSATE_PLAY_DELAY_IN_SECS_SETTING)
    if compensate_play_dely_in_secs == None:
        # fallback to default if setting not found
        compensate_play_dely_in_secs = COMPENSATE_PLAY_DELAY_IN_SECS_SETTING_DEFAULT

    return compensate_play_dely_in_secs


def set_compensate_play_dely_in_secs(value: float):
    if value < 0:
        raise ValueError(f"Invalid Wall Clock Time Delay Compensation: {value}.")
    return _g_settings.set(COMPENSATE_PLAY_DELAY_IN_SECS_SETTING, value)


def get_snap_to_frame() -> bool:
    snap_to_frame = _g_settings.get_as_bool(SNAP_TO_FRAME_SETTING)
    if snap_to_frame == None:
        # fallback to default if setting not found
        snap_to_frame = SNAP_TO_FRAME_SETTING_DEFAULT

    return snap_to_frame


def set_snap_to_frame(value: bool):
    return _g_settings.set(SNAP_TO_FRAME_SETTING, value)


def get_play_every_frame() -> bool:
    play_every_frame = _g_settings.get_as_bool(PLAY_EVERY_FRAME_SETTING)
    if play_every_frame == None:
        # fallback to default if setting not found
        play_every_frame = PLAY_EVERY_FRAME_SETTING_DEFAULT

    return play_every_frame


def set_play_every_frame(value: bool):
    return _g_settings.set(PLAY_EVERY_FRAME_SETTING, value)


def get_ticks_per_frame() -> int:
    sub_stepping = _g_settings.get_as_int(TICKS_PER_FRAME_SETTING)
    if sub_stepping == None:
        # falback to default if setting is not recognized
        sub_stepping = TICKS_PER_FRAME_SETTING_DEFAULT
    return sub_stepping


def set_ticks_per_frame(value: int):
    if isinstance(value, int):
        if value < TICKS_PER_FRAME_SETTING_MIN or value > TICKS_PER_FRAME_SETTING_MAX:
            raise ValueError(f"Invalid Sub-Stepping value: {value}.")
        return _g_settings.set(TICKS_PER_FRAME_SETTING, value)
    else:
        raise ValueError(f"Invalid Sub-Stepping type: {value}.")
