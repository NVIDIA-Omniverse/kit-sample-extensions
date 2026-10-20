# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
import asyncio
from datetime import datetime

import omni.kit.app
from omni import ui
from omni.kit.environment.core import (
    EnvironmentProperties,
    PlayButton,
    PlayLoopButton,
    PlayRateButton,
    SunstudyTimeSlider,
    UsdModelBuilder,
    get_sunstudy_player,
)
from pxr import Sdf

from ..style import SLIDER_STYLE
from .calendar_window import CalendarWindow
from .clock_window import ClockWindow
from .property_group import AbstractPropertyGroup


class DateTimeGroup(AbstractPropertyGroup):
    def __init__(self):
        self._player = get_sunstudy_player()

        self._rate_button = None
        self._loop_button = None
        self._play_button = None
        self._clock_window = None
        self._calendar_window = None
        self._time_label = None
        self._date_label = None
        self._time_slider = None

        self._date_model = UsdModelBuilder().create_property_value_model(
            EnvironmentProperties.DATE, value_type=Sdf.ValueTypeNames.String, default=self._player.current_date
        )
        self._date_model.add_value_changed_fn(self._on_datetime_changed)

        super().__init__("Time of Day")

    def destroy(self):
        if self._time_slider is not None:
            self._time_slider.destroy()
        if self._play_button is not None:
            self._play_button.destroy()
            self._rate_button.destroy()
            self._loop_button.destroy()

        self._clock_window = None
        self._calendar_window = None

        super().destroy()

    def _build_widgets(self):
        with ui.VStack(height=0):
            self._time_slider = SunstudyTimeSlider(on_datetime_changed_fn=self._on_datetime_changed, style=SLIDER_STYLE)
            ui.Spacer(height=2)
            with ui.ZStack():
                with ui.HStack(height=20):
                    ui.Spacer(width=24)
                    self._rate_button = PlayRateButton(width=16, height=16, image_width=14, image_height=14)
                    self._loop_button = PlayLoopButton(width=16, height=16, image_width=14, image_height=14)
                    ui.Spacer()

                with ui.HStack(height=0):
                    ui.Spacer()
                    self._play_button = PlayButton(self._player, width=16, height=16, image_width=14, image_height=14)
                    ui.Spacer()

        self._time_slider.current_time_model.add_value_changed_fn(self._on_datetime_changed)
        self._update_datetime()

    def _build_extra_header(self):
        self._time_label = ui.Label("", width=0, mouse_pressed_fn=lambda x, y, b, a: self._show_clock())
        ui.Spacer(width=6)
        self._date_label = ui.Label("", width=0, mouse_pressed_fn=lambda x, y, b, a: self._show_calendar())
        self._calendar_button = ui.Button(
            "",
            width=20,
            height=20,
            image_width=16,
            image_height=16,
            mouse_pressed_fn=lambda x, y, a, m: self._show_calendar(),
            style_type_name_override="Date.Calendar",
        )
        self._update_datetime()

    def _show_clock(self):
        if self._clock_window is None:
            self._clock_window = ClockWindow(self._time_slider.current_time_model)
        self._clock_window.visible = True

        async def __set_position():
            while self._clock_window.computed_content_width <= 0:
                await omni.kit.app.get_app().next_update_async()
            await omni.kit.app.get_app().next_update_async()
            self._clock_window.position_x = (
                self._time_label.screen_position_x
                + self._time_label.computed_content_width
                - self._clock_window.computed_content_width
            )
            self._clock_window.position_y = (
                self._time_label.screen_position_y - self._clock_window.computed_content_height
            )

        asyncio.ensure_future(__set_position())

    def _show_calendar(self):
        if self._calendar_window is None:
            self._calendar_window = CalendarWindow()
            self._calendar_window.model.add_value_changed_fn(self._on_calendar_changed)
        self._calendar_window.visible = True

        async def __set_position():
            while self._calendar_window.computed_content_width <= 0:
                await omni.kit.app.get_app().next_update_async()
            await omni.kit.app.get_app().next_update_async()
            self._calendar_window.position_x = (
                self._calendar_button.screen_position_x
                + self._calendar_button.computed_content_width
                - self._calendar_window.computed_content_width
            )
            self._calendar_window.position_y = (
                self._calendar_button.screen_position_y - self._calendar_window.computed_content_height
            )

        asyncio.ensure_future(__set_position())

    def _on_calendar_changed(self, model: ui.AbstractValueModel) -> None:
        self._date_model.set_value(model.as_string)

    def _on_datetime_changed(self, mode: ui.AbstractValueModel) -> None:
        self._update_datetime()

    def _update_datetime(self):
        if self._time_slider is None or self._time_label is None:
            return
        time = self.time_float_to_string(self._time_slider.current_time_model.as_float)
        date_time = datetime.strptime(f"{self._date_model.as_string} {time}", "%Y-%m-%d %H:%M:%S")
        self._time_label.text = date_time.strftime("%I:%M %p")
        self._date_label.text = date_time.strftime("%B %d, %Y")

    def time_float_to_string(self, value: float) -> str:
        value = max(value, 0)
        value = min(value, 24)

        hour = int(value)
        total_seconds = int((value - hour) * 3600)
        minute = int(total_seconds / 60)
        second = total_seconds % 60

        return "{}:{:02d}:{:02d}".format(hour, minute, second)
