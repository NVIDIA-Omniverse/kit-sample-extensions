# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
import omni.ui as ui

from .constant import COLORS, FONT_OFFSET_Y, DarkColors, FontSize, LightColors, MouseKey
from .style import get_ui_style


class TriangleCursorIntSlider:
    LIGHT_STYLE = {
        "Slider::transparent": {
            "draw_mode": ui.SliderDrawMode.HANDLE,
            "background_color": COLORS.TRANSPARENT,
            "color": COLORS.TRANSPARENT,
            "secondary_color": COLORS.TRANSPARENT,
            "secondary_selected_color": COLORS.TRANSPARENT,
        },
        "Triangle::slider": {"background_color": LightColors.Background},
    }
    DARK_STYLE = {
        "Slider::transparent": {
            "draw_mode": ui.SliderDrawMode.HANDLE,
            "background_color": COLORS.TRANSPARENT,
            "color": COLORS.TRANSPARENT,
            "secondary_color": COLORS.TRANSPARENT,
            "secondary_selected_color": COLORS.TRANSPARENT,
        },
        "Triangle::slider": {"background_color": DarkColors.Background},
    }
    UI_STYLES = {"NvidiaLight": LIGHT_STYLE, "NvidiaDark": DARK_STYLE}

    def __init__(self, min, max, value, width, height, **kwargs):
        self._value = min
        self._value_changed_fn = None
        self._min = min
        self._value_steps = max - min
        self._cursor_size = kwargs.get("cursor_size", 12)

        with ui.ZStack(width=width, height=height, style=TriangleCursorIntSlider.UI_STYLES[get_ui_style()]):
            self._slider = ui.IntSlider(min=min, max=max, step=1, width=width, name="transparent", **kwargs)
            with ui.VStack(height=height):
                ui.Spacer()
                ui.Line(height=1, style={"color": 0xFFA4A4A4})
                ui.Line(height=1, style={"color": 0xFFC7C7C7})
                ui.Spacer()
            with ui.VStack(height=height - 4):
                ui.Spacer()
                self._slider_cursor = ui.Placer(offset_x=0)
                with self._slider_cursor:
                    self._cursor = ui.Triangle(
                        width=self._cursor_size,
                        height=self._cursor_size,
                        name="slider",
                        alignment=ui.Alignment.CENTER_BOTTOM,
                        **kwargs,
                    )
                ui.Spacer()

        self._slider.model.add_value_changed_fn(self._on_value_changed)
        self.set_value(value)

    def set_value_changed_fn(self, value_changed_fn):
        self._value_changed_fn = value_changed_fn

    def set_value(self, value):
        self._slider.model.set_value(value)

    def _on_value_changed(self, model):
        value = model.as_int
        if value != self._value:
            self._value = value
            self._set_cursor()
            if self._value_changed_fn is not None:
                self._value_changed_fn(self._value)

    def _set_cursor(self):
        self._slider_cursor.offset_x = (
            (self._value - self._min) * (self._slider.width.value - self._cursor_size) / (self._value_steps)
        )


class FloatSliderEx:
    LIGHT_STYLE = {
        "Slider": {
            "background_color": LightColors.WindowBackground,
            "color": COLORS.TRANSPARENT,
            "border_color": LightColors.Background,
            "secondary_color": LightColors.Background,
            "border_radius": 20,
            "border_width": 1,
            "padding": 1.5,
            "font_size": FontSize.Small,
        },
        "Slider:disabled": {
            "background_color": 0xFFE0E0E0,
            "color": COLORS.TRANSPARENT,
            "border_color": 0xFFACACAC,
            "secondary_color": 0xFFACACAC,
            "border_radius": 20,
            "border_width": 1,
            "padding": 1.5,
            "font_size": FontSize.Small,
        },
        "Slider.Text": {"color": LightColors.TextSelected},
        "Slider.Text:disabled": {"color": LightColors.Background},
    }
    DARK_STYLE = {
        "Slider": {
            "background_color": DarkColors.WindowBackground,
            "secondary_color": DarkColors.Background,
            "color": COLORS.TRANSPARENT,
            "border_color": DarkColors.Background,
            "border_width": 2,
            "border_radius": 20,
            "padding": 1.5,
            "font_size": FontSize.Small,
        },
        "Slider.Text:disabled": {"color": DarkColors.TextDisabled},
    }
    UI_STYLES = {"NvidiaLight": LIGHT_STYLE, "NvidiaDark": DARK_STYLE}

    DEFAULT_HEIGHT = 26

    def __init__(
        self, value, on_value_changed_fn: callable = None, min=0, max=1, step=0.1, unit=None, enabled=True, **kwargs
    ):
        if "height" not in kwargs:
            kwargs["height"] = self.DEFAULT_HEIGHT
        if "style" not in kwargs:
            kwargs["style"] = self.UI_STYLES[get_ui_style()]
        height = kwargs.get("height")

        if "min" in kwargs:
            min = kwargs.get("min")
        if "max" in kwargs:
            max = kwargs.get("max")
        if "step" in kwargs:
            step = kwargs.get("step")
        if "unit" in kwargs:
            unit = kwargs.get("unit")
        self.trigger_event_when_set_value = True
        if "always_trigger_event" in kwargs:
            self.trigger_event_when_set_value = kwargs.get("always_trigger_event")

        if min > max:
            temp = max
            max = min
            min = temp
        if value < min:
            value = min
        elif value > max:
            value = max

        self._in_set_value = False
        # Used to set display value decimal
        self._unit = unit
        self._decimal_factor = self._get_value_factor(step)
        self._value = self._format_value(value)
        self._on_value_changed_fn = on_value_changed_fn
        self._enabled = enabled
        self._selected = False

        with ui.ZStack(**kwargs):
            with ui.VStack():
                ui.Spacer()
                self._slider = ui.FloatSlider(min=min, max=max, height=height - 8)
                ui.Spacer()
            with ui.Placer(offset_y=FONT_OFFSET_Y):
                self._label = ui.Label("", style_type_name_override="Slider.Text", alignment=ui.Alignment.CENTER)

        self._label.text = self._get_display()
        self._label.enabled = enabled
        self._slider.model.set_value(self._value)
        self._slider.model.add_value_changed_fn(self._on_value_changed)
        self._slider.enabled = enabled

    def __del__(self):
        pass

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, new_value):
        self._in_set_value = True
        # self._value = new_value
        self._slider.model.set_value(new_value)
        self._in_set_value = False

    @property
    def min(self):
        return self._slider.min

    @min.setter
    def min(self, value):
        self._slider.min = value

    @property
    def max(self):
        return self._slider.min

    @max.setter
    def max(self, value):
        self._slider.max = value

    @property
    def enabled(self):
        return self._enabled

    @enabled.setter
    def enabled(self, status):
        self._enabled = status
        self._slider.enabled = status
        self._label.enabled = status

    @property
    def selected(self):
        return self._selected

    @selected.setter
    def selected(self, status):
        self._selected = status
        self._slider.selected = status

    def _get_value_factor(self, step):
        number = step
        count = 0
        while round(number) < 1:
            number *= 10
            count += 1
        return pow(10, count)

    def _format_value(self, value):
        value = round(value * self._decimal_factor)
        value /= self._decimal_factor
        return value

    def _get_display(self):
        return f"{self._value} {self._unit}" if self._unit is not None else str(self._value)

    def _on_value_changed(self, model):
        value = self._format_value(model.as_float)
        if self._value != value:
            self._value = value
            self._label.text = self._get_display()

            if self._on_value_changed_fn:
                if self.trigger_event_when_set_value or not self._in_set_value:
                    self._on_value_changed_fn(self._value)
