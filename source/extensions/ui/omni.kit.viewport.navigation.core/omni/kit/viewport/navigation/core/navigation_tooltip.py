from enum import IntEnum
from typing import Dict, Optional

import carb
import carb.input
import omni.ui as ui

from .style import TOOLTIP_STYLE, Colors


def get_nominal_font_size(real_size):
    settings = carb.settings.get_settings()
    app_font_size = 14.0
    app_font_size_str = settings.get("/app/font/size")
    if app_font_size_str is not None:
        app_font_size = float(app_font_size_str)
    nominal_size = round(14.0 * real_size / app_font_size)
    return nominal_size


class ViewportNavigationTooltip:
    __singleton = None
    __should_show_tooltip = True

    POINTER_WIDTH = 8
    POINTER_HEIGHT = 12
    TOOLTIP_SIDE_SPACE = 5
    BOUNDARY = 7

    def __init__(self, upper_offset, lower_offset, limited_rect):
        self._func_name = None

        self._upper_offset = upper_offset
        self._lower_offset = lower_offset
        self._limited_rect = limited_rect

        self._placer_content = ui.Placer(style=TOOLTIP_STYLE)
        self._placer_pointer = ui.Placer(style=TOOLTIP_STYLE)

        ViewportNavigationTooltip.__singleton = self

    @staticmethod
    def build_space(self):
        with ui.VStack():
            ui.Spacer(height=ViewportNavigationTooltip.TOOLTIP_SIDE_SPACE)
            with ui.HStack(height=0):
                ui.Spacer(width=ViewportNavigationTooltip.TOOLTIP_SIDE_SPACE)
                ViewportNavigationTooltip._build_space_shortcut()
                ui.Spacer(width=ViewportNavigationTooltip.TOOLTIP_SIDE_SPACE)

    @staticmethod
    def build_shortcut(key, size):
        with ui.VStack():
            ui.Spacer(height=ViewportNavigationTooltip.BOUNDARY)
            with ui.HStack(height=0):
                ui.Spacer(width=ViewportNavigationTooltip.BOUNDARY)
                ViewportNavigationTooltip._build_shortcut_ui(key, size)
                ui.Spacer(width=ViewportNavigationTooltip.BOUNDARY)

    @staticmethod
    def build_label(text):
        with ui.VStack():
            ui.Spacer(height=ViewportNavigationTooltip.TOOLTIP_SIDE_SPACE)
            with ui.HStack(height=0):
                ui.Spacer(width=ViewportNavigationTooltip.TOOLTIP_SIDE_SPACE)
                ui.Label(text, alignment=ui.Alignment.CENTER, name="shortcut")
                ui.Spacer(width=ViewportNavigationTooltip.TOOLTIP_SIDE_SPACE)

    @staticmethod
    def set_visible(visible):
        instance = ViewportNavigationTooltip.__singleton
        if instance is None:
            return
        instance.__should_show_tooltip = visible

    @staticmethod
    def create(upper_offset, lower_offset, limited_rect):
        # OM-84675: It create twice with USD Explorer app, so need clear and create again
        if ViewportNavigationTooltip.__singleton:
            ViewportNavigationTooltip.__singleton = None
        if ViewportNavigationTooltip.__singleton is None:
            ViewportNavigationTooltip.__singleton = ViewportNavigationTooltip(upper_offset, lower_offset, limited_rect)

    @staticmethod
    def _build_shortcut_ui(key, size, isdark=False):
        font_size = get_nominal_font_size(14)

        if isdark:
            style = {
                "Label::keyboard": {"color": Colors.shortcut_white, "font_size": font_size},
                "Rectangle::keyboard": {
                    "background_color": 0xFF444444,
                    "border_width": 1,
                    "border_radius": 2,
                    "border_color": 0xFF444444,
                },
            }
        else:
            style = {
                "Label::keyboard": {"color": Colors.shortcut, "font_size": font_size},
                "Rectangle::keyboard": {
                    "background_color": 0x00000000,
                    "border_width": 1,
                    "border_radius": 2,
                    "border_color": 0xFF444444,
                },
            }

        with ui.HStack(spacing=0, width=size, style=style):
            d = (size - 16) / 2
            ui.Spacer(width=d)
            with ui.VStack(height=size):
                ui.Spacer(height=d)
                with ui.ZStack():
                    ui.Rectangle(name="keyboard", width=16, height=16)
                    ui.Label(key, alignment=ui.Alignment.CENTER, name="keyboard", width=16, height=16)
                ui.Spacer()
            ui.Spacer()

    @staticmethod
    def _build_space_shortcut():
        font_size = get_nominal_font_size(14)

        style = {
            "Label::keyboard": {"color": Colors.shortcut, "font_size": font_size},
            "Rectangle::keyboard": {
                "background_color": 0x00000000,
                "border_width": 1,
                "border_radius": 2,
                "border_color": 0xFF444444,
            },
        }

        size = 40
        with ui.HStack(spacing=0, width=size, style=style):
            ui.Spacer(width=1)
            with ui.VStack(height=size):
                ui.Spacer(height=1)
                with ui.ZStack():
                    ui.Rectangle(name="keyboard", width=size - 2, height=16)
                    ui.Label("Space", alignment=ui.Alignment.CENTER, name="keyboard", width=size - 2, height=16)
                ui.Spacer()
            ui.Spacer()

    @staticmethod
    def destroy():
        ViewportNavigationTooltip.__singleton = None

    @staticmethod
    def show(widget, func_name, build_tooltip_fn):
        instance = ViewportNavigationTooltip.__singleton
        if instance is None:
            carb.log_error("Navigation tooltip is not initialized before use it")
            return

        if not instance.__should_show_tooltip:
            return
        instance._show_tooltip_for(widget, func_name, build_tooltip_fn)

    @staticmethod
    def show_tooltip():
        return ViewportNavigationTooltip.__should_show_tooltip

    @staticmethod
    def hide(func_name):
        if ViewportNavigationTooltip.__singleton is None:
            return
        if ViewportNavigationTooltip.__singleton._func_name == func_name:
            ViewportNavigationTooltip.__singleton._placer_content.clear()
            ViewportNavigationTooltip.__singleton._placer_pointer.clear()

    def _show_tooltip_for(self, widget, func_name, build_tooltip_fn):
        # Content size
        content_width = 0
        content_height = 0

        self._placer_content.clear()
        self._placer_pointer.clear()

        # Build the tooltip content
        with self._placer_content:
            with ui.ZStack(width=0, height=0, spacing=0):
                content_rc = ui.Rectangle(name="tooltip", width=10, height=10)
                content_width, content_height = build_tooltip_fn()
                # to support no tooltip button
                if content_width == 0 and content_height == 0:
                    content_rc.visible = False
                    return
            content_rc.width = ui.Pixel(content_width)
            content_rc.height = ui.Pixel(content_height)

        # Determine the position of the tooltip
        tooltip_height = ViewportNavigationTooltip.POINTER_HEIGHT + content_height
        x = widget.screen_position_x - self._limited_rect.left
        y = widget.screen_position_y - self._limited_rect.top

        h = widget.height
        w = widget.width

        if y + h + tooltip_height + self._lower_offset > self._limited_rect.height:
            # Make the tooltip above the widget
            # don't know why this could trigger the content show
            self._placer_content.offset_y = 10
            self._placer_pointer.offset_y = y - ViewportNavigationTooltip.POINTER_HEIGHT - self._upper_offset
            self._placer_content.offset_y = y - tooltip_height - self._upper_offset + 1
            align = ui.Alignment.CENTER_BOTTOM
            pass
        else:
            # Make the tooltip below the widget
            self._placer_content.offset_y = 11
            self._placer_pointer.offset_y = y + h + self._lower_offset
            self._placer_content.offset_y = y + h + ViewportNavigationTooltip.POINTER_HEIGHT + self._lower_offset - 1
            align = ui.Alignment.CENTER_TOP
            pass

        with self._placer_pointer:
            ui.Triangle(
                name="tooltip",
                width=ViewportNavigationTooltip.POINTER_WIDTH,
                height=ViewportNavigationTooltip.POINTER_HEIGHT,
                alignment=align,
            )

        self._placer_pointer.offset_x = x + (w - ViewportNavigationTooltip.POINTER_WIDTH) / 2
        if x < (content_width - w) / 2:
            self._placer_content.offset_x = 0
        elif x + w + content_width / 2 > self._limited_rect.width:
            self._placer_content.offset_x = self._limited_rect.width - content_width
        else:
            self._placer_content.offset_x = x + (w - content_width) / 2

        self._func_name = func_name
