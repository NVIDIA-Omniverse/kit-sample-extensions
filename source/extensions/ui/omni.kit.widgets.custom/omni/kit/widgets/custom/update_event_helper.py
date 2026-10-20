# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
from typing import Callable

import carb
import carb.events
import omni.kit.app

DEBUG_MODE = False


def dbg_print(*args):
    if DEBUG_MODE:
        print(*args)


class UpdateEventHelper:
    __singleton = None

    def __init__(self):
        self._update_applicants = {}
        self._update_sub = None

    @staticmethod
    def create():
        if not UpdateEventHelper.__singleton:
            UpdateEventHelper.__singleton = UpdateEventHelper()
        return UpdateEventHelper.__singleton

    @staticmethod
    def get_instance():
        return UpdateEventHelper.__singleton

    def release(self):
        UpdateEventHelper.__singleton = None

    def register_update(self, applicant):
        dbg_print(f"{self} Enter register_update, applicant:{applicant}")

        if applicant in self._update_applicants:
            self._update_applicants[applicant] = self._update_applicants[applicant] + 1
        else:
            if len(self._update_applicants) == 0:
                # First register:
                assert self._update_sub is None
                app = omni.kit.app.get_app()
                if not app:
                    carb.log_error("Can not get current APP!")
                    return
                self._update_sub = carb.eventdispatcher.get_eventdispatcher().observe_event(
                    observer_name="omni.kit.widgets.custom.UpdateEventHelper",
                    event_name=omni.kit.app.GLOBAL_EVENT_UPDATE,
                    on_event=self._on_update,
                )
            self._update_applicants[applicant] = 1

    def deregister_update(self, applicant):
        dbg_print(f"{self} Enter deregister_update, applicant:{applicant}")
        if applicant not in self._update_applicants:
            return
        register_count = self._update_applicants[applicant]
        if register_count > 1:
            self._update_applicants[applicant] = register_count - 1
        else:
            self._update_applicants.pop(applicant)
            if len(self._update_applicants) == 0:
                dbg_print("on_update end")
                assert self._update_sub is not None
                self._update_sub = None

    def __del__(self):
        self._update_sub = None

    def _on_update(self, event: carb.eventdispatcher.Event):
        dt = event["dt"]
        applicants = [*self._update_applicants]
        for applicant in applicants:
            need_more = applicant.on_update(dt)
            if need_more is not None:
                if not need_more:
                    self.deregister_update(applicant)


class DelayExecutor:
    def __init__(self, callback: callable, description, max_retry_count=1):
        self._callback = callback
        self._desc = description
        self._max_retry_count = max_retry_count
        self._retry_count = 0
        self._finished = False

        event_helper = UpdateEventHelper.get_instance()
        event_helper.register_update(self)

    def deregister(self):
        UpdateEventHelper.get_instance().deregister_update(self)

    def on_update(self, dt):
        if self._finished or self._retry_count >= self._max_retry_count:
            # Done or failed, cleanup
            if not self._finished:
                carb.log_error(f"Delay Executor: '{self._desc}' failed")
            return False
        elif self._delay_expired(dt):
            self._retry_count += 1
            self._finished = self._callback()

        return True

    def _delay_expired(self, dt):
        return True


class DelayTimeExecutor(DelayExecutor):
    def __init__(self, milliseconds, callback: callable, description, max_retry_count=1):
        self._milliseconds = milliseconds
        super().__init__(callback, description, max_retry_count)

    def _delay_expired(self, dt):
        if self._milliseconds > 0:
            self._milliseconds -= dt * 1000
        return self._milliseconds <= 0


class DelayFrameExecutor(DelayExecutor):
    def __init__(self, frame_count, callback: callable, description, max_retry_count=1):
        self._frame_count = frame_count
        super().__init__(callback, description, max_retry_count)

    def _delay_expired(self, dt):
        if self._frame_count > 0:
            self._frame_count -= 1
        return self._frame_count <= 0


def delay_execute_by_frame(frame_count, callback: callable, description, max_retry_count=1):
    return DelayFrameExecutor(frame_count, callback, description, max_retry_count)


def delay_execute_by_milliseconds(milliseconds, callback: callable, description, max_retry_count=1):
    return DelayTimeExecutor(milliseconds, callback, description, max_retry_count)


class Timer:
    def __init__(self, interval: float, on_timer_fn: Callable[[None], bool], start=False):
        """
        A timer class.
        Args:
            interval (float): Timer interval, in seconds.
            on_timer_fn (callable): Callback when timer tiggered. Return True to trigger again. Return False to stop timer.
        Kwargs:
            start (bool): Auto start if True.
        """
        self._interval = interval if interval > 0 else 0.1
        self._on_timer_fn = on_timer_fn

        self._action_time = 0.0
        self._current_time = 0.0
        self._running = False
        self._paused = False

        if start:
            self.start()

    def __del__(self):
        self.stop()

    @property
    def running(self):
        return self._running

    @property
    def interval(self):
        return self._interval

    @interval.setter
    def interval(self, value):
        self._interval = value if value > 0 else 0.1

    def on_update(self, dt):
        if self._paused:
            return

        self._current_time += dt
        if self._current_time - self._action_time >= self._interval:
            if self._on_timer_fn:
                run_again = self._on_timer_fn()
                if run_again is not None and not run_again:
                    # update event will be deregister if return False
                    # only set flag here
                    self._running = False
                    return False
            self._action_time = self._current_time
        return True

    def start(self):
        self._running = True
        UpdateEventHelper.get_instance().register_update(self)

    def stop(self):
        if self._running:
            UpdateEventHelper.get_instance().deregister_update(self)
            self._running = False

    def pause(self) -> None:
        self._paused = True

    def resume(self) -> None:
        self._paused = False
