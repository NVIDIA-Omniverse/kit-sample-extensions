# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
import math

import omni.ext
import omni.kit.app
import omni.timeline
import omni.ui as ui
from carb.eventdispatcher import get_eventdispatcher
from omni.timeline import TimelineEventType


class TimelineLoopModel(ui.AbstractValueModel):
    def __init__(self):
        super().__init__()
        self._timeline = omni.timeline.get_timeline_interface()
        self._timeline_sub = get_eventdispatcher().observe_event(
            observer_name="omni.kit.timeline.minibar:TimelineLoopModel",
            event_name=omni.timeline.GLOBAL_EVENT_LOOP_MODE_CHANGED,
            on_event=lambda _: self._value_changed(),
        )

    def __del__(self):  # pragma: no cover
        self.destroy()

    def destroy(self):  # pragma: no cover
        self._timeline_sub = None
        self._timeline = None

    def get_value_as_bool(self):
        return self._timeline.is_looping()

    def set_value(self, value: bool):
        self._timeline.set_looping(value)


class TimelinePlayModel(ui.AbstractValueModel):
    def __init__(self):
        super().__init__()
        self._timeline = omni.timeline.get_timeline_interface()
        self._timeline_subs = [
            get_eventdispatcher().observe_event(
                observer_name="omni.kit.timeline.minibar:TimelinePlayModel",
                event_name=event_name,
                on_event=lambda _: self._value_changed(),
            )
            for event_name in (
                omni.timeline.GLOBAL_EVENT_PLAY,
                omni.timeline.GLOBAL_EVENT_STOP,
                omni.timeline.GLOBAL_EVENT_PAUSE,
            )
        ]

    def __del__(self):  # pragma: no cover
        self.destroy()

    def destroy(self):  # pragma: no cover
        self._timeline_subs.clear()
        self._timeline = None

    def get_value_as_bool(self):
        return self._timeline.is_playing()

    def set_value(self, value: bool):
        if value:
            self._timeline.play()
        else:
            self._timeline.pause()


class TimelineStartModel(ui.AbstractValueModel):
    def __init__(self):
        super().__init__()
        self._timeline = omni.timeline.get_timeline_interface()
        self._timeline_subs = [
            get_eventdispatcher().observe_event(
                observer_name="omni.kit.timeline.minibar:TimelineStartModel",
                event_name=event_name,
                on_event=lambda _: self._value_changed(),
            )
            for event_name in (
                omni.timeline.GLOBAL_EVENT_START_TIME_CHANGED,
                omni.timeline.GLOBAL_EVENT_TIME_CODE_PER_SECOND_CHANGED,
            )
        ]
        self._on_editing = False
        self._edit_value = 0

    def __del__(self):  # pragma: no cover
        self.destroy()

    def destroy(self):  # pragma: no cover
        self._timeline_subs.clear()
        self._timeline = None

    def get_value_as_int(self):
        tps = self._timeline.get_time_codes_per_seconds()
        return round(self._timeline.get_start_time() * tps)

    def set_value(self, value: int):
        if self._on_editing:
            self._edit_value = value
            return

        try:
            v = int(value)
        except ValueError:
            return

        tps = self._timeline.get_time_codes_per_seconds()
        if math.isclose(tps, 0):
            return

        v = min(self._timeline.get_end_time() * tps - 1, v)
        self._timeline.set_start_time(v / tps)

    def begin_edit(self) -> None:
        self._on_editing = True

    def end_edit(self) -> None:
        super().end_edit()
        self._on_editing = False
        self.set_value(self._edit_value)


class TimelineEndModel(ui.AbstractValueModel):
    def __init__(self):
        super().__init__()
        self._timeline = omni.timeline.get_timeline_interface()
        self._timeline_subs = [
            get_eventdispatcher().observe_event(
                observer_name="omni.kit.timeline.minibar:TimelineEndModel",
                event_name=event_name,
                on_event=lambda _: self._value_changed(),
            )
            for event_name in (
                omni.timeline.GLOBAL_EVENT_END_TIME_CHANGED,
                omni.timeline.GLOBAL_EVENT_TIME_CODE_PER_SECOND_CHANGED,
            )
        ]
        self._on_editing = False
        self._edit_value = 0

    def __del__(self):  # pragma: no cover
        self.destroy()

    def destroy(self):  # pragma: no cover
        self._timeline_subs.clear()
        self._timeline = None

    def get_value_as_int(self):
        tps = self._timeline.get_time_codes_per_seconds()
        return round(self._timeline.get_end_time() * tps)

    def set_value(self, value):
        if self._on_editing:
            self._edit_value = value
            return

        try:
            v = int(value)
        except ValueError:
            return

        tps = self._timeline.get_time_codes_per_seconds()
        if math.isclose(tps, 0):
            return
        v = max(self._timeline.get_start_time() * tps + 1, v)

        self._timeline.set_end_time(v / tps)

    def begin_edit(self) -> None:
        self._on_editing = True

    def end_edit(self) -> None:
        super().end_edit()
        self._on_editing = False
        self.set_value(self._edit_value)


class TimelineCurrentModel(ui.AbstractValueModel):
    def __init__(self):
        super().__init__()
        self._timeline = omni.timeline.get_timeline_interface()
        # Note: CURRENT_TIME_CHANGED is deprecated and no longer dispatched
        self._timeline_subs = [
            get_eventdispatcher().observe_event(
                observer_name="omni.kit.timeline.minibar:TimelineCurrentModel",
                event_name=event_name,
                on_event=lambda _: self._value_changed(),
            )
            for event_name in (
                omni.timeline.GLOBAL_EVENT_STOP,
                omni.timeline.GLOBAL_EVENT_CURRENT_TIME_TICKED,
                omni.timeline.GLOBAL_EVENT_TIME_CODE_PER_SECOND_CHANGED,
            )
        ]

    def __del__(self):  # pragma: no cover
        self.destroy()

    def destroy(self):  # pragma: no cover
        self._timeline_subs.clear()
        self._timeline = None

    def get_value_as_int(self):
        tps = self._timeline.get_time_codes_per_seconds()
        return round(self._timeline.get_current_time() * tps)

    def set_value(self, value: int):
        try:
            v = int(value)
        except ValueError:
            return

        tps = self._timeline.get_time_codes_per_seconds()
        if math.isclose(tps, 0):
            return

        self._timeline.set_current_time(v / tps)

    def begin_edit(self) -> None:
        pass
