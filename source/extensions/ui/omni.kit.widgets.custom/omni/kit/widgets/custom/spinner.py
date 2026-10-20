# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
from pathlib import Path

from omni import ui

from .constant import COLORS, FONT_OFFSET_Y, FontSize, LightColors, MouseKey
from .style import get_ui_style
from .update_event_helper import UpdateEventHelper

# Reserved space for spinner icons
SPINNER_ICON_MAX_WIDTH = 20
# TODO: with font_size=15 in high resolution, the min float field height is 26
SPINNER_MIN_HEIGHT = 26
# First delay time to start a long click (in seconds)
SPINNER_LONG_CLICK_DELAY = 0.6
# Long click interval (in seconds)
SPINNER_LONG_CLICK_INTERVAL = 0.2

CURRENT_PATH = Path(__file__).parent
ICON_PATH = CURRENT_PATH.parent.parent.parent.parent.joinpath("icons")


# A FloatSpinner, combined with a float field for value and two icons to change value
class BaseSpinner:
    LIGHT_STYLE = {
        "Label": {"color": LightColors.Text},
        "Label:disabled": {"color": LightColors.TextDisabled},
        "Field::spinner_show_value": {
            "background_color": LightColors.Background,
            "color": LightColors.Text,
            "border_radius": 1.0,
            "border_width": 0,
        },
        "Field::spinner_show_value:pressed": {
            "background_color": COLORS.WIDGET_BACKGROUND_LIGHT,
            "color": COLORS.TEXT_LIGHT,
            "border_radius": 1.0,
            "border_width": 0,
        },
        "Field::spinner_hide_value": {
            "background_color": COLORS.TRANSPARENT,
            "secondary_color": COLORS.TRANSPARENT,
            "color": COLORS.TRANSPARENT,
            "border_radius": 0.0,
            "border_width": 0,
        },
        "Slider::spinner_show_value": {
            "background_color": LightColors.Background,
            "secondary_color": LightColors.Background,
            "color": COLORS.TEXT_LIGHT,
            "border_radius": 0.0,
            "border_width": 0,
        },
        "Slider::spinner_show_value:pressed": {
            "background_color": LightColors.Background,
            "secondary_color": LightColors.Background,
            "color": COLORS.TEXT_LIGHT,
            "border_radius": 0.0,
            "border_width": 0,
        },
        "Slider::spinner_hide_value": {
            "background_color": LightColors.Background,
            "secondary_color": LightColors.Background,
            "border_color": COLORS.TRANSPARENT,
            "color": COLORS.TRANSPARENT,
            "border_radius": 0.0,
            "border_width": 0,
        },
        "Image::down": {"image_url": f"{ICON_PATH}/Spinner_Down_Light.svg", "fill_policy": ui.FillPolicy.STRETCH},
        "Image::down:disabled": {"image_url": f"{ICON_PATH}/Spinner_Down.svg", "fill_policy": ui.FillPolicy.STRETCH},
        "Image::left": {"image_url": f"{ICON_PATH}/Spinner_Left_Light.svg", "fill_policy": ui.FillPolicy.STRETCH},
        "Image::left:disabled": {"image_url": f"{ICON_PATH}/Spinner_Left.svg", "fill_policy": ui.FillPolicy.STRETCH},
        "Image::right": {"image_url": f"{ICON_PATH}/Spinner_Right_Light.svg", "fill_policy": ui.FillPolicy.STRETCH},
        "Image::right:disabled": {"image_url": f"{ICON_PATH}/Spinner_Right.svg", "fill_policy": ui.FillPolicy.STRETCH},
        "Image::up": {"image_url": f"{ICON_PATH}/Spinner_Up_Light.svg", "fill_policy": ui.FillPolicy.STRETCH},
        "Image::up:disabled": {"image_url": f"{ICON_PATH}/Spinner_Up.svg", "fill_policy": ui.FillPolicy.STRETCH},
        "Rectangle": {"background_color": LightColors.Background, "border_radius": 0.0},
    }

    DARK_STYLE = {
        "Label": {"color": COLORS.TEXT_DARK},
        "Label:disabled": {"color": COLORS.TEXT_DISABLED_DARK},
        "Field::spinner_show_value": {
            "background_color": COLORS.WIDGET_BACKGROUND_DARK,
            "color": COLORS.TEXT_DARK,
            "border_radius": 1.0,
            "border_width": 0,
        },
        "Field::spinner_show_value:pressed": {
            "background_color": COLORS.WIDGET_BACKGROUND_DARK,
            "color": COLORS.TEXT_DARK,
            "border_radius": 1.0,
            "border_width": 0,
        },
        "Field::spinner_hide_value": {
            "background_color": COLORS.TRANSPARENT,
            "color": COLORS.TRANSPARENT,
            "border_radius": 1.0,
            "border_width": 0,
        },
        "Slider::spinner_hide_value": {
            "background_color": COLORS.TRANSPARENT,
            "color": COLORS.TRANSPARENT,
            "border_radius": 1.0,
            "border_width": 0,
        },
        "Image::down": {"image_url": f"{ICON_PATH}/Spinner_Down.svg", "fill_policy": ui.FillPolicy.STRETCH},
        "Image::down:disabled": {"image_url": f"{ICON_PATH}/Spinner_Down.svg", "fill_policy": ui.FillPolicy.STRETCH},
        "Image::left": {"image_url": f"{ICON_PATH}/Spinner_Left_Light.svg", "fill_policy": ui.FillPolicy.STRETCH},
        "Image::left:disabled": {"image_url": f"{ICON_PATH}/Spinner_Left.svg", "fill_policy": ui.FillPolicy.STRETCH},
        "Image::right": {"image_url": f"{ICON_PATH}/Spinner_Right_light.svg", "fill_policy": ui.FillPolicy.STRETCH},
        "Image::right:disabled": {"image_url": f"{ICON_PATH}/Spinner_Right.svg", "fill_policy": ui.FillPolicy.STRETCH},
        "Image::up": {"image_url": f"{ICON_PATH}/Spinner_Up.svg", "fill_policy": ui.FillPolicy.STRETCH},
        "Image::up:disabled": {"image_url": f"{ICON_PATH}/Spinner_Up.svg", "fill_policy": ui.FillPolicy.STRETCH},
        "Rectangle": {"background_color": COLORS.WIDGET_BACKGROUND_DARK, "border_radius": 1.0},
    }

    UI_STYLES = {"NvidiaLight": LIGHT_STYLE, "NvidiaDark": DARK_STYLE}

    def __init__(
        self,
        value_changed_fn,
        value=0.0,
        step=0.1,
        width=None,
        height=SPINNER_MIN_HEIGHT,
        vertical=True,
        min_value=None,
        max_value=None,
        auto_subscribe=True,
        **kwargs,
    ):
        self._value = value
        self._step = abs(step)
        self._min = min_value
        self._max = max_value
        self._spin_up = None
        self._spin_down = None
        self._spin_left = None
        self._spin_right = None

        self._enabled = True
        self._up_pressed = False
        self._down_pressed = False
        self._cur_time = 0.0  # Current system time
        self._action_time = 0.0  # Next time to trigger an click action
        self._in_edit = False  # Float field in edit mode
        self._need_submit = False

        self._style = BaseSpinner.UI_STYLES[get_ui_style()]
        self._opaque = kwargs.pop("opaque_for_mouse_events", False)

        self._on_value_changed_fn = value_changed_fn

        if height < SPINNER_MIN_HEIGHT:
            height = SPINNER_MIN_HEIGHT

        icon_height = 6 if height <= 20 else 9
        icon_width = icon_height / 3 * 4

        additional_zstack_args = {}
        if width is not None:
            additional_zstack_args["width"] = width
        self._panel = ui.ZStack(spacing=0, height=height, style=self._style, **additional_zstack_args)
        with self._panel:
            # Use ui.Rectangle instead of OpaqueRectangle to make field editable
            ui.Rectangle(height=height)
            if vertical:
                self._build_vertical(icon_width, icon_height, height)
            else:
                self._build_horizontal(icon_width, icon_height, height)

        # self._widget.visible = False
        self.set_value(self._value)
        self._widget.model.add_value_changed_fn(self._on_value_changed)
        self._widget.model.add_begin_edit_fn(self._on_begin_edit)
        self._widget.model.add_end_edit_fn(self._on_end_edit)

        if auto_subscribe:
            UpdateEventHelper.get_instance().register_update(self)

    def __del__(self):
        UpdateEventHelper.get_instance().deregister_update(self)

    @property
    def max(self):
        return self._max

    @max.setter
    def max(self, value):
        self._max = value

    @property
    def min(self):
        return self._min

    @min.setter
    def min(self, value):
        self._min = value

    @property
    def enabled(self):
        return self._enabled

    @enabled.setter
    def enabled(self, value):
        self._enabled = value
        self._label.enabled = value
        if value:
            if self._spin_up is not None:
                self._spin_up.enabled = True
            if self._spin_down is not None:
                self._spin_down.enabled = True
            if self._spin_left is not None:
                self._spin_left.enabled = True
            if self._spin_right is not None:
                self._spin_right.enabled = True
            self._widget.enabled = True
        else:
            if self._spin_up is not None:
                self._spin_up.enabled = False
            if self._spin_down is not None:
                self._spin_down.enabled = False
            if self._spin_left is not None:
                self._spin_left.enabled = False
            if self._spin_right is not None:
                self._spin_right.enabled = False
            self._widget.enabled = False

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, _value):
        self.set_value(_value)

    def lock(self, locked):
        self._in_edit = locked

    def get_value(self):
        return self._value

    def set_value(self, value):
        value = self._format_value(value)
        if self._min is not None and value < self._min:
            value = self._min
        if self._max is not None and value > self._max:
            value = self._max
        self._value = value
        self._widget.model.set_value(value)
        self._label.text = str(value)

    def _build_content(self, height):
        with ui.ZStack(height=height):
            self._widget = self._create_widget(name="spinner_hide_value")
            with ui.Placer(offset_y=FONT_OFFSET_Y):
                self._label = ui.Label("", alignment=ui.Alignment.CENTER)

    def _build_vertical(self, icon_width, icon_height, height):
        with ui.HStack(opaque_for_mouse_events=self._opaque):
            self._build_content(height)
            with ui.VStack(width=icon_width):
                ui.Spacer()
                self._spin_up = ui.Image(
                    name="up",
                    width=icon_width,
                    height=icon_height,
                    mouse_pressed_fn=(lambda x, y, key, m: self._on_up_clicked(key)),
                    mouse_released_fn=(lambda *_: self._on_up_released()),
                    opaque_for_mouse_events=self._opaque,
                )
                ui.Spacer(height=2)
                self._spin_down = ui.Image(
                    name="down",
                    width=icon_width,
                    height=icon_height,
                    mouse_pressed_fn=lambda x, y, key, m: self._on_down_clicked(key),
                    mouse_released_fn=(lambda *_: self._on_down_released()),
                    opaque_for_mouse_events=self._opaque,
                )
                ui.Spacer()
            ui.Spacer(width=2)

    def _build_horizontal(self, icon_width, icon_height, height):
        with ui.HStack(opaque_for_mouse_events=self._opaque):
            ui.Spacer(width=2)
            with ui.VStack(width=icon_height):
                ui.Spacer()
                self._spin_left = ui.Image(
                    name="left",
                    width=icon_height,
                    height=icon_width,
                    mouse_pressed_fn=(lambda x, y, key, m: self._on_down_clicked(key)),
                    mouse_released_fn=(lambda *_: self._on_down_released()),
                    opaque_for_mouse_events=self._opaque,
                )
                ui.Spacer()
            self._build_content(height)
            with ui.VStack(width=icon_height):
                ui.Spacer()
                self._spin_right = ui.Image(
                    name="right",
                    width=icon_height,
                    height=icon_width,
                    mouse_pressed_fn=lambda x, y, key, m: self._on_up_clicked(key),
                    mouse_released_fn=(lambda *_: self._on_up_released()),
                    opaque_for_mouse_events=self._opaque,
                )
                ui.Spacer()
            ui.Spacer(width=2)

    # Need to subscribe update_event using this member as callback.
    # If not, the widget can still run, but the keep-press-automatically-incress
    # feature will lost.
    def on_update(self, dt):
        self._cur_time += dt

        # Check if button pressed
        factor = 0
        if self._up_pressed:
            factor = self._step
        elif self._down_pressed:
            factor = -self._step
        else:
            if self._need_submit:
                self._need_submit = False
                if self._on_value_changed_fn:
                    self._on_value_changed_fn(self._value)
            return True

        if self._action_time == 0.0:
            self._action_time = self._cur_time + SPINNER_LONG_CLICK_DELAY
        elif self._cur_time > self._action_time:
            self._step_value(factor)
            self._action_time += SPINNER_LONG_CLICK_INTERVAL

        return True

    def _on_up_clicked(self, button):
        # We only respond to left button
        if button != MouseKey.LEFT or not self._enabled:
            return

        self._up_pressed = True
        self._action_time = 0.0
        self._step_value(self._step)

    def _on_up_released(self):
        self._up_pressed = False
        self._need_submit = True

    def _on_down_clicked(self, button):
        # We only respond to left button
        if button != MouseKey.LEFT or not self._enabled:
            return

        self._down_pressed = True
        self._action_time = 0.0
        self._step_value(-self._step)

    def _on_down_released(self):
        self._down_pressed = False
        self._need_submit = True

    def _step_value(self, factor):
        value = self._widget.model.get_value_as_float()
        value += factor
        self.set_value(value)

    def _on_value_changed(self, model):
        if self._in_edit:
            return
        value = model.get_value_as_float()
        self._value = value
        self._need_submit = True

    def _on_begin_edit(self, model):
        self._label.visible = False
        self._widget.name = "spinner_show_value"
        self._in_edit = True

    def _on_end_edit(self, model):
        self._label.visible = True
        self._widget.name = "spinner_hide_value"
        self._in_edit = False
        self.set_value(model.get_value_as_float())
        # value changed function is called before end edit, so have to call it again
        self._on_value_changed(model)

    def _format_value(self, value):
        return value


class FloatSpinner(BaseSpinner):
    def __init__(self, value_changed_fn, **kwargs):
        self._decimal = kwargs.pop("decimal", None)
        self._decimal_factor = None

        super().__init__(value_changed_fn, **kwargs)

    def _create_widget(self, **kwargs):
        return ui.FloatField(**kwargs)

    def _get_value_factor(self):
        number = self._step
        count = 0
        while round(number) < 1:
            number *= 10
            count += 1
        return pow(10, count)

    def _format_value(self, value):
        if self._decimal_factor is None:
            # Used to set display value decimal
            self._decimal_factor = self._get_value_factor() if self._decimal is None else self._decimal

        value = round(value * self._decimal_factor)
        value /= self._decimal_factor
        return value


class IntSpinner(BaseSpinner):
    def __init__(self, value_changed_fn, **kwargs):
        self._use_drag = kwargs.pop("drag", False)
        super().__init__(value_changed_fn, **kwargs)

    def _create_widget(self, **kwargs):
        if self.min is not None:
            kwargs["min"] = self.min
        if self.max is not None:
            kwargs["max"] = self.max
        if self._use_drag:
            # A strange issue is the IntDrag a pixle different from others in v position
            return ui.IntDrag(**kwargs)
        else:
            return ui.IntField(**kwargs)

    def _format_value(self, value):
        return int(value)
