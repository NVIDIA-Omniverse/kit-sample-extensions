import math

import carb
import omni.ext
import omni.timeline
from omni import ui

from .timeline_value_model import TimelineValueModel


class TimelineTimeKeyItem(ui.AbstractItem):
    def __init__(self, name, key_id, time):
        super().__init__()
        self._name = name
        self._key_id = key_id
        self._time = ui.SimpleFloatModel(time)


class TimelineRootItem(ui.AbstractItem):
    def __init__(self, timeline_key_items):
        super().__init__()
        self.children = [TimelineTimeKeyItem(name, keys) for name, keys in timeline_key_items.items()]
        self.begin_time_model = TimelineValueModel(omni.timeline.TimelineEventType.START_TIME_CHANGED)
        self.end_time_model = TimelineValueModel(omni.timeline.TimelineEventType.END_TIME_CHANGED)
        self.current_time_model = TimelineValueModel(omni.timeline.TimelineEventType.CURRENT_TIME_CHANGED)

    def update_filter(self, text):
        for c in self.children:
            c.update_filter(text)

    def get_children(self):
        return [c for c in self.children if len(c.children) != 0]


class TimelineTimeModel(ui.AbstractItemModel):
    def __init__(self, timeline_items):
        super().__init__()
        self._root = TimelineRootItem(timeline_items)
        self._filter_text = ""

    def get_time_item(self):
        return self._root
