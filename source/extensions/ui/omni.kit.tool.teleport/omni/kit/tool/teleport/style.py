# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
from omni import ui
from omni.ui import color as cl


class Colors:
    window = cl.shade(0xA0000000, light=0xA0000000)
    transparent = cl.shade(0x0, light=0x0)
    line = cl.shade(0xFF9E9E9E, light=0xFF9E9E9E)
    tooltip = cl.shade(0xFFA5C5CA, light=0xFFA5C5CA)
    shortcut = cl.shade(0xFF444444, light=0xFF444444)
    shortcut_white = cl.shade(0xFFCCCCCC, light=0xFFCCCCCC)
    Background = ui.color.shade(0xFF23211F, light=0xFF535354)
    Text = ui.color.shade(0xFFA1A1A1, light=0xFFE0E0E0)
    DarkText = ui.color.shade(0xFF504F50, light=0xFFA1A1A1)
    ResetInvalid = ui.color.shade(0xFF505050)
    Reset = ui.color.shade(0xFFA07D4F)
    Line = ui.color.shade(0x338A8777)


class ConstSize:
    Radius = 2


FONT_SIZE = 14
# UI style
STYLE = {
    "Window": {"background_color": Colors.window, "margin": 0.0, "margin_height": 0, "margin_width": 0, "padding": 0},
    "ImageButton": {"background_color": Colors.transparent, "border_width": 0, "border_radius": 2.0},
    "Line": {"color": Colors.line},
    "Rectangle::background": {"background_color": 0xA0000000, "border_width": 0},
    "Rectangle::background:hovered": {"background_color": 0xA0000000, "border_width": 1, "border_color": 0x30808080},
    "Rectangle::window_dimension": {"background_color": 0x00000000, "border_width": 0, "border_radius": 0},
}

TOOLTIP_STYLE = {
    "Triangle::tooltip": {
        "background_color": Colors.tooltip,
        "border_width": 0,
        "border_radius": 1,
        "margin": 0.0,
        "margin_height": 0,
        "margin_width": 0,
        "padding": 0,
    },
    "Rectangle::tooltip": {
        "background_color": Colors.tooltip,
        "border_width": 0,
        "border_radius": 2,
        "margin": 0.0,
        "margin_height": 0,
        "margin_width": 0,
        "padding": 0,
    },
    "Label::shortcut": {"color": Colors.shortcut, "font_size": FONT_SIZE},
    "Label::shortcut_white": {"color": Colors.shortcut_white, "font_size": FONT_SIZE},
    "Image::tooltip": {"margin": 0, "padding": 0},
    "Tooltip": {"background_color": Colors.transparent, "border_width": 0, "border_radius": 0},
}

PREFERENCE_PAGE_STYLES = {
    "Reset_invalid.Rect": {"background_color": Colors.ResetInvalid, "border_radius": ConstSize.Radius},
    "Reset.Rect": {"background_color": Colors.Reset, "border_radius": ConstSize.Radius},
    "Setting.Field": {"color": Colors.Text, "background_color": Colors.Background},
    "Setting.Field:disabled": {"color": Colors.DarkText},
    "Setting.Label": {"color": Colors.Text},
    "Setting.Label:disabled": {"color": Colors.DarkText},
    "Seperator": {"color": Colors.Line},
}
