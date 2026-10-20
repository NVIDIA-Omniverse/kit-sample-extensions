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

import carb.settings
from omni import ui
from omni.ui import color as cl

CURRENT_PATH = Path(__file__).parent.absolute()
ICON_PATH = CURRENT_PATH.parent.parent.parent.parent.joinpath("icons")
try:
    UI_THEME = carb.settings.get_settings().get_as_string("/persistent/app/window/uiStyle")
except Exception:
    UI_THEME = None
finally:
    UI_THEME = UI_THEME or "NvidiaDark"


class Colors:
    ss_sliderbar_drag_rect_background = cl.shade(0xFF686868, light=0xFF535354)
    ss_sliderbar_drag_rect_border = cl.shade(0xFF686868, light=0xFF535354)
    ss_sliderbar_drag_label = cl.shade(0xFFF4F4F4, light=0xFFF4F4F4)
    ss_sliderbar_drag_triangle = cl.shade(0xFF686868, light=0xFF535354)
    ss_sliderbar_rect_outer_background = cl.shade(0xFF24211F, light=0xFFC9C9C9)
    ss_sliderbar_rect_outer_border = cl.shade(0xFFF4F4F4, light=0xFF383838)
    ss_sliderbar_rect_end_background = cl.shade(0xFFD1981D, light=0xFF535354)
    ss_sliderbar_rect_start_background = cl.shade(0xFF24211F, light=0xFFC9C9C9)
    ss_sliderbar_circle_cursor = cl.shade(0xFF888888, light=0xFFE0E0E0)
    ss_sliderbar_circle_cursor_hovered = cl.shade(0xFF888888, light=0xFFF4F4F4)
    ss_sliderbar_circle_cursor_pressed = cl.shade(0xFF888888, light=0xFFF4F4F4)


# The slider bar's height
THICKNESS = 16
UI_STYLE = {
    "Rectangle::drag": {
        "background_color": Colors.ss_sliderbar_drag_rect_background,
        "border_width": 1.0,
        "border_color": Colors.ss_sliderbar_drag_rect_border,
        "border_radius": 3.0,
    },
    "Label::drag": {"color": Colors.ss_sliderbar_drag_label},
    "Triangle::drag": {"background_color": Colors.ss_sliderbar_drag_triangle, "border_width": 0},
    "Rectangle::outer": {
        "background_color": Colors.ss_sliderbar_rect_outer_background,
        "border_width": 1.0,
        "border_radius": THICKNESS / 2.0,
    },
    "Rectangle::end": {
        "background_color": Colors.ss_sliderbar_rect_end_background,
        "border_width": 0,
        "border_radius": 0,
    },
    "Rectangle::start": {
        "background_color": Colors.ss_sliderbar_rect_start_background,
        "border_width": 0,
        "border_radius": 0,
    },
    "Circle::cursor": {"background_color": Colors.ss_sliderbar_circle_cursor, "border_width": 0},
    "Circle::cursor:hovered": {"background_color": Colors.ss_sliderbar_circle_cursor_hovered},
    "Circle::cursor:pressed": {"background_color": Colors.ss_sliderbar_circle_cursor_pressed},
    "Image::slider_left": {"image_url": f"{ICON_PATH}/{UI_THEME}/Left.png"},
    "Image::slider_right": {"image_url": f"{ICON_PATH}/{UI_THEME}/Right.png"},
    "Seperator": {"color": 0},
}
