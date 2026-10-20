import math
import numbers
import weakref

import carb.settings
import omni.ext
import omni.kit.app
import omni.timeline
import omni.ui as ui
from pxr import Usd

from .utils import get_display_str, string_to_frame


class WeakMethod(weakref.WeakMethod):
    def __call__(self, *args, **kwargs):
        obj = weakref.ref.__call__(self)
        func = self._func_ref()
        if obj is None or func is None:
            return None
        return func(obj, *args, **kwargs)


class TimelineFPSModel(ui.AbstractValueModel):
    def __init__(self):
        super().__init__()
        self._timeline = omni.timeline.get_timeline_interface()
        self._value = self._timeline.get_time_codes_per_seconds()
        self._timeline_event_sub = self._timeline.get_timeline_event_stream().create_subscription_to_pop_by_type(
            omni.timeline.TimelineEventType.TIME_CODE_PER_SECOND_CHANGED, WeakMethod(self._on_timeline_event)
        )

    def __del__(self):
        self._timeline_event_sub = None
        self._timeline = None

    def _on_timeline_event(self, evt):
        self._value = self._timeline.get_time_codes_per_seconds()
        self._value_changed()

    def get_value_as_float(self):
        return self._value

    def get_value_as_string(self) -> str:
        return "{0:g}".format(self._value)

    def set_value(self, value):
        try:
            v = float(value)
        except ValueError:
            return

        self._value = v

    def begin_edit(self):
        pass

    def end_edit(self):
        self._value = min(max(self._value, 0.01), 999999)
        self._timeline.set_time_codes_per_second(self._value)


class TimelineValueModel(ui.AbstractValueModel):
    def __init__(self, event_type=omni.timeline.TimelineEventType.CURRENT_TIME_CHANGED):
        super().__init__()
        self._event_type = event_type
        self._timeline = omni.timeline.get_timeline_interface()
        self._settings = carb.settings.get_settings()

        # relam -- Finding a better home for this would remove another dependency
        self._timeline_event_sub = self._timeline.get_timeline_event_stream().create_subscription_to_pop(
            WeakMethod(self._on_timeline_event)
        )
        self._fps = self._timeline.get_time_codes_per_seconds()
        setters = {
            omni.timeline.TimelineEventType.START_TIME_CHANGED: self._timeline.set_start_time,
            omni.timeline.TimelineEventType.END_TIME_CHANGED: self._timeline.set_end_time,
            omni.timeline.TimelineEventType.CURRENT_TIME_CHANGED: self._timeline.set_current_time,
        }
        getters = {
            omni.timeline.TimelineEventType.START_TIME_CHANGED: self._timeline.get_start_time,
            omni.timeline.TimelineEventType.END_TIME_CHANGED: self._timeline.get_end_time,
            omni.timeline.TimelineEventType.CURRENT_TIME_CHANGED: self._timeline.get_tentative_time,
        }
        start_guard = lambda value: min(value, self._timeline.get_end_time() * self._fps - 1)
        end_guard = lambda value: max(self._timeline.get_start_time() * self._fps + 1, value)
        guards = {
            omni.timeline.TimelineEventType.START_TIME_CHANGED: start_guard,
            omni.timeline.TimelineEventType.END_TIME_CHANGED: end_guard,
            omni.timeline.TimelineEventType.CURRENT_TIME_CHANGED: lambda value: value,
        }
        self._getter = getters.get(self._event_type)
        self._setter = setters.get(self._event_type)
        self._value_guard = guards.get(self._event_type)
        self._time_value = self.get_value_as_float()
        self._last_value = self._time_value

    def __del__(self):
        self._timeline_event_sub = None
        self._timeline = None
        self._settings = None

    def _on_timeline_event(self, evt):
        this_type = int(self._event_type)
        if evt.type == this_type:
            self._value_changed()
        elif evt.type == int(omni.timeline.TimelineEventType.TIME_CODE_PER_SECOND_CHANGED):
            self._fps = self._timeline.get_time_codes_per_seconds()
            self._value_changed()
        elif self._event_type == omni.timeline.TimelineEventType.CURRENT_TIME_CHANGED:
            if (
                (evt.type == int(omni.timeline.TimelineEventType.CURRENT_TIME_CHANGED))
                or (evt.type == int(omni.timeline.TimelineEventType.CURRENT_TIME_TICKED))
                or (evt.type == int(omni.timeline.TimelineEventType.STOP))
            ):
                self._value_changed()

    def get_value_as_string(self) -> str:
        if not self._getter:
            return
        return get_display_str(self._fps, self._getter() * self._fps)

    def get_value_as_float(self):
        if not self._getter:
            return
        return self._getter() * self._fps

    def begin_edit(self):
        self._last_value = self._time_value

    def filter_value(self, value):
        if value is None:
            return math.nan
        elif isinstance(value, Usd.TimeCode):
            return value.GetValue()
        elif isinstance(value, str):
            fps = self._timeline.get_time_codes_per_seconds()
            return string_to_frame(fps, value)
        elif isinstance(value, numbers.Real):
            return value

    def set_value(self, value):
        filtered_value = self.filter_value(value)
        if filtered_value is None:
            return

        filtered_value = self._value_guard(filtered_value)
        if filtered_value == self._time_value:
            return

        self._time_value = filtered_value

    def end_edit(self):
        if not self._setter:
            return
        if math.isclose(self._fps, 0, abs_tol=0):
            return
        if self._last_value == self._time_value:
            return

        self._setter(self._time_value / self._fps)
        self._value_changed()


# copy from sequencer
class TimeCodeModel(ui.AbstractValueModel):
    """An model for storing UsdTimeCode value.
    Can view in seconds, smpte, or timecodes (frames)
    Internal value is always stored as float i.e. (Usd.TimeCodes)."""

    def __init__(self, second, *args, **kwargs):
        self._timeline = omni.timeline.get_timeline_interface()
        fps = self._timeline.get_time_codes_per_seconds()
        frame = round(second * fps)
        filtered_value = self.filter_value(frame)
        if filtered_value is None:
            raise ValueError(f"Value not valid: {frame}")
        self._value = filtered_value
        self._previous_value = None
        self._editing = False

        self._settings = carb.settings.get_settings()
        super().__init__(*args, **kwargs)

    def __repr__(self) -> str:
        return f"<TimeCode({self._value})>"

    @property
    def is_editing(self):
        return self._editing

    def begin_edit(self) -> None:
        self._previous_value = self._value
        self._editing = True
        super().begin_edit()

    def end_edit(self) -> None:
        self._editing = False
        super().end_edit()

    def filter_value(self, value):
        if value is None:
            return math.nan
        elif isinstance(value, Usd.TimeCode):
            return value.GetValue()
        elif isinstance(value, str):
            fps = self._timeline.get_time_codes_per_seconds()
            return string_to_frame(fps, value)
        elif isinstance(value, numbers.Real):
            return value

    @property
    def previous_value(self):
        return self._previous_value

    @property
    def is_valid(self):
        return self.filter_value(self._value) is not None

    def set_value(self, value):
        filtered_value = self.filter_value(value)
        if filtered_value is None or filtered_value == self._value:
            return
        self._value = filtered_value
        self._value_changed()

    def get_value_as_float(self) -> float:
        return self._value

    def get_value_as_string(self):
        """Reimplemented get string"""
        # This string goes to the field.
        # Value is always in timecodes - convert as appropriate for display
        fps = self._timeline.get_time_codes_per_seconds()
        return get_display_str(fps, self.as_float)
