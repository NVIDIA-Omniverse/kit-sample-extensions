import typing

import carb
import carb.settings
import omni.kit.app
from omni import ui
from omni.kit.window.preferences import PERSISTENT_SETTINGS_PREFIX, PreferenceBuilder, SettingType

from .frame_rate_setting import FRAME_RATE_SETTING, FrameRate
from .time_display import TimeDisplay

TIME_SETTINGS_TITLE = "Time Settings"
TIME_DISPLAY_SETTING = f"{PERSISTENT_SETTINGS_PREFIX}/app/anim/timeDisplay"
TIME_CODE_RANGE_SETTING = f"{PERSISTENT_SETTINGS_PREFIX}/app/stage/timeCodeRange"
TIME_CODE_RANGE_SETTING_DEFAULT = [0.0, 100.0]
SNAP_TO_FRAME_SETTING = f"{PERSISTENT_SETTINGS_PREFIX}/app/anim/snapToFrame"
SNAP_TO_FRAME_SETTING_DEFAULT = True
SUB_STEPPING_SETTING_MIN = 1
SUB_STEPPING_SETTING_MAX = 30

_g_settings = carb.settings.get_settings()


class EditScope:
    """The class to avoid circular event calling"""

    def __init__(self):
        self.active = False

    def __enter__(self):
        self.active = True

    def __exit__(self, type, value, traceback):
        self.active = False

    def __bool__(self):
        return self.active


class TimeDisplaySettingModel(ui.SimpleStringModel):
    """A string value model for TimeDisplay.
    If default value is empty string or unspecified, changes to time display setting will update this model."""

    def __init__(self, default_value: str = "") -> None:
        if not default_value:
            self._time_setting_sub = omni.kit.app.SettingChangeSubscription(
                TIME_DISPLAY_SETTING, on_change=self._on_time_display_settings_change
            )
        default_value = default_value or get_time_display()
        self._edit_scope = EditScope()
        super().__init__(default_value)

    def _on_time_display_settings_change(self, value, event_type: carb.settings.ChangeEventType):
        time_display = get_time_display()
        if time_display == self.as_string:
            return
        self.as_string = time_display

    def set_value(self, value):
        if self._edit_scope:
            return

        if value not in TimeDisplay.values():
            raise ValueError(f"Time display value invalid: {value}")

        with self._edit_scope:
            set_time_display(value)
            super().set_value(value)


def build_time_preferences(pref_builder: PreferenceBuilder):
    with ui.VStack():
        pref_builder.create_setting_widget_combo("Display Time As", TIME_DISPLAY_SETTING, TimeDisplay.values())

        # if _g_settings.get(TIME_CODE_RANGE_SETTING) is None:
        #     _g_settings.set_float_array(TIME_CODE_RANGE_SETTING, TIME_CODE_RANGE_SETTING_DEFAULT)
        # pref_builder.create_setting_widget("Default Frame Range", TIME_CODE_RANGE_SETTING, SettingType.DOUBLE2, tooltip="The default start & end frame range when we create a new stage.")


def get_time_display() -> str:
    time_display = _g_settings.get_as_string(TIME_DISPLAY_SETTING)
    if not time_display:
        return TimeDisplay.default()
    time_display = time_display.lower()
    if time_display not in TimeDisplay.values():
        carb.log_warn(f"Saved Time Display setting invalid: {time_display}")
        return TimeDisplay.default()
    return time_display


def set_time_display(value: typing.Union[str, TimeDisplay]):
    time_display = str(value).lower()
    if time_display not in TimeDisplay.values():
        raise ValueError(f"Invalid time display value: {value}.")
    return _g_settings.set_string(TIME_DISPLAY_SETTING, time_display)


g_time_display_model = TimeDisplaySettingModel()


def get_time_code_range():
    time_code_range = _g_settings.get(TIME_CODE_RANGE_SETTING)
    # temptest. see type. should be float_array
    if time_code_range == None:
        # fallback to default if setting not found
        time_code_range = TIME_CODE_RANGE_SETTING_DEFAULT

    return time_code_range


def set_time_code_range(range_min: float, range_max: float):
    return _g_settings.set_float_array(TIME_CODE_RANGE_SETTING, [range_min, range_max])
