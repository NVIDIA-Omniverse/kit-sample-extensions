from enum import Enum
from typing import Dict

import carb
import carb.settings
import omni.ext
import omni.ui as ui
from omni.kit.widgets.custom import COLORS, FontSize, LightColors
from omni.kit.widgets.custom.constant import DarkColors

from .common import get_icon_path
from .tooltips_reader import TooltipsReader


# Defines where to attach a triangle to the tooltip window, making it pointing to the widget with the tooltip
class TrianglePosition(Enum):
    LEFT_UPPER = 0
    LEFT_LOWER = 1
    BOTTOM_LEFT = 2
    BOTTOM_RIGHT = 3
    RIGHT_LOWER = 4
    RIGHT_UPPER = 5
    TOP_RIGHT = 6
    TOP_LEFT = 7


TOOLTIP_BACKGROUND = COLORS.CLR_3  # 0xFFC7F5FC
tooltip_style = {"Tooltip": {"background_color": COLORS.TRANSPARENT, "border_width": 0, "border_radius": 0}}
tooltip_simple_style = {
    "Tooltip": {"background_color": 0xFFC7F5FC, "color": 0xFF4B493B, "border_width": 1, "border_radius": 0}
}
triangle_style = {"background_color": TOOLTIP_BACKGROUND}
tooltip_content_style = {"background_color": TOOLTIP_BACKGROUND, "border_radius": 2}
tooltip_text_style = {"color": COLORS.TEXT_SELECTED, "font_size": FontSize.Large}
tooltip_shortcut_style = {"background_color": TOOLTIP_BACKGROUND, "color": DarkColors.Text, "font_size": FontSize.Large}
tooltip_text_frame_style = {"background_color": TOOLTIP_BACKGROUND, "margin": 0, "padding": 0}
tooltip_description_style = {"color": LightColors.Text, "margin": 0, "padding": 0}
tooltip_image_style = {"border_width": 2, "border_color": 0xFF858585, "margin": 0, "padding": 0}

TOOLTIP_WIDTH = 300
TOOLTIP_HEIGHT = 460
TOOLTIP_SIDE_SPACE = 10
TOOLTIP_CAP_ICON_SIZE = 32
TOOLTIP_SPECIAL_KEY_WIDTH = 60
TOOLTIP_PLUS_WIDTH = 20
TOOLTIP_ALPHABET_KEY_WIDTH = 30
TOOLTIP_IMAGE_WIDTH = 280
TOOLTIP_IMAGE_HEIGHT = 173
TOOLTIP_VERTICAL_SPACE = 8
TOOLTIP_TRIANGLE_WIDTH = 13
TOOLTIP_TRIANGLE_HEIGHT = 20

# this is a roughly calculated length with current font setting. Once font changes, this needs to be revised too.
TEXT_LEN_PER_LINE = 36
TEXT_LINE_HEIGHT = 16
HEIGHT_EXCEPT_TEXT_DESC_COMPLETE = TOOLTIP_VERTICAL_SPACE * 4 + TOOLTIP_CAP_ICON_SIZE + TOOLTIP_IMAGE_HEIGHT
HEIGHT_EXCEPT_TEXT_DESC_SIMPLE = TOOLTIP_VERTICAL_SPACE * 2 + TOOLTIP_CAP_ICON_SIZE
g_tooltip_height = 460
g_text_desc_height = 113

APP_TOOLTIP_ENABLED_SETTING_PATH = "/persistent/app/omniverse/tooltipEnabled"
TOOLTIP_PREFIX = "tname:"


class usd_explorerTooltipExtension(omni.ext.IExt):
    """The entry point for the extension"""

    def on_startup(self):
        pass

    def on_shutdown(self):
        if usd_explorerTooltipWrapper.usd_explorer_tooltip_wrapper_instance:
            usd_explorerTooltipWrapper.usd_explorer_tooltip_wrapper_instance.destroy()
            usd_explorerTooltipWrapper.usd_explorer_tooltip_wrapper_instance = None


class usd_explorerTooltipWrapper:
    usd_explorer_tooltip_wrapper_instance = None

    def __init__(self):
        self._dict = carb.dictionary.get_dictionary()
        settings = carb.settings.get_settings()
        self._is_tooltip_enabled = settings.get_as_bool(APP_TOOLTIP_ENABLED_SETTING_PATH) or False

        self._tooltip_setting_sub = settings.subscribe_to_node_change_events(
            APP_TOOLTIP_ENABLED_SETTING_PATH, self._on_tooltip_setting_change
        )
        self._registered_widgets: Dict[ui.Widget, str] = {}

    def destroy(self):
        self._tooltip_setting_sub = None
        self._is_tooltip_enabled = None
        self._dict = None
        self._registered_widgets = None

    @staticmethod
    def get_instance():
        if usd_explorerTooltipWrapper.usd_explorer_tooltip_wrapper_instance is None:
            usd_explorerTooltipWrapper.usd_explorer_tooltip_wrapper_instance = usd_explorerTooltipWrapper()
        return usd_explorerTooltipWrapper.usd_explorer_tooltip_wrapper_instance

    def set_tooltip(self, widget, tooltip):
        self._registered_widgets[widget] = tooltip
        tooltip_detail = None
        idx = tooltip.find("//")
        if idx > 0:
            tooltip_detail = tooltip[idx + 2 :]
            tooltip = tooltip[:idx]
        self._set_tooltip_internal(widget, tooltip, tooltip_detail)

    def _on_tooltip_setting_change(self, item, event_type):
        enabled = self._dict.get(item)
        if self._is_tooltip_enabled != enabled:
            self._is_tooltip_enabled = enabled
            for widget, tooltip in self._registered_widgets.items():
                tooltip_detail = None
                idx = tooltip.find("//")
                if idx > 0:
                    tooltip_detail = tooltip[idx + 2 :]
                    tooltip = tooltip[:idx]
                self._set_tooltip_internal(widget, tooltip, tooltip_detail)

    def _set_tooltip_internal(self, widget, tooltip, tooltip_detail):
        if self._is_tooltip_enabled and tooltip.startswith(TOOLTIP_PREFIX):
            widget.set_tooltip_fn(lambda w=widget, name=tooltip: self._set_custom_tooltip(w, name))
        else:
            if tooltip_detail is None:
                tooltip_txt = tooltip[len(TOOLTIP_PREFIX) : len(tooltip)]
            else:
                tooltip_txt = tooltip_detail

            widget.set_style(tooltip_simple_style)
            widget.tooltip_offset_x = 0
            widget.tooltip_offset_y = 0
            widget.set_tooltip(tooltip_txt)

    def _set_custom_tooltip(self, widget, tooltip):
        # to hack the issue that no tooltip will be created if it's disabled and then reenbled.
        # give it an offset will force recreation
        widget.tooltip_offset_x = 1

        if self._is_tooltip_enabled and tooltip.startswith(TOOLTIP_PREFIX):
            tooltip_name = tooltip[len(TOOLTIP_PREFIX) : len(tooltip)]
            tooltips_reader = TooltipsReader()
            tooltip_data = tooltips_reader.get_tooltip_by_name(tooltip_name)
            if tooltip_data is None:
                carb.log_warn(f"Please check if tooltip for {tooltip_name} is defined correctly.")
            shortcut, doc_link, text_desc, image_desc = tooltip_data
            widget.set_style(tooltip_style)
            try:
                global g_text_desc_height
                line_count = int(len(text_desc) / TEXT_LEN_PER_LINE) + 2
                g_text_desc_height = line_count * TEXT_LINE_HEIGHT

                # a valid png/svg name is at least 5 letters long
                global g_tooltip_height
                if len(image_desc) > 5:
                    g_tooltip_height = HEIGHT_EXCEPT_TEXT_DESC_COMPLETE + g_text_desc_height
                else:
                    g_tooltip_height = HEIGHT_EXCEPT_TEXT_DESC_SIMPLE + g_text_desc_height
                self._set_tooltip(widget, tooltip_name, shortcut, doc_link, text_desc, image_desc)
            except Exception as e:
                carb.log_warn(f"{e}")

    def _set_tooltip(self, widget, tooltip_name, shortcut, doc_link, text_desc, image_desc):
        triangle_position = self._get_triangle_position(widget)

        if triangle_position == TrianglePosition.LEFT_UPPER:
            self._set_tooltip_at_left_upper(widget, tooltip_name, shortcut, doc_link, text_desc, image_desc)
        elif triangle_position == TrianglePosition.LEFT_LOWER:
            self._set_tooltip_at_left_lower(widget, tooltip_name, shortcut, doc_link, text_desc, image_desc)
        elif triangle_position == TrianglePosition.BOTTOM_LEFT:
            self._set_tooltip_at_bottom_left(widget, tooltip_name, shortcut, doc_link, text_desc, image_desc)
        elif triangle_position == TrianglePosition.RIGHT_LOWER:
            self._set_tooltip_at_right_lower(widget, tooltip_name, shortcut, doc_link, text_desc, image_desc)
        elif triangle_position == TrianglePosition.RIGHT_UPPER:
            self._set_tooltip_at_right_upper(widget, tooltip_name, shortcut, doc_link, text_desc, image_desc)
        else:  # all other cases are treated as top left
            self._set_tooltip_at_top_left(widget, tooltip_name, shortcut, doc_link, text_desc, image_desc)

    def _get_triangle_position(self, widget):
        OFFSET_WIDTH = 30
        OFFSET_HEIGHT = 30
        SIZE_MULTIPLIER = 1
        tw = TOOLTIP_WIDTH * SIZE_MULTIPLIER + OFFSET_WIDTH
        th = g_tooltip_height * SIZE_MULTIPLIER + OFFSET_HEIGHT

        main_window_width = ui.Workspace.get_main_window_width()
        main_window_height = ui.Workspace.get_main_window_height()

        if main_window_width - widget.screen_position_x < tw:
            if main_window_height - widget.screen_position_y < th:
                return TrianglePosition.RIGHT_LOWER
            else:
                return TrianglePosition.RIGHT_UPPER
        else:
            if main_window_height - widget.screen_position_y < th:
                return TrianglePosition.BOTTOM_LEFT
            else:
                return TrianglePosition.TOP_LEFT

    # to get different parts of a shortcut, which could be a combination of Control/Alt/Shift + Key, or just a Key
    def _get_shortcut_parts(self, shortcut):
        shortcut_s = shortcut.replace(" ", "")
        special_key = ""
        alphabet_key = ""

        if len(shortcut_s) == 0:
            return special_key, alphabet_key

        plus_index = shortcut_s.find("+")
        if plus_index == 0 or plus_index == len(shortcut_s) - 1:
            return special_key, alphabet_key

        if plus_index > 0:
            special_key = shortcut_s[0:plus_index]
            alphabet_key = shortcut_s[plus_index + 1 : plus_index + 2]
        else:
            # if there is no + sign, take the first letter only
            alphabet_key = shortcut_s[0:1]

        return special_key, alphabet_key

    def _get_tooltip_image_path(self, image_desc):
        return get_icon_path(image_desc)

    def _build_shortcut_ui(self, shortcut):
        special_key, alphabet_key = self._get_shortcut_parts(shortcut)
        if len(alphabet_key) > 0:
            with ui.HStack():
                ui.Spacer()
                with ui.ZStack(width=TOOLTIP_SPECIAL_KEY_WIDTH + TOOLTIP_PLUS_WIDTH):
                    ui.Rectangle(style=tooltip_shortcut_style)
                    if len(special_key) > 0:
                        with ui.HStack():
                            ui.Label(special_key, alignment=ui.Alignment.RIGHT_CENTER, style=tooltip_shortcut_style)
                            ui.Label(
                                "+",
                                width=TOOLTIP_PLUS_WIDTH,
                                alignment=ui.Alignment.CENTER,
                                style=tooltip_shortcut_style,
                            )
                with ui.ZStack(width=TOOLTIP_ALPHABET_KEY_WIDTH):
                    ui.Rectangle(style=tooltip_shortcut_style)
                    ui.Image(get_icon_path("Key.png"))
                    ui.Label(alphabet_key, alignment=ui.Alignment.CENTER, style=tooltip_shortcut_style)

    def _build_tooltip_content(self, widget, tooltip_name, shortcut, doc_link, text_desc, image_desc):
        with ui.ZStack():
            ui.Rectangle(width=TOOLTIP_WIDTH, height=g_tooltip_height, style=tooltip_content_style)
            with ui.HStack():
                ui.Spacer(width=TOOLTIP_SIDE_SPACE)
                with ui.VStack():
                    ui.Spacer(height=TOOLTIP_SIDE_SPACE)
                    with ui.HStack(height=32):
                        with ui.HStack(width=ui.Percent(60)):
                            ui.Label(tooltip_name, style=tooltip_text_style, width=0)
                            ui.Spacer(width=ui.Pixel(8))
                            ui.Image(
                                get_icon_path("Learn_Icon.png"),
                                width=TOOLTIP_CAP_ICON_SIZE,
                                height=TOOLTIP_CAP_ICON_SIZE,
                                alignment=ui.Alignment.RIGHT_CENTER,
                            )
                            ui.Spacer()
                        self._build_shortcut_ui(shortcut)

                    with ui.ScrollingFrame(
                        width=ui.Percent(100),
                        height=g_text_desc_height,
                        horizontal_scrollbar_policy=ui.ScrollBarPolicy.SCROLLBAR_ALWAYS_OFF,
                        vertical_scrollbar_policy=ui.ScrollBarPolicy.SCROLLBAR_ALWAYS_OFF,
                        style=tooltip_text_frame_style,
                    ):
                        ui.Label(text_desc, width=ui.Percent(100), word_wrap=True, style=tooltip_description_style)

                    if len(image_desc) >= 5:
                        ui.Spacer(height=TOOLTIP_VERTICAL_SPACE)
                        ui.Image(
                            self._get_tooltip_image_path(image_desc),
                            fill_policy=ui.FillPolicy.STRETCH,
                            width=TOOLTIP_IMAGE_WIDTH,
                            height=TOOLTIP_IMAGE_HEIGHT,
                            style=tooltip_image_style,
                        )
                ui.Spacer(width=TOOLTIP_SIDE_SPACE)

    def _set_tooltip_at_top_left(self, widget, tooltip_name, shortcut, doc_link, text_desc, image_desc):
        widget.tooltip_offset_y = 30
        widget.tooltip_offset_x = 0
        with ui.VStack(width=TOOLTIP_WIDTH):
            with ui.HStack(height=TOOLTIP_TRIANGLE_HEIGHT, style={"margin": 0, "padding": 0}):
                ui.Spacer(width=10)
                ui.Triangle(
                    height=TOOLTIP_TRIANGLE_HEIGHT,
                    width=TOOLTIP_TRIANGLE_WIDTH,
                    style=triangle_style,
                    alignment=ui.Alignment.CENTER_TOP,
                )
                ui.Spacer()
            self._build_tooltip_content(widget, tooltip_name, shortcut, doc_link, text_desc, image_desc)

    def _set_tooltip_at_left_upper(self, widget, tooltip_name, shortcut, doc_link, text_desc, image_desc):
        widget.tooltip_offset_y = -10
        widget.tooltip_offset_x = 30

        with ui.HStack(width=TOOLTIP_WIDTH + TOOLTIP_TRIANGLE_HEIGHT, style=tooltip_style):
            with ui.VStack(width=TOOLTIP_TRIANGLE_HEIGHT):
                ui.Spacer(height=10)
                ui.Triangle(
                    width=TOOLTIP_TRIANGLE_HEIGHT,
                    height=TOOLTIP_TRIANGLE_WIDTH,
                    style=triangle_style,
                    alignment=ui.Alignment.LEFT_CENTER,
                )
                ui.Spacer()
            self._build_tooltip_content(widget, tooltip_name, shortcut, doc_link, text_desc, image_desc)

    def _set_tooltip_at_left_lower(self, widget, tooltip_name, shortcut, doc_link, text_desc, image_desc):
        widget.tooltip_offset_y = -g_tooltip_height - 22
        widget.tooltip_offset_x = 30

        with ui.HStack(width=TOOLTIP_WIDTH + TOOLTIP_TRIANGLE_HEIGHT, style=tooltip_style):
            with ui.VStack(width=TOOLTIP_TRIANGLE_HEIGHT):
                ui.Spacer()
                ui.Triangle(
                    width=TOOLTIP_TRIANGLE_HEIGHT,
                    height=TOOLTIP_TRIANGLE_WIDTH,
                    style=triangle_style,
                    alignment=ui.Alignment.LEFT_CENTER,
                )

                ui.Spacer(height=10)
            self._build_tooltip_content(widget, tooltip_name, shortcut, doc_link, text_desc, image_desc)

    def _set_tooltip_at_bottom_left(self, widget, tooltip_name, shortcut, doc_link, text_desc, image_desc):
        widget.tooltip_offset_y = -g_tooltip_height - TOOLTIP_TRIANGLE_HEIGHT  # - widget.height.value - 30
        widget.tooltip_offset_x = 0
        with ui.VStack(width=TOOLTIP_WIDTH, style=tooltip_style):
            self._build_tooltip_content(widget, tooltip_name, shortcut, doc_link, text_desc, image_desc)

            with ui.HStack(height=TOOLTIP_TRIANGLE_HEIGHT):
                ui.Spacer(width=10)
                ui.Triangle(
                    height=TOOLTIP_TRIANGLE_HEIGHT,
                    width=TOOLTIP_TRIANGLE_WIDTH,
                    style=triangle_style,
                    alignment=ui.Alignment.CENTER_BOTTOM,
                )
                ui.Spacer()

    def _set_tooltip_at_right_lower(self, widget, tooltip_name, shortcut, doc_link, text_desc, image_desc):
        widget.tooltip_offset_y = -g_tooltip_height + widget.height.value / 2
        widget.tooltip_offset_x = -TOOLTIP_WIDTH - TOOLTIP_TRIANGLE_HEIGHT

        with ui.HStack(width=TOOLTIP_WIDTH + TOOLTIP_TRIANGLE_HEIGHT, style=tooltip_style):
            self._build_tooltip_content(widget, tooltip_name, shortcut, doc_link, text_desc, image_desc)

            with ui.VStack(width=TOOLTIP_TRIANGLE_HEIGHT):
                ui.Spacer()
                ui.Triangle(
                    width=TOOLTIP_TRIANGLE_HEIGHT,
                    height=TOOLTIP_TRIANGLE_WIDTH,
                    style=triangle_style,
                    alignment=ui.Alignment.RIGHT_CENTER,
                )
                ui.Spacer(height=10)

    def _set_tooltip_at_right_upper(self, widget, tooltip_name, shortcut, doc_link, text_desc, image_desc):
        widget.tooltip_offset_y = 0
        widget.tooltip_offset_x = -TOOLTIP_WIDTH - TOOLTIP_TRIANGLE_HEIGHT

        with ui.HStack(width=TOOLTIP_WIDTH + TOOLTIP_TRIANGLE_HEIGHT, style=tooltip_style):
            self._build_tooltip_content(widget, tooltip_name, shortcut, doc_link, text_desc, image_desc)

            with ui.VStack(width=TOOLTIP_TRIANGLE_HEIGHT):
                ui.Spacer(height=10)
                ui.Triangle(
                    width=TOOLTIP_TRIANGLE_HEIGHT,
                    height=TOOLTIP_TRIANGLE_WIDTH,
                    style=triangle_style,
                    alignment=ui.Alignment.RIGHT_CENTER,
                )
                ui.Spacer()


def set_usd_explorer_tooltip(widget, tooltip):
    usd_explorerTooltipWrapper.get_instance().set_tooltip(widget, tooltip)
