# SPDX-FileCopyrightText: Copyright (c) 2022-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
__all__ = ["minibar_style"]

import pathlib

import omni.kit.app
import omni.ui as ui
from omni.ui import color as cl
from omni.ui import url

# Pre-defined constants. It's possible to change them runtime.
cl.minibar_border = 0xFFC2C2C2
cl.minibar_second = 0xFFFFFFFF
cl.minibar_bg = 0xA0000000
cl.minibar_fg = cl("#1f1f1f")
cl.minibar_hover = 0x40000000

MINIBAR_WIDTH = 400
MINIBAR_MIN_WIDTH = 300
MINIBAR_MAX_WIDTH = 800
MINIBAR_HEIGHT = 30
RANGE_HANDLE_WIDTH = 34
BUTTON_IMAGE_SIZE = 16
CORSOR_WIDTH = 3
MARGIN_HEIGHT = 5
EXTENSION_FOLDER_PATH = pathlib.Path(__file__).parent.parent.parent.parent.parent

url.minibar_icon_play = f"{EXTENSION_FOLDER_PATH}/data/play.svg"
url.minibar_icon_pause = f"{EXTENSION_FOLDER_PATH}/data/pause_blue.svg"
url.minibar_icon_loop = f"{EXTENSION_FOLDER_PATH}/data/loop.svg"
url.minibar_icon_loop_checked = f"{EXTENSION_FOLDER_PATH}/data/loop_active.svg"
url.minibar_icon_backward = f"{EXTENSION_FOLDER_PATH}/data/step_backward.svg"
url.minibar_icon_forward = f"{EXTENSION_FOLDER_PATH}/data/step_forward.svg"
url.minibar_icon_close = f"{EXTENSION_FOLDER_PATH}/data/close.svg"
url.minibar_icon_speed_1x = f"{EXTENSION_FOLDER_PATH}/data/rate_1x_dark.svg"
url.minibar_icon_speed_2x = f"{EXTENSION_FOLDER_PATH}/data/rate_2x_dark.svg"
url.minibar_icon_speed_4x = f"{EXTENSION_FOLDER_PATH}/data/rate_4x_dark.svg"
url.minibar_icon_speed_8x = f"{EXTENSION_FOLDER_PATH}/data/rate_8x_dark.svg"


# The main style dict
minibar_style = {
    "Rectangle": {
        "background_color": cl.minibar_bg,
        "border_radius": 0,
    },
    "Button": {
        "background_color": cl.transparent,
        "margin_height": MARGIN_HEIGHT,
        "margin_width": 0,
        # "border_color": cl.minibar_border,
        # "border_width": 1,
    },
    "Button:hovered": {
        "background_color": cl.minibar_hover,
    },
    "Button.Image::play": {"image_url": url.minibar_icon_play},
    "Button.Image::play:checked": {"image_url": url.minibar_icon_pause},
    "Button.Image::loop": {"image_url": url.minibar_icon_loop},
    "Button.Image::loop:checked": {"image_url": url.minibar_icon_loop_checked},
    "Button.Image::step_backward": {"image_url": url.minibar_icon_backward},
    "Button.Image::step_forward": {"image_url": url.minibar_icon_forward},
    "Button.Image::close": {"image_url": url.minibar_icon_close},
    "Button.Image::speed_1x": {"image_url": url.minibar_icon_speed_1x},
    "Button.Image::speed_2x": {"image_url": url.minibar_icon_speed_2x},
    "Button.Image::speed_4x": {"image_url": url.minibar_icon_speed_4x},
    "Button.Image::speed_8x": {"image_url": url.minibar_icon_speed_8x},
    "Button::loop": {"background_color": cl.transparent},
    "Button::loop:checked": {"background_color": cl.transparent},
    "Button::play:checked": {"background_color": cl.transparent},
    "Rectangle::cursor": {
        "background_color": cl.minibar_second,
        "margin_height": 8,
        "margin_width": 0,
        "border_radius": 1,
    },
    "Field": {
        "background_color": 0xFF000000,
        "padding": 2,
        "margin_height": MARGIN_HEIGHT,
        "margin_width": 0,
        "border_radius": 2,
        "font_size": 16,
    },
    "Slider::timeline": {
        "background_color": cl.minibar_fg,
        "draw_mode": ui.SliderDrawMode.HANDLE,
        "secondary_color": cl.transparent,
        "secondary_selected_color": cl.transparent,
        "border_color": cl.minibar_border,
        "padding": 2,
        "margin_height": MARGIN_HEIGHT,
        "margin_width": 0,
        "border_width": 1,
        "border_radius": 4,
        "font_size": 16,
    },
    "Label::short_name": {"font_size": 14},
}
