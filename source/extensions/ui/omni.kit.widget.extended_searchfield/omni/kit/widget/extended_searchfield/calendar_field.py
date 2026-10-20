# SPDX-FileCopyrightText: Copyright (c) 2018-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
from datetime import datetime, timedelta
from typing import Callable

import omni.ui as ui

from .calendar_popup import CalendarPopup
from .named_field import NamedField
from .style import ICON_PATH


class CalendarField(NamedField):

    OFFSET_X = 150
    OFFSET_Y = -100

    def __init__(
        self,
        name: str,
        hint: str = "",
        date_validator: Callable[[None], None] = None,
        ok_handler: Callable[[NamedField], None] = None,
    ):
        self._name = name
        self._hint = hint
        self._field_container = {}
        self._default = ""
        self._ok_handler = ok_handler
        self._date_validator = date_validator
        self._build_ui()

    def set_date(self, date: str):
        self._string_field.visible = bool(date)
        self._hint_container.visible = not bool(date)
        self._model.set_value(date)

    def _day_selected(self, calendar):
        date = calendar.model.get_value_as_string()
        self.set_date(date)
        self._calendar.hide()
        if self._ok_handler:
            self._ok_handler(self)
        # Shows an error if the "after" date is after the "before" date
        self._date_validator()

    def show(self):
        self._model.set_value("")
        self._string_field.visible = False
        self._hint_container.visible = True
        self._container.visible = True

    def hide(self):
        self._model.set_value("")
        self._string_field.visible = False
        self._container.visible = False

    def _build_ui(self):
        self._container = ui.HStack()
        with self._container:
            with ui.VStack():
                button = ui.Button(
                    name=self._name,
                    image_url=f"{ICON_PATH}/folder.svg",
                    image_width=14,
                    height=18,
                    style_type_name_override="Calendar.Button",
                )
                self._calendar = CalendarPopup(title=self._name, width=255, on_day_selected_fn=self._day_selected)
                self._calendar.hide()
                button.set_clicked_fn(
                    lambda p=button, c=self._calendar: c.show(
                        p, offset_x=CalendarField.OFFSET_X, offset_y=CalendarField.OFFSET_Y
                    )
                )
                ui.Spacer(height=1)

            with ui.ZStack(width=75):
                self._string_field = ui.StringField(
                    name=self._name,
                    style_type_name_override="ExtendedSearchField.CalendarStringField",
                    alignment=ui.Alignment.CENTER,
                )

                self._string_field.enabled = False
                self._model = self._string_field.model
                self._string_field.set_mouse_pressed_fn(
                    lambda x, y, b, m, p=button, c=self._calendar: c.show(
                        p, offset_x=CalendarField.OFFSET_X, offset_y=CalendarField.OFFSET_Y
                    )
                )

                self._sub_begin_edit = self._model.subscribe_begin_edit_fn(self._on_begin_edit)
                self._sub_end_edit = self._model.subscribe_end_edit_fn(self._on_end_edit)

                self._hint_container = ui.HStack()
                with self._hint_container:
                    label = ui.Label(self._hint, style_type_name_override="ExtendedSearchField.CalendarHint")
                    label.set_mouse_pressed_fn(
                        lambda x, y, b, m, p=button, c=self._calendar: c.show(
                            p, offset_x=CalendarField.OFFSET_X, offset_y=CalendarField.OFFSET_Y
                        )
                    )

        self._container.visible = False

    def _on_end_edit(self, model: ui.AbstractValueModel):
        super()._on_end_edit(model)
        self._date_validator()

    def destroy(self):
        super().destroy()
        self._calendar = None
        self._field_container = None


class CalendarController:
    def __init__(self, error_handler: Callable[[bool, str], None], ok_handler: Callable[[NamedField], None] = None):
        """Create two calendar fields, one for `created_after` and one for `created_before`.

        Also creates the combobox that allows selecting prespecified date ranges.
        """
        date_options = ["Any time", "Today", "Yesterday", "Last 7 days", "Last 30 days", "Last 90 days", "Custom"]
        self._custom_index = date_options.index("Custom")
        now = datetime.now()
        dates = {
            # Adjust all ranges by 1 day because it is > not >=
            "Today": now - timedelta(days=1),
            "Yesterday": now - timedelta(days=2),
            "Last 7 days": now - timedelta(days=8),
            "Last 30 days": now - timedelta(days=31),
            "Last 90 days": now - timedelta(days=91),
        }
        self._date_values = {d: "{}-{}-{}".format(dates[d].year, dates[d].month, dates[d].day) for d in dates}
        self._date_model = ui.ComboBox(0, *date_options, width=100).model
        self._created_after_field = CalendarField(
            name="created_after", hint="Start Date", date_validator=self.date_validator, ok_handler=ok_handler
        )
        self._created_before_field = CalendarField(
            name="created_before", hint="End Date", date_validator=self.date_validator, ok_handler=ok_handler
        )
        self._error_handler = error_handler

        def changed_date_range(model):

            index = model.get_item_value_model().get_value_as_int()
            if index == self._custom_index:
                self._created_after_field.show()
                self._created_before_field.show()
            else:
                self._created_before_field.hide()
                self._created_after_field.hide()
                # Non-custom entries are all "created_after". We set the model but hide the field.
                key = date_options[index]
                if key in self._date_values:
                    self._created_after_field.model.set_value(self._date_values[key])
                self._error_handler(False)

        self._date_model.add_item_changed_fn(lambda m, i: changed_date_range(m))

    @property
    def created_before_field(self):
        return self._created_before_field

    @property
    def created_after_field(self):
        return self._created_after_field

    def date_validator(self):
        # check that created_after < created_before
        before = self.created_before_field.model.as_string
        after = self.created_after_field.model.as_string
        if before and after:
            try:
                before_date = datetime.strptime(before, "%Y-%m-%d")
                after_date = datetime.strptime(after, "%Y-%m-%d")
                self._error_handler(after_date > before_date, message="End date must be greater than start date.")
            except ValueError:
                self._error_handler(False)
        else:
            self._error_handler(False)

    def clear(self):
        self._created_before_field.set_date("")
        self._created_after_field.set_date("")
        self._date_model.get_item_value_model(None).set_value(0)
        self._error_handler(False)

    def set_before_date(self, date: str):
        self._date_model.get_item_value_model(None).set_value(self._custom_index)
        self._created_before_field.set_date(date)
        self.date_validator()

    def set_after_date(self, date: str):
        self._date_model.get_item_value_model(None).set_value(self._custom_index)
        self._created_after_field.set_date(date)
        self.date_validator()
