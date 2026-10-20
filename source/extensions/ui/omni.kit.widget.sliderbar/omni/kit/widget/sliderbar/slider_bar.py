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
from enum import IntEnum
from typing import Callable, Dict

import carb
import omni.kit.app
from omni import ui

from .drag_button import ArrowAlignment, DragButton, ImageAlignment
from .style import UI_STYLE


class MouseKey(IntEnum):
    NONE = -1
    LEFT = 0
    RIGHT = 1
    MIDDLE = 2


class StartPoint:
    WIDGET = "widget"
    SLIDER = "slider"
    CONTENT = "content"


class SliderBar:
    """
    Represents a slider bar with dragable buttons.

    Keyword Args:
        width (ui.Length): Widget width. Default ui.Fraction(1)
        start (float): Slider bar's start value. Default 0.
        end (float): Slider bar's end value. Default 24.
        current (float): Slider bar's current value. Default 0.
        value_format_fn (callable): Function called to do value format. Default None, means using default style.
        min_value (float): Slider bar's min value. Default 0.0.
        min_value_inclusive (bool): To show the slider bar whether include the min value. Default True.
        max_value (float): Slider bar's min value. Default 24.0.
        max_value_inclusive (bool): To show the slider bar whether include the max value. Default False.
        style (Dict): Widget additional style. Default None, means using default style.
        padding_width (ui.Length): Padding width of the widget.
        slider_padding_width (ui.Length): Padding width of slider.
        slier_height (ui.Length): Height of slider.
    """

    # Object that can be dragging
    OBJ_CURSOR = 0
    OBJ_START = 1
    OBJ_END = 2

    def __init__(
        self,
        width: ui.Length = ui.Fraction(1),
        start: float = 0.0,
        end: float = 24.0,
        current: float = 0.0,
        value_format_fn: Callable[[float], str] = None,
        min_value: float = 0.0,
        min_value_inclusive: bool = True,
        max_value: float = 24.0,
        max_value_inclusive: bool = False,
        style: Dict = {},
        padding_width: ui.Length = ui.Pixel(60),
        slider_padding_width: ui.Length = ui.Pixel(30),
        slider_height: ui.Length = ui.Pixel(16),
        arrow_height: ui.Length = ui.Pixel(8),
        start_arrow_alignment: ArrowAlignment = ArrowAlignment.RIGHT,
        end_arrow_alignment: ArrowAlignment = ArrowAlignment.LEFT,
    ):
        self._width = width
        self._value = current
        self._min_value = min_value
        self._min_value_inclusive = min_value_inclusive
        self._max_value = max_value
        self._max_value_inclusive = max_value_inclusive
        self._start = max(start, self._get_real_min_value())
        self._end = min(end, self._get_real_max_value())
        self._value_format_fn = value_format_fn
        self._style = style
        self._padding_width = padding_width
        self._slider_padding_width = slider_padding_width
        self._slider_height = slider_height
        self._arrow_height = arrow_height
        self._start_arrow_alignment = start_arrow_alignment
        self._end_arrow_alignment = end_arrow_alignment

        self._value_range = self._max_value - self._min_value
        self._drag_context = {}

        self._saved_context_width = None
        self._cursor_radius = self._slider_height / 2 - 1

        self._start_changed_callbacks = []
        self._end_changed_callbacks = []
        self._current_changed_callbacks = []

        self._build_ui()

        if isinstance(self._width, ui.Fraction):
            # TODO: No widget width changed event, use on_update instead
            self._update_sub = carb.eventdispatcher.get_eventdispatcher().observe_event(
                observer_name="omni.kit.widget.sliderbar.SliderBar",
                event_name=omni.kit.app.GLOBAL_EVENT_UPDATE,
                on_event=self._on_update,
            )

    def destroy(self):
        self._update_sub = None

    def _build_ui(self):
        with ui.Frame(width=self._width, height=0, style=UI_STYLE):
            with ui.VStack(style=self._style):
                self._build_buttons()
                self._build_slider()

        async def __update_position_async():
            while self._content_container.computed_content_width <= 0:
                await omni.kit.app.get_app().next_update_async()
            self._start_button.text = self._get_display_value(self._start)
            self._end_button.text = self._get_display_value(self._end)
            await omni.kit.app.get_app().next_update_async()
            self._update_position()
            self._saved_context_width = self._content_container.computed_content_width

        asyncio.ensure_future(__update_position_async())

    def _build_buttons(self):
        with ui.ZStack(height=0):
            self._start_placer = ui.Placer(offset_x=0, offset_y=0)
            with self._start_placer:
                self._start_button = DragButton(
                    image_alignment=ImageAlignment.LEFT,
                    arrow_alignment=self._start_arrow_alignment,
                    arrow_height=self._arrow_height,
                )
            self._start_button.set_mouse_event_fn(
                lambda x, y, key, a: self._on_double_clicked_trim(SliderBar.OBJ_START),
                lambda x, y, key, a: self._begin_drag(key, x, SliderBar.OBJ_START),
                lambda x, y, key, m: self._dragging(x),
                lambda x, y, key, m: self._end_drag(),
                lambda x, y, key, m: self._reset_start_pos(key),
            )

            self._end_placer = ui.Placer(offset_x=200, offset_y=0)
            with self._end_placer:
                self._end_button = DragButton(
                    image_alignment=ImageAlignment.RIGHT,
                    arrow_alignment=self._end_arrow_alignment,
                    arrow_height=self._arrow_height,
                )
            self._end_button.set_mouse_event_fn(
                lambda x, y, key, a: self._on_double_clicked_trim(SliderBar.OBJ_END),
                lambda x, y, key, a: self._begin_drag(key, x, SliderBar.OBJ_END),
                lambda x, y, key, m: self._dragging(x),
                lambda x, y, key, m: self._end_drag(),
                lambda x, y, key, m: self._reset_end_pos(key),
            )

    def _build_slider(self):
        with ui.HStack():
            ui.Spacer(width=self._padding_width)
            with ui.ZStack(height=self._slider_height):
                ui.Rectangle(name="outer")
                with ui.HStack():
                    ui.Spacer(width=self._slider_padding_width)
                    self._content_container = ui.ZStack()
                    with self._content_container:
                        self._end_rect = ui.Rectangle(
                            name="end", width=ui.Percent((self._end - self._min_value) * 100 / self._value_range)
                        )
                        self._start_rect = ui.Rectangle(
                            name="start", width=ui.Percent((self._start - self._min_value) * 100 / self._value_range)
                        )
                    ui.Spacer(width=self._slider_padding_width)

                self._end_seperator_placer = ui.Placer(offset_x=0, offset_y=0)
                with self._end_seperator_placer:
                    self._end_line = ui.Line(
                        width=1, padding=0, alignment=ui.Alignment.LEFT, style_type_name_override="Seperator"
                    )
                self._start_seperator_placer = ui.Placer(offset_x=0, offset_y=0)
                with self._start_seperator_placer:
                    ui.Line(width=1, alignment=ui.Alignment.LEFT, style_type_name_override="Seperator")

                self._cursor_placer = ui.Placer(offset_x=0, offset_y=1)
                with self._cursor_placer:
                    ui.Circle(
                        name="cursor",
                        radius=self._cursor_radius,
                        width=self._cursor_radius * 2,
                        height=self._cursor_radius * 2,
                        alighment=ui.Alignment.CENTER,
                        mouse_pressed_fn=(lambda x, y, key, m: self._begin_drag(key, x, SliderBar.OBJ_CURSOR)),
                        mouse_moved_fn=(lambda x, y, key, m: self._dragging(x)),
                        mouse_released_fn=(lambda x, y, key, m: self._end_drag()),
                    )
            ui.Spacer(width=self._padding_width)

    def set_current(self, current):
        self._value = current
        self._cursor_placer.offset_x = self._get_cursor_offset(current)

    def get_current(self):
        return self._value

    def set_start(self, start):
        self._start = max(start, self._get_real_min_value())
        self._start_rect.width = ui.Percent((self._start - self._min_value) * 100 / self._value_range)
        self._start_seperator_placer.offset_x = self._get_seperator_offset(self._start)
        self._start_button.text = self._get_display_value(self._start)
        self._start_placer.offset_x = self._get_start_button_offset(self._start)

    def get_start(self):
        return self._start

    def set_end(self, end):
        self._end = min(end, self._get_real_max_value())
        self._end_rect.width = ui.Percent((self._end - self._min_value) * 100 / self._value_range)
        self._end_seperator_placer.offset_x = self._get_seperator_offset(self._end)
        self._end_button.text = self._get_display_value(self._end)
        self._end_placer.offset_x = self._get_end_button_offset(self._end)

    def get_end(self):
        return self._end

    def _add_callback_fn(self, callback_fn: callable, callback_fn_list):
        for cb in callback_fn_list:
            if cb == callback_fn:
                return
        callback_fn_list.append(callback_fn)

    def _trigger_callback_fn(self, callback_fn_list, value):
        if len(callback_fn_list) > 0:
            for cb in callback_fn_list:
                cb(value)

    def add_callback_fns(self, on_start_changed: callable, on_end_changed: callable, on_current_changed: callable):
        if on_start_changed is not None:
            self._add_callback_fn(on_start_changed, self._start_changed_callbacks)

        if on_end_changed is not None:
            self._add_callback_fn(on_end_changed, self._end_changed_callbacks)

        if on_current_changed is not None:
            self._add_callback_fn(on_current_changed, self._current_changed_callbacks)

    def _begin_drag(self, key, x, drag_object):
        if key != MouseKey.LEFT:
            return

        self._drag_context["object"] = drag_object
        self._drag_context["start_mouse_pos_x"] = x
        if drag_object == SliderBar.OBJ_CURSOR:
            self._drag_context["start_object_pos"] = self._cursor_placer.offset_x.value
            self._drag_context["start_value"] = self._value
        elif drag_object == SliderBar.OBJ_START:
            self._drag_context["start_object_pos"] = self._start_placer.offset_x.value
            self._drag_context["start_value"] = self._start
        elif drag_object == SliderBar.OBJ_END:
            self._drag_context["start_object_pos"] = self._end_placer.offset_x.value
            self._drag_context["start_value"] = self._end

    def _dragging(self, x):
        delta = x - self._drag_context["start_mouse_pos_x"]
        value = self._drag_context["start_value"] + self._offset_to_value(delta)

        if self._drag_context["object"] == SliderBar.OBJ_CURSOR:
            value = max(value, self._start)
            value = min(value, self._end)
            if value != self._value:
                self.set_current(value)
                self._trigger_callback_fn(self._current_changed_callbacks, value)

        elif self._drag_context["object"] == SliderBar.OBJ_START:
            value = max(value, self._get_real_min_value())
            value = min(value, self._value)
            if value != self._start:
                self.set_start(value)
                self._trigger_callback_fn(self._start_changed_callbacks, value)

        elif self._drag_context["object"] == SliderBar.OBJ_END:
            value = min(value, self._get_real_max_value())
            value = max(value, self._value)
            if value != self._end:
                self.set_end(value)
                self._trigger_callback_fn(self._end_changed_callbacks, value)

    def _end_drag(self):
        self._drag_context["object"] = None

    def _on_double_clicked_trim(self, drag_object):
        pass

    def _get_real_min_value(self):
        if self._min_value_inclusive:
            return self._min_value
        else:
            return self._min_value + 0.000001

    def _get_real_max_value(self):
        if self._max_value_inclusive:
            return self._max_value
        else:
            return self._max_value - 0.000001

    def _reset_start_pos(self, key):
        if key != MouseKey.LEFT:
            return

        self.set_start(self._get_real_min_value())
        self._trigger_callback_fn(self._start_changed_callbacks, self._get_real_min_value())

    def _reset_end_pos(self, key):
        if key != MouseKey.LEFT:
            return

        self.set_end(self._get_real_max_value())
        self._trigger_callback_fn(self._end_changed_callbacks, self._get_real_max_value())

    def _value_to_offset(self, value: float) -> float:
        # Offset in content area
        return value * self._content_container.computed_content_width / self._value_range

    def _offset_to_value(self, offset: float) -> float:
        return offset * self._value_range / self._content_container.computed_content_width

    def _get_offset(self, value: float, start_point: StartPoint):
        offset = self._value_to_offset(value)
        if start_point == StartPoint.CONTENT:
            return offset
        elif start_point == StartPoint.SLIDER:
            return offset + self._slider_padding_width
        elif start_point == StartPoint.WIDGET:
            return offset + self._slider_padding_width + self._padding_width

    def _get_cursor_offset(self, value: float) -> float:
        return self._get_offset(value - self._min_value, StartPoint.SLIDER) - self._cursor_radius

    def _get_seperator_offset(self, value: float) -> float:
        return self._get_offset(value - self._min_value, StartPoint.SLIDER)

    def _get_start_button_offset(self, value: float) -> float:
        return self._get_offset(value - self._min_value, StartPoint.WIDGET) - self._start_button.offset_arrow

    def _get_end_button_offset(self, value: float) -> float:
        return self._get_offset(value - self._min_value, StartPoint.WIDGET) - self._end_button.offset_arrow

    def _on_update(self, _):
        if self._saved_context_width is None:
            return

        async def __quick_update():
            self._end_placer.visible = False
            self._cursor_placer.visible = False
            self._end_seperator_placer.visible = False
            self._start_placer.visible = False
            self._start_seperator_placer.visible = False
            await omni.kit.app.get_app().next_update_async()
            self._update_position()
            self._end_placer.visible = True
            self._cursor_placer.visible = True
            self._end_seperator_placer.visible = True
            self._start_placer.visible = True
            self._start_seperator_placer.visible = True

        if abs(self._content_container.computed_content_width - self._saved_context_width) >= 1:
            asyncio.ensure_future(__quick_update())
            self._saved_context_width = self._content_container.computed_content_width

    def _update_position(self):
        self._cursor_placer.offset_x = self._get_cursor_offset(self._value)
        self._start_placer.offset_x = self._get_start_button_offset(self._start)
        self._end_placer.offset_x = self._get_end_button_offset(self._end)
        self._start_seperator_placer.offset_x = self._get_seperator_offset(self._start)
        self._end_seperator_placer.offset_x = self._get_seperator_offset(self._end)

    def _get_display_value(self, value: float) -> str:
        if self._value_format_fn is not None:
            return self._value_format_fn(value)
        else:
            return "{:.2f}".format(value)
