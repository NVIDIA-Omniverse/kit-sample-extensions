import omni.ext
import omni.kit.app
import omni.timeline
from omni import ui

from .ui_helpers import WeakMethod

# Lazy-initialized timeline interface and dispatch tables. They are populated on
# first use rather than at module import time because the underlying C++ plugin
# is not guaranteed to be available when this module is imported (e.g. during
# extension cold-start or test discovery). Accessing attributes on a None
# interface at import time used to raise AttributeError and break the import
# of the whole extension.
_timeline = None
_setters = None
_getters = None


def _get_timeline():
    global _timeline, _setters, _getters
    if _timeline is None:
        timeline = omni.timeline.get_timeline_interface()
        if timeline is None:
            raise RuntimeError(
                "omni.timeline.get_timeline_interface() returned None; the timeline " "plugin is not loaded yet."
            )
        setters = {
            omni.timeline.TimelineEventType.START_TIME_CHANGED: timeline.set_start_time,
            omni.timeline.TimelineEventType.END_TIME_CHANGED: timeline.set_end_time,
            omni.timeline.TimelineEventType.CURRENT_TIME_CHANGED: timeline.set_current_time,
        }
        getters = {
            omni.timeline.TimelineEventType.START_TIME_CHANGED: timeline.get_start_time,
            omni.timeline.TimelineEventType.END_TIME_CHANGED: timeline.get_end_time,
            omni.timeline.TimelineEventType.CURRENT_TIME_CHANGED: timeline.get_current_time,
        }
        # Publish atomically so concurrent callers never observe a
        # half-initialized cache where `_timeline` is set but `_setters` /
        # `_getters` are still `None`.
        _setters = setters
        _getters = getters
        _timeline = timeline
    return _timeline, _setters, _getters


class TimelineValueModel(ui.AbstractValueModel):
    def __init__(self, event_type=omni.timeline.TimelineEventType.END_TIME_CHANGED):
        super().__init__()
        self._event_type = event_type

        timeline, setters, getters = _get_timeline()

        # relam -- Finding a better home for this would remove another dependency
        self._timeline_event_sub = timeline.get_timeline_event_stream().create_subscription_to_pop(
            WeakMethod(self._on_timeline_event)
        )
        self._time_codes = timeline.get_time_codes_per_seconds()
        self._getter = getters.get(self._event_type)
        self._setter = setters.get(self._event_type)
        if self._getter is None or self._setter is None:
            raise ValueError(
                f"Unsupported timeline event_type: {self._event_type!r}; " f"expected one of {list(getters.keys())}"
            )
        self._time_value = self._getter()
        self._new_time_value = None

    def __del__(self):
        self._timeline_event_sub = None
        self._timeline = None

    def _on_timeline_event(self, evt):
        this_type = int(self._event_type)
        if evt.type == this_type:
            self._time_value = self._getter()
            self._value_changed()
        elif evt.type == int(omni.timeline.TimelineEventType.TIME_CODE_PER_SECOND_CHANGED):
            timeline, _, _ = _get_timeline()
            self._time_codes = timeline.get_time_codes_per_seconds()
            self._value_changed()
        elif self._event_type == omni.timeline.TimelineEventType.CURRENT_TIME_CHANGED:
            if (
                (evt.type == int(omni.timeline.TimelineEventType.CURRENT_TIME_CHANGED))
                or (evt.type == int(omni.timeline.TimelineEventType.CURRENT_TIME_TICKED))
                or (evt.type == int(omni.timeline.TimelineEventType.STOP))
            ):
                self._value_changed()

    def get_value_as_string(self):
        if self._time_value is None:
            return
        return str("{:.0f}".format(self._time_value * self._time_codes))

    def get_value_as_float(self):
        if self._time_value is None:
            return
        return self._time_value * self._time_codes

    def begin_edit(self):
        pass

    def set_value(self, value):
        try:
            v = float(value)
            self._new_time_value = v
        except ValueError:
            self._new_time_value = None

    def end_edit(self):
        if self._new_time_value is None:
            return
        if self._new_time_value == self._time_value:
            return
        if not self._setter:
            return

        clamped_value = min(max(self._new_time_value, 0), 999999)
        self._time_value = clamped_value / self._time_codes

        # set time in kit
        self._setter(self._time_value)
        # tell listeners value has changed
        self._value_changed()
        self._new_time_value = None
