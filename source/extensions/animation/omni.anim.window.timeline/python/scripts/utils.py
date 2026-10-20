from __future__ import annotations

import math
import typing
from enum import Enum
from os import path

import carb
import omni.kit.commands
import omni.kit.notification_manager as nm
from pxr import Usd, UsdGeom

EXT_ICON_PATH = ""

TIME_DISPLAY_SETTING = f"/persistent/app/anim/timeDisplay"
AUTO_KEY_ALL_XFORM_SETTING = f"/persistent/app/anim/autoKeyAllXform"
COMPENSATE_PLAY_DELAY_IN_SECS_SETTING = f"/app/player/CompensatePlayDelayInSecs"
SNAP_TO_FRAME_SETTING = f"/persistent/app/anim/snapToFrame"
SUB_STEPPING_SETTING_MIN = 1
SUB_STEPPING_SETTING_MAX = 30


# copy from omni.kit.preferences.animation
class TimeDisplay(str, Enum):
    """Time Display enum.
    Timecode is a synonym for 'SMPTE' and has the same enum value.
    This is on purpose to avoid confustion with USD Timecodes.
    """

    FRAMES = "frames"
    SECONDS = "seconds"
    SMPTE = "smpte"
    TIMECODE = "smpte"

    @classmethod
    def default(cls):
        return cls.FRAMES

    def __str__(self) -> str:
        return self.value

    @classmethod
    def values(cls) -> typing.List[str]:
        return [item.value for item in cls]

    @staticmethod
    def from_string(value: str) -> TimeDisplay:
        value = str(value).lower()
        for item in TimeDisplay:
            if item.value == value:
                return item
        raise ValueError(f"Invalid string: {value}. Valid strings: {(item for item in TimeDisplay)}")


def init_icon_path(ext_path):
    icons_subpath = path.join("data", "icons")
    global EXT_ICON_PATH
    EXT_ICON_PATH = path.join(ext_path, icons_subpath)


def get_icon_path(filename):
    global EXT_ICON_PATH
    return path.join(EXT_ICON_PATH, filename)


def get_display_str(fps, frames) -> str:
    if math.isclose(fps, 0, abs_tol=0):
        return "0"
    format = get_time_display()
    if format == TimeDisplay.FRAMES:
        if math.isnan(frames):
            return ""
        rounded = round(frames)
        if math.isclose(frames, rounded, abs_tol=0):
            return f"{rounded}"
        return f"{frames:.2f}"
    elif format == TimeDisplay.SMPTE:
        abs_frames = abs(frames)
        second = int(abs_frames / fps)
        sign = "" if frames >= 0 else "-"
        return "{0}{1:02d}:{2:02d}:{3:02d}:{4:02d}".format(
            sign, int(second // 3600), int(second // 60 % 60), int(second % 60), int(abs_frames % fps)
        )
    elif format == TimeDisplay.SECONDS:
        sec = frames / fps
        return f"{sec:.2f}"
    else:
        return f"{frames:.2f}"


def string_to_frame(fps: float, display_value: str):
    # TODO: convert SMPTE to time - for now just convert string to float
    try:
        value = float(display_value)
        format = get_time_display()
        if format == TimeDisplay.SECONDS:
            value = value * fps
        return value

    except ValueError:
        return None


def add_xform_keys(prim_paths: list, stage, time: Usd.TimeCode = None):
    if prim_paths is None or len(prim_paths) == 0:
        message = "Please select xformable prims(objects) before adding animation keys."
        nm.post_notification(
            message,
            hide_after_timeout=True,
            duration=2,
            status=nm.NotificationStatus.WARNING,
        )
        carb.log_info(message)
        return
    keyable_xform_attr_names = [
        "xformOp:translate",
        "xformOp:rotateX",
        "xformOp:rotateY",
        "xformOp:rotateZ",
        "xformOp:rotateXYZ",
        "xformOp:rotateXZY",
        "xformOp:rotateYXZ",
        "xformOp:rotateYZX",
        "xformOp:rotateZXY",
        "xformOp:rotateZYX",
        "xformOp:scale",
        "visibility",
    ]
    curve_names = []
    for prim_path in prim_paths:
        if path is not None:
            prim = stage.GetPrimAtPath(prim_path)
            if prim and prim.IsA(UsdGeom.Xformable):
                for attr_name in keyable_xform_attr_names:
                    attr = prim.GetAttribute(attr_name)
                    if attr:
                        curve_names.append(attr.GetPath().pathString)
    if len(curve_names) > 0:
        omni.kit.commands.execute("SetAnimCurveKeys", paths=curve_names, time=time)
    else:
        message = "There is no suitable xformable attribute to author keys."
        nm.post_notification(
            message,
            hide_after_timeout=True,
            duration=2,
            status=nm.NotificationStatus.INFO,
        )
        carb.log_info(message)
        return


def remove_all_keys(prim_paths: list, stage: Usd.Stage, start_time: Usd.TimeCode = None, end_time: Usd.TimeCode = None):
    if prim_paths is None or len(prim_paths) == 0:
        message = "Please select xformable prims(objects) before remove animation keys."
        nm.post_notification(
            message,
            hide_after_timeout=True,
            duration=2,
            status=nm.NotificationStatus.WARNING,
        )
        carb.log_info(message)
        return

    if start_time is None or end_time is None:
        omni.kit.commands.execute("RemoveAnimCurveKeys", stage=stage, paths=prim_paths)
        return

    omni.kit.undo.begin_group()
    curve_plugin = omni.anim.curve.core.acquire_interface()
    for prim_path in prim_paths:
        prim = stage.GetPrimAtPath(prim_path)
        curves = curve_plugin.get_curves(str(prim.GetPath()))

        ticks_per_sec = curve_plugin.get_ticks_per_second()
        time_codes_per_sec = stage.GetTimeCodesPerSecond()

        start = start_time.GetValue() / time_codes_per_sec * ticks_per_sec
        end = end_time.GetValue() / time_codes_per_sec * ticks_per_sec

        times = set()

        for name, curve in curves.items():
            for key in curve.keys:
                if key.time >= start and key.time <= end:
                    times.add(key.time)

        if not times:
            continue

        for key_time in times:
            omni.kit.commands.execute(
                "RemoveAnimCurveKeys",
                stage=stage,
                paths=[prim_path],
                time=Usd.TimeCode(key_time / ticks_per_sec * time_codes_per_sec),
            )
    omni.kit.undo.end_group()


def get_auto_key_all_xform() -> bool:
    settings = carb.settings.get_settings()
    return settings.get_as_bool(AUTO_KEY_ALL_XFORM_SETTING)


def set_auto_key_all_xform(value: bool):
    settings = carb.settings.get_settings()
    return settings.set(AUTO_KEY_ALL_XFORM_SETTING, value)


def get_time_display() -> str:
    settings = carb.settings.get_settings()
    time_display = settings.get_as_string(TIME_DISPLAY_SETTING)
    return time_display.lower()


def set_time_display(value: str):
    settings = carb.settings.get_settings()
    time_display = str(value).lower()
    return settings.set_string(TIME_DISPLAY_SETTING, time_display)


def get_compensate_play_delay_in_secs() -> float:
    settings = carb.settings.get_settings()
    compensate_play_delay_in_secs = settings.get_as_float(COMPENSATE_PLAY_DELAY_IN_SECS_SETTING)
    return compensate_play_delay_in_secs


def set_compensate_play_delay_in_secs(value: float):
    settings = carb.settings.get_settings()
    value = max(0, value)
    return settings.set(COMPENSATE_PLAY_DELAY_IN_SECS_SETTING, value)


def get_snap_to_frame() -> bool:
    settings = carb.settings.get_settings()
    snap_to_frame = settings.get_as_bool(SNAP_TO_FRAME_SETTING)
    return snap_to_frame


def set_snap_to_frame(value: bool):
    settings = carb.settings.get_settings()
    return settings.set(SNAP_TO_FRAME_SETTING, value)


def snap_to_frame(value: float):
    if get_snap_to_frame():
        return round(value)
    return value
