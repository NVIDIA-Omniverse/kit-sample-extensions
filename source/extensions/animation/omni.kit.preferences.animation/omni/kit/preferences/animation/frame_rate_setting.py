import typing
from enum import Enum

import carb.settings
from omni.kit.window.preferences import PERSISTENT_SETTINGS_PREFIX

FRAME_RATE_SETTING = f"{PERSISTENT_SETTINGS_PREFIX}/app/stage/timeCodesPerSecond"


# Frame rate enum
class FrameRate(Enum):
    TWENTY_FOUR = 24
    TWENTY_NINE_POINT_NINE_SEVEN = 29.97
    THIRTY = 30
    SIXTY = 60
    ONE_HUNDRED_TWENTY = 120

    @classmethod
    def default(cls):
        return cls.THIRTY

    @classmethod
    def values(cls) -> typing.List[float]:
        return [item.value for item in cls]

    @classmethod
    def value_strs(cls) -> typing.List[str]:
        return [str(item.value) for item in cls]


def get_frame_rate() -> float:
    frame_rate = carb.settings.get_settings().get_as_float(FRAME_RATE_SETTING)
    if frame_rate == None:
        # fallback to default if setting not found
        frame_rate = FrameRate.default()
    elif frame_rate not in FrameRate.values():
        carb.log_warn(f"Saved Frame Rate setting invalid: {frame_rate}")
        # falback to default if setting is not recognized
        frame_rate = FrameRate.default()

    return frame_rate


def set_frame_rate(value: float):
    if value not in FrameRate.values():
        raise ValueError(f"Invalid frame rate value: {value}.")
    return carb.settings.get_settings().set(FRAME_RATE_SETTING, value)
