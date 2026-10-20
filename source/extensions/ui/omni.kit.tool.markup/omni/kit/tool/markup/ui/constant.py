# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
from typing import Sequence

from omni import ui
from omni.kit.widgets.custom import COLORS, DarkColors, LightColors

# UI layouts
CONTROL_HEIGHT = 24
SWITCH_HEIGHT = 28
SWITCH_WIDTH = 28
SPINNER_WIDTH = 150
PANEL_PADDING_X = 30
PANEL_SPACING_Y = 10
PANEL_PADDING_INNER_X = 10
ICON_SIZE = 40
SELECTED_BORDER = 2

SHORTEST_ALLOWED_ELEMENT = 0.1

# UI style
LIGHT_STYLE = {
    "Button::image": {
        "background_color": COLORS.TRANSPARENT,
        "stack_direction": ui.Direction.LEFT_TO_RIGHT,
        "padding": 0,
    },
    "Button::image:hovered": {
        "background_color": LightColors.ButtonHovered,
        "stack_direction": ui.Direction.LEFT_TO_RIGHT,
    },
    "Button::image:pressed": {
        "background_color": LightColors.ButtonPressed,
        "stack_direction": ui.Direction.LEFT_TO_RIGHT,
    },
    "Button::align_x": {"background_color": LightColors.Button},
    "Button.Label::align_x": {"color": 0xFF6F6FB0},
    "Button::align_y": {"background_color": LightColors.Button},
    "Button.Label::align_y": {"color": 0xFF8FB08B},
    "Button::align_z": {"background_color": LightColors.Button},
    "Button.Label::align_z": {"color": 0xFFB49F82},
    "Button::control": {"background_color": LightColors.Button},
    "Button.Label::control": {
        # "color": 0xFFB49F82,
    },
    "Rectangle": {"background_color": COLORS.LIGHRT_GARY},
    "TreeView.Item": {"color": COLORS.CLR_E},
    "ScrollingFrame::edit": {"background_color": COLORS.TRANSPARENT, "secondary_color": COLORS.WIDGET_BACKGROUND_LIGHT},
    "VGrid::edit": {
        "background_color": COLORS.WIDGET_BACKGROUND_LIGHT,
        "secondary_color": COLORS.WIDGET_BACKGROUND_LIGHT,
    },
    "Rectangle::border": {"background_color": COLORS.WIDGET_BACKGROUND_LIGHT},
    "Rectangle::detail": {"background_color": COLORS.TRANSPARENT},
    "Rectangle::back": {"background_color": COLORS.WIDGET_BACKGROUND_LIGHT},
    "Label::detail": {"background_color": COLORS.TRANSPARENT, "color": COLORS.CLR_D},
    "Rectangle::detail:selected": {
        "background_color": COLORS.TRANSPARENT,
        "border_color": 0xFFA4936C,
        "border_radius": 3.0,
        "border_width": SELECTED_BORDER,
    },
}


DARK_WINDOW_BACKGROUND = 0xFF2E2E2E
DARK_FONT_COLOR = 0xFF6F6E6D
DARK_STYLE = {
    "Button::image": {
        "background_color": COLORS.TRANSPARENT,
        "stack_direction": ui.Direction.LEFT_TO_RIGHT,
        "padding": 0,
    },
    "Button::image:hovered": {
        "background_color": DarkColors.ButtonHovered,
        "stack_direction": ui.Direction.LEFT_TO_RIGHT,
    },
    "Button::image:pressed": {
        "background_color": DarkColors.ButtonPressed,
        "stack_direction": ui.Direction.LEFT_TO_RIGHT,
    },
    "Button::align_x": {"background_color": DarkColors.Button},
    "Button.Label::align_x": {"color": 0xFF6F6FB0},
    "Button::align_y": {"background_color": DarkColors.Button},
    "Button.Label::align_y": {"color": 0xFF8FB08B},
    "Button::align_z": {"background_color": DarkColors.Button},
    "Button.Label::align_z": {"color": 0xFFB49F82},
    "Button::control": {"background_color": DarkColors.Button},
    "Button.Label::control": {
        # "color": 0xFFB49F82,
    },
    "Rectangle": {"background_color": COLORS.LIGHRT_GARY},
    "TreeView.Item": {"color": COLORS.CLR_E},
    "ScrollingFrame::edit": {"background_color": COLORS.TRANSPARENT},
    "VGrid::edit": {"background_color": COLORS.TRANSPARENT, "secondary_color": COLORS.TRANSPARENT},
    "Rectangle::border": {"background_color": COLORS.TRANSPARENT},
    "Rectangle::detail": {"background_color": COLORS.TRANSPARENT},
    "Rectangle::back": {"background_color": COLORS.TRANSPARENT},
    "Label::detail": {"background_color": COLORS.TRANSPARENT, "color": COLORS.CLR_D},
    "Rectangle::detail:selected": {
        "background_color": COLORS.TRANSPARENT,
        "border_color": 0xFFA4936C,
        "border_radius": 3.0,
        "border_width": SELECTED_BORDER,
    },
}


STYLE = {
    "Rectangle::nv_button": {"background_color": 0x00000000, "border_width": 0},
    "Rectangle::nv_button:hovered": {
        "background_color": 0x40000000,
        "border_width": 2,
        "border_color": 0x30808080,
    },
    "Image": {"color": 0xFFA8A8A8, "fill_policy": ui.FillPolicy.STRETCH},
    "Image:disabled": {"color": 0xFF515151},
    "Image:checked": {"color": 0xFFFFC734},
    "Image::markup_unlock": {
        "color": 0xFF6A6ACB,
        "image_url": "${omni.kit.tool.markup}/data/icons/markup_unlock_tint.svg",
    },
    "Image::markup_unlock:checked": {"color": 0xFF6A6ACB},
    "Image::markup_unlock:disabled": {"color": 0xFF4A4AAB},
    "Image::markup_unlock:hovered": {
        "color": 0xFF6A6ACB,
        "image_url": "${omni.kit.tool.markup}/data/icons/markup_lock_tint.svg",
    },
    "Image::markup_unlock:pressed": {
        "color": 0xFF6A6ACB,
        "image_url": "${omni.kit.tool.markup}/data/icons/markup_lock_tint.svg",
    },
    "Line": {"color": 0xFF9E9E9E},
    "Frame": {"margin": 3, "spacing": 0},
    "Stack": {"margin": 0, "spacing": 0},
}

SETTINGS_UI_HIDE = "/app/window/hideUi"
SETTINGS_MARKUP_ROOT = "/exts/omni.kit.markup.core/"
SETTINGS_MARKUP_ACTIVE = SETTINGS_MARKUP_ROOT + "active_markup"
SETTINGS_MARKUP_EDITING = SETTINGS_MARKUP_ROOT + "editing_markup"

EXTENSION_NAME = "markup"

CURRENT_TOOL_PATH = "/app/viewport/currentTool"
MARKUP_TOOL_SETTINGS_ROOT = "/exts/omni.kit.tool.markup"

SETTINGS_MARKUP_ROOT = "/persistent/exts/omni.kit.tool.markup"
SETTINGS_VIEWPORT_RECT = f"{SETTINGS_MARKUP_ROOT}/viewport_rect"
MARKUP_TOOL_CURRENT = f"{SETTINGS_MARKUP_ROOT}/tool_default"
MARKUP_BLOCK_GESTURES = f"{MARKUP_TOOL_SETTINGS_ROOT}/block_gestures"
MARKUP_TOOL_HIDE = f"{MARKUP_TOOL_SETTINGS_ROOT}/tool_hide"
MARKUP_TOOLBAR_OFFSET = f"{MARKUP_TOOL_SETTINGS_ROOT}/toolbar_offset"
MARKUP_SELECT_CLICK_GESTURE = "markup_select_click"
MARKUP_LETTERBOX_COLOR = f"{MARKUP_TOOL_SETTINGS_ROOT}/letterbox_color"

SETTINGS_PATH_MODAL_TOOL_ACTIVE = "/app/tools/modal_tool_active"


class TOOL_NAME:
    SELECT = "select"
    SHAPES = "shapes"
    ARROW = "arrow"
    LINE = "line"
    DRAW = "draw"
    COMMENT = "comment"


TOOL_NAME_LIST = [val for name, val in vars(TOOL_NAME).items() if not name.startswith("__")]

# default red color
MARKUP_TOOL_SUBTOOL_COLOR_RED = 0xFF0000FF

TOOL_PROPERTIES = {
    TOOL_NAME.SELECT: {},
    TOOL_NAME.SHAPES: {
        "shape": (
            ("rectangle", 0),
            ("circle", 1),
        ),
        "color": (("color", MARKUP_TOOL_SUBTOOL_COLOR_RED),),
        "stroke": (
            ("stroke_s", 1),
            ("stroke_m", 2),
            ("stroke_l", 4),
            ("stroke_xl", 8),
        ),
    },
    TOOL_NAME.ARROW: {
        "arrow": (
            ("arrow_start", 0),
            ("arrow_end", 1),
            ("arrow_double", 2),
        ),
        "color": (("color", MARKUP_TOOL_SUBTOOL_COLOR_RED),),
        "stroke": (
            ("stroke_s", 2),
            ("stroke_m", 4),
            ("stroke_l", 8),
            ("stroke_xl", 12),
        ),
    },
    TOOL_NAME.LINE: {
        "color": (("color", MARKUP_TOOL_SUBTOOL_COLOR_RED),),
        "stroke": (
            ("stroke_s", 2),
            ("stroke_m", 4),
            ("stroke_l", 8),
            ("stroke_xl", 12),
        ),
    },
    TOOL_NAME.DRAW: {
        "color": (("color", MARKUP_TOOL_SUBTOOL_COLOR_RED),),
        "stroke": (
            ("stroke_s", 2),
            ("stroke_m", 4),
            ("stroke_l", 8),
            ("stroke_xl", 12),
        ),
    },
    TOOL_NAME.COMMENT: {
        "color": (("color", MARKUP_TOOL_SUBTOOL_COLOR_RED),),
        "text": (("text_s", 18), ("text_m", 24), ("text_l", 36), ("text_xl", 48)),
    },
}

# The hierachy gathers all configurable default settings
MARKUP_TOOL_DEFAULT_CONFIG = f"{SETTINGS_MARKUP_ROOT}/default_config"
# The setting path configurates the default subtool when entering edit mode
MARKUP_TOOL_DEFAULT_CONFIG_SUBTOOL = f"{MARKUP_TOOL_DEFAULT_CONFIG}/subtool"

# By default, draw is the default subtool when entering edit mode
MARKUP_TOOL_DEFAULT_DRAW_SUBTOOL = TOOL_NAME.DRAW

MARKUP_TOOL_SUBTOOL_SHAPES_SHAPE_RECT = 0  # rectangel
MARKUP_TOOL_SUBTOOL_SHAPE_STROKE_M = 2  # stroke_m
MARKUP_TOOL_SUBTOOL_ARROW_STROKE_M = 4  # stroke_m
MARKUP_TOOL_SUBTOOL_LINE_STROKE_M = 4  # stroke_m
MARKUP_TOOL_SUBTOOL_DRAW_STROKE_M = 4  # stroke_m
MARKUP_TOOL_SUBTOOL_COMMENT_TEXT_M = 24  # text_m
MARKUP_TOOL_SUBTOOL_ARROW_ARROW_END = 1  # arrow_end

MARKUP_TOOL_SUBTOOL_DEFAULT_SETTING = {
    (TOOL_NAME.SHAPES, "shape"): MARKUP_TOOL_SUBTOOL_SHAPES_SHAPE_RECT,
    (TOOL_NAME.SHAPES, "color"): MARKUP_TOOL_SUBTOOL_COLOR_RED,
    (TOOL_NAME.SHAPES, "stroke"): MARKUP_TOOL_SUBTOOL_SHAPE_STROKE_M,
    (TOOL_NAME.ARROW, "arrow"): MARKUP_TOOL_SUBTOOL_ARROW_ARROW_END,
    (TOOL_NAME.ARROW, "color"): MARKUP_TOOL_SUBTOOL_COLOR_RED,
    (TOOL_NAME.ARROW, "stroke"): MARKUP_TOOL_SUBTOOL_ARROW_STROKE_M,
    (TOOL_NAME.LINE, "color"): MARKUP_TOOL_SUBTOOL_COLOR_RED,
    (TOOL_NAME.LINE, "stroke"): MARKUP_TOOL_SUBTOOL_LINE_STROKE_M,
    (TOOL_NAME.DRAW, "color"): MARKUP_TOOL_SUBTOOL_COLOR_RED,
    (TOOL_NAME.DRAW, "stroke"): MARKUP_TOOL_SUBTOOL_DRAW_STROKE_M,
    (TOOL_NAME.COMMENT, "color"): MARKUP_TOOL_SUBTOOL_COLOR_RED,
    (TOOL_NAME.COMMENT, "text"): MARKUP_TOOL_SUBTOOL_COMMENT_TEXT_M,
}


class MARKUP_TOOL_ELEMENT_TYPE:
    SELECT = "Select"
    TEXT = "Label"
    ARROW = "Arrow"
    LINE = "Line"
    CIRCLE = "Circle"
    RECTANGLE = "Rectangle"
    SEGMENT = "LineSegment"
    SHAPE = "Shape"


def float_rgb_to_hex_bgr(color_rgb: Sequence[float]) -> int:
    if len(color_rgb) == 3:  # pragma: no cover
        color_rgb = (*color_rgb, 1)

    color_hex = 0x0
    for x in reversed(color_rgb):
        color_hex = color_hex << 8 | int(x * 255)
    return color_hex


def hex_bgr_to_float_rgb(color: int) -> "tuple[float, float, float]":
    r = (color >> 0 & 0xFF) / 0xFF
    g = (color >> 8 & 0xFF) / 0xFF
    b = (color >> 16 & 0xFF) / 0xFF
    return r, g, b


def hex_abgr_to_float_rgb(color: int) -> "tuple[float, float, float, float]":  # pragma: no cover
    r = (color >> 0 & 0xFF) / 0xFF
    g = (color >> 8 & 0xFF) / 0xFF
    b = (color >> 16 & 0xFF) / 0xFF
    a = (color >> 24 & 0xFF) / 0xFF
    return r, g, b, a


def initialize_defaults():
    import carb.settings

    try:
        settings_interface = carb.settings.get_settings()
    except Exception as e:
        print(f"Error getting settings: {e}")
        return

    settings_interface.set_default(MARKUP_TOOL_HIDE, False)

    default_subtool = settings_interface.get(MARKUP_TOOL_DEFAULT_CONFIG_SUBTOOL)
    if default_subtool in TOOL_NAME_LIST:
        settings_interface.set_default(MARKUP_TOOL_CURRENT, default_subtool)
    else:
        settings_interface.set_default(MARKUP_TOOL_CURRENT, MARKUP_TOOL_DEFAULT_DRAW_SUBTOOL)
        settings_interface.set_default(MARKUP_TOOL_DEFAULT_CONFIG_SUBTOOL, MARKUP_TOOL_DEFAULT_DRAW_SUBTOOL)

    for element, element_info in TOOL_PROPERTIES.items():
        for group, data in element_info.items():
            pth = f"{SETTINGS_MARKUP_ROOT}/{element}/{group}"

            default_value = data[0][1]
            if (element, group) in MARKUP_TOOL_SUBTOOL_DEFAULT_SETTING:
                # Check the existence of configured default
                configured = False
                config_value = settings_interface.get(f"{MARKUP_TOOL_DEFAULT_CONFIG}/{element}/{group}")
                if config_value is not None:  # pragma: no cover
                    if len(data) > 1:
                        # For shapes/shape, arrow/arrow, stroke and text, it needs to be
                        # restricted to a predefined value, config_value is the name as the
                        # first item of the tuple.
                        for n, v in data:
                            if n == config_value:
                                configured = True
                                default_value = v
                                break
                    else:
                        configured = True
                        default_value = config_value

                if not configured:
                    default_value = MARKUP_TOOL_SUBTOOL_DEFAULT_SETTING[(element, group)]

            if group == "color":  # Color is annoying because we want both the hex value, and the floats
                settings_interface.set_default(f"{pth}/abgr_color", default_value)
                settings_interface.set_default(f"{pth}/color", hex_bgr_to_float_rgb(default_value))
            else:
                settings_interface.set_default(pth, default_value)
