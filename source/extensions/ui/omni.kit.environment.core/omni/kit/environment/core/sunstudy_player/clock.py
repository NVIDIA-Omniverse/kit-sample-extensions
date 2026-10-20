# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
from typing import Tuple

from omni import ui

from ..style import CLOCK_STYLES


class Spinner:
    REPEAT_DELAY = 0.500
    REPEAT_INTERVAL = 0.300

    def __init__(self, width, height, on_spin_fn, with_up=True, with_down=True, repeat=True):
        self._on_spin_fn = on_spin_fn
        self._repeat = repeat

        self._cur_time = 0.0
        self._action_time = 0.0
        # 1: Up pressed, 0: None, -1: Down pressed
        self._repeat_step = 0

        padding_x = width // 6
        padding_y = height // 9

        with ui.ZStack(width=width, height=height):
            with ui.Placer(offset_x=padding_x, offset_y=padding_y):
                self._spin_up = ui.Triangle(
                    width=padding_x * 4,
                    height=padding_y * 3,
                    alignment=ui.Alignment.CENTER_TOP,
                    mouse_pressed_fn=(lambda x, y, key, m: self._on_spin_clicked(key, 1)),
                    mouse_released_fn=(lambda x, y, key, m: self._on_spin_released(key)),
                    visible=with_up,
                    opaque_for_mouse_events=True,
                    style_type_name_override="Spinner",
                )
            with ui.Placer(offset_x=padding_x, offset_y=padding_y * 5):
                self._spin_down = ui.Triangle(
                    width=padding_x * 4,
                    height=padding_y * 3,
                    alignment=ui.Alignment.CENTER_BOTTOM,
                    mouse_pressed_fn=lambda x, y, key, m: self._on_spin_clicked(key, -1),
                    mouse_released_fn=(lambda x, y, key, m: self._on_spin_released(key)),
                    visible=with_down,
                    opaque_for_mouse_events=True,
                    style_type_name_override="Spinner",
                )

    def on_update(self, dt):
        self._cur_time += dt

        if not self._repeat or self._repeat_step == 0:
            return

        if self._cur_time > self._action_time:
            self._on_spin_fn(self._repeat_step)
            self._action_time += self.REPEAT_INTERVAL

    def _on_spin_clicked(self, key, step):
        # We only respond to left button
        if key != 0:
            return

        self._action_time = self._cur_time + self.REPEAT_DELAY
        self._repeat_step = step
        self._on_spin_fn(step)

    def _on_spin_released(self, key):
        if key != 0:
            return
        self._repeat_step = 0


class Number:
    def __init__(self):
        self._value = 0
        self._label = ui.Label("0", style_type_name_override="Number")

    def set_value(self, value, force=False):
        if value < 0:
            value = 0
        elif value > 9:
            value = 9
        if not force and self._value == value:
            return

        self._value = value
        self._label.text = str(value)

    @staticmethod
    def set_ui_style(style):
        pass


class Clock:
    """A digital clock widget that displays and adjusts time using a ui.AbstractValueModel.

    Clock connects to the provided model and listens for time updates. It splits the time value into hours, minutes, and seconds and updates the display using individual number and spinner controls. Users can adjust the hour, minute, or half-day indicators through spinner interactions, and the clock updates the model value accordingly.

    Args:
        model (ui.AbstractValueModel): A model representing time in hours as a float. The model is used to determine the current hour, minute, and second, and to update the time when changes are made through the UI.
    """

    def __init__(self, model: ui.AbstractValueModel):
        self._model = model

        self._build_ui()
        self._model.add_value_changed_fn(self._on_time_changed)
        self._on_time_changed(self._model)

    def _build_ui(self):
        with ui.HStack(height=0, width=0, style=CLOCK_STYLES):
            ui.Spacer(width=10)
            # 2 digits for hour
            self._hour10x = Number()
            self._hour1x = Number()

            # Spin for hour
            ui.Spacer(width=2)
            with ui.VStack():
                ui.Spacer(height=10)
                self._hour_spin = Spinner(15, 30, self._on_hour_spin)

            # Colon between hour and minute
            ui.Spacer(width=4)
            circle_size = 3
            with ui.VStack():
                ui.Spacer(height=12)
                ui.Circle(width=circle_size, height=circle_size)
                ui.Spacer()
                ui.Circle(width=circle_size, height=circle_size)
                ui.Spacer(height=12)
            ui.Spacer(width=4)

            # 2 digits for minute
            self._minute10x = Number()
            self._minute1x = Number()

            # Spin for minute
            ui.Spacer(width=2)
            with ui.VStack():
                ui.Spacer(height=10)
                self._minute_spin = Spinner(15, 30, self._on_minute_spin)

            # Lable for half-day
            ui.Spacer(width=4)
            with ui.VStack():
                ui.Spacer(height=16)
                self._half_day = ui.Label("PM", style_type_name_override="AMPM")

            # Spin for half-day
            with ui.VStack():
                ui.Spacer(height=10)
                self._half_day_spin = Spinner(15, 30, self._on_half_day_spin, False, True, False)

    def _update_hour(self, hour: int):
        section = "PM"
        if hour < 1:
            section = "AM"
            hour = 12
        elif hour < 12:
            section = "AM"
        elif hour < 13:
            hour = hour
        else:
            hour = hour - 12

        self._half_day.text = section
        self._hour10x.set_value(hour // 10)
        self._hour1x.set_value(hour % 10)

    def _update_minute(self, minute: int):
        self._minute10x.set_value(minute // 10)
        self._minute1x.set_value(minute % 10)

    def _on_hour_spin(self, step):
        hour, minute, second = self._get_time(self._model)
        hour += step
        if hour < 0:
            hour = 23
        elif hour > 23:
            hour = 0

        self._set_time(hour, minute, second)

    def _on_minute_spin(self, step):
        hour, minute, second = self._get_time(self._model)
        minute += step
        if minute < 0:
            minute = 59
        elif minute > 59:
            minute = 0

        self._set_time(hour, minute, second)

    def _on_half_day_spin(self, step):
        hour, minute, second = self._get_time(self._model)
        if hour < 12:
            hour += 12
            self._half_day.text = "PM"
        else:
            hour -= 12
            self._half_day.text = "AM"

        self._set_time(hour, minute, second)

    def _on_time_changed(self, model: ui.AbstractValueModel) -> None:
        hour, minute, second = self._get_time(model)

        self._update_hour(hour)
        self._update_minute(minute)

    def _get_time(self, model: ui.AbstractValueModel) -> Tuple[int, int, int]:
        value = model.as_float
        value = max(value, 0)
        value = min(value, 24)

        hour = int(value)
        total_seconds = int((value - hour) * 3600)
        minute = int(total_seconds / 60)
        second = total_seconds % 60

        return (hour, minute, second)

    def _set_time(self, hour: int, minute: int, second: int) -> float:
        value = hour + float(minute * 60 + second) / 3600
        self._model.set_value(value)

    def on_update(self, dt):
        """Updates the hour and minute spinner objects of the Clock using the elapsed time.

        Args:
            dt (float): Elapsed time in seconds for spin update.

        Returns:
            bool: True after updating the spinner objects.
        """
        self._hour_spin.on_update(dt)
        self._minute_spin.on_update(dt)
        return True
