# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
import calendar
from datetime import datetime
from enum import IntEnum
from typing import Callable, Dict, Optional

from omni import ui

from .style import UI_STYLE


class MouseKey(IntEnum):
    NONE = -1
    LEFT = 0
    RIGHT = 1
    MIDDLE = 2


class AbstractCalendarClass:
    pass


class Calendar(AbstractCalendarClass):
    """
    Represents a calendar to show year month and day
    Keyword Args:
        date (datetime.date). Show date time. Default is None, means use current date.
        width (Optional[ui.Length]): Widget widthl. Default ui.Pixel(210). Use None for auto.
        height (Optional[ui.Length]): Widget height. Default ui.Pixel(200). Use None for auto.
        style (Dict): Widget additional style. Default None, means using default style.
        show_combobox (bool): Show comboxbox for year/month or use button instead.
        first_weekday (int): Set the first weekday, 0 = Monday...6 = Sunday.
    Functions:
        set_date(dt: datetime.date): Change show date to dt.
    Properties:
        year (int): Current show year.
        month (int): Current show month.
        day (int): Current show day.
    """

    YEAR_MIN = 2000
    YEAR_MAX = 2051

    def __init__(
        self,
        date: datetime.date,
        width: Optional[ui.Length] = ui.Pixel(210),
        height: Optional[ui.Length] = ui.Pixel(200),
        style: Dict = None,
        show_combobox: bool = False,
        day_selected_handler: Callable[[AbstractCalendarClass], None] = None,
        first_weekday: int = calendar.SUNDAY,
    ):
        # Default to today
        self._day: int = date.day
        self._month: int = date.month
        self._year: int = date.year
        self._day_selected_handler = day_selected_handler
        if first_weekday in range(7):
            self._first_weekday = first_weekday
        else:
            self._first_weekday = calendar.SUNDAY

        self.model = ui.SimpleStringModel(self._get_model_value())

        ui_style = UI_STYLE.copy()
        if style is not None:
            ui_style.update(style)

        self._day_buttons = [None for i in range(32)]
        self._calendar = calendar.Calendar(self._first_weekday)

        self._year_list = [str(year) for year in range(Calendar.YEAR_MIN, Calendar.YEAR_MAX)]
        self._month_list = calendar.month_name[1:]

        month_offset = 10 if show_combobox else 15
        month_width = 90 if show_combobox else 80
        year_offset = 165 if show_combobox else 155
        year_width = 60 if show_combobox else 80
        with ui.VStack(width=width, height=height, spacing=0, style=ui_style):
            # Month and Year
            with ui.ZStack(spacing=0, height=30, width=width):
                with ui.Placer(offset_x=month_offset, offset_y=5):
                    self._month_combo = ui.ComboBox(
                        self._month - 1, *self._month_list, name="calendar", width=month_width, height=26
                    )
                with ui.Placer(offset_x=10, offset_y=0):
                    self._month_rect = ui.Button(
                        self._month_list[self._month - 1], name="calendar", width=90, height=30
                    )

                with ui.Placer(offset_x=year_offset, offset_y=5):
                    self._year_combo = ui.ComboBox(
                        self._year - Calendar.YEAR_MIN, *self._year_list, name="calendar", width=year_width, height=26
                    )
                with ui.Placer(offset_x=150, offset_y=0):
                    self._year_rect = ui.Button(str(self._year), name="calendar", width=90, height=30)

                self._month_combo.model.add_item_changed_fn(self._on_month_changed)
                self._year_combo.model.add_item_changed_fn(self._on_year_changed)

            # Week days
            ui.Spacer(height=5)
            with ui.ZStack(width=width, height=18, spacing=0):
                base_week_day = ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"]
                week_day = base_week_day[self._first_weekday :] + base_week_day[0 : self._first_weekday]
                for i in range(7):
                    with ui.Placer(offset_x=i * 33 + 10, offset_y=0):
                        ui.Label(week_day[i], name="calendar", alignment=ui.Alignment.CENTER, width=30)

            # Day in month
            self._day_frame = ui.ZStack(width=width, height=120, spacing=0)
            self._rebuild_day_array()

            self._month_rect.visible = not show_combobox
            self._year_rect.visible = not show_combobox

    def _rebuild_day_array(self):
        self._day_frame.clear()
        for i in range(32):
            self._day_buttons[i] = None

        _, lastday = calendar.monthrange(self._year, self._month)
        if self._day > lastday:
            self._day = lastday

        with self._day_frame:
            index = 0
            for day in self._calendar.itermonthdays(self._year, self._month):
                x = (index % 7) * 33 + 10
                y = (index // 7) * 24
                if day > 0:
                    with ui.Placer(offset_x=x, offset_y=y):
                        button = ui.Button(str(day), name="day", width=30, height=18)
                        button.set_mouse_pressed_fn(lambda x, y, b, a, index=day: self._on_day_clicked(b, index))
                        self._day_buttons[day] = button
                        if day == self._day:
                            button.selected = True
                index += 1

    def _on_month_changed(self, model, item):
        selected_month = model.get_item_value_model().as_int + 1
        if not self._month == selected_month:
            self._month = selected_month
            self._month_rect.text = calendar.month_name[self._month]
            self._rebuild_day_array()
            self.model.set_value(self._get_model_value())

    def _on_year_changed(self, model, item):
        selected_year = model.get_item_value_model().as_int + Calendar.YEAR_MIN
        if not self._year == selected_year:
            self._year = selected_year
            self._year_rect.text = str(self._year)
            self._rebuild_day_array()
            self.model.set_value(self._get_model_value())

    def _on_day_clicked(self, key, day):
        if key != MouseKey.LEFT:
            return
        self._day_buttons[self._day].selected = False
        self._day = day
        self._day_buttons[day].selected = True
        self.model.set_value(self._get_model_value())
        if self._day_selected_handler:
            self._day_selected_handler(self)

    def _get_model_value(self) -> str:
        return "{}-{:02}-{:02}".format(self._year, self._month, self._day)

    @property
    def year(self):
        return self._year

    @property
    def month(self):
        return self._month

    @property
    def day(self):
        return self._day

    def set_date(self, dt: datetime.date):
        self._year = dt.year
        self._month = dt.month
        self._day = dt.day

        self._year_combo.model.get_item_value_model().set_value(self._year - Calendar.YEAR_MIN)
        self._year_rect.text = str(self._year)
        self._month_combo.model.get_item_value_model().set_value(self._month - 1)
        self._month_rect.text = self._month_list[self._month - 1]
        self._rebuild_day_array()
        self.model.set_value(self._get_model_value())
