# SPDX-FileCopyrightText: Copyright (c) 2022-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.


import omni.ui as ui

from .utils import get_icon

FRAME_STYLE = {"CollapsableFrame": {"border_radius": 5, "border_width": 0, "padding": 10, "margin": 4}}

HEADER_STYLE = {
    "padding": 0,
    "Button": {"stack_direction": ui.Direction.LEFT_TO_RIGHT},
}

TABLE_HEADER_STYLE = {
    "margin": 6,
}

TREE_VIEW_STYLE = {
    "TreeView.Item.Title": {
        "margin": 4,
    },
    "TreeView.Item": {
        "margin": 4,
    },
    "TreeView.Item.Title:selected": {
        "color": 0xFF23211F,
    },
    "TreeView.ScrollingFrame": {"background_color": 0xFF4A4A4A},
}

CONTROL_STATE_STYLE = {"margin": 0, "border_radius": 2}

ARG_STYLE = {
    "": {"margin": 4, "color": 0xFFA0A0A0, "border_radius": 2},
    ":disabled": {
        "color": 0x44A0A0A0,
    },
}


BOOL_ARG_STYLE = {
    "margin": 6,
    "color": 0xFF000000,
    "border_radius": 2,
    "background_color": 0xFF9A9A9A,
    "font_size": 12,
}

BUTTON_STYLE = {
    "padding": 2,
    "Button": {"stack_direction": ui.Direction.LEFT_TO_RIGHT},
}

LINE_STYLE = {
    "color": 0xFF505050,
}

IMAGE_COLOR = 0xFF505050

DRAG_BUTTON_STYLE = {
    "Button.Image::drag": {
        "alignment": ui.Alignment.CENTER,
        "color": IMAGE_COLOR,
        "background_color": 0x0,
        "image_url": get_icon("drag.svg"),
    },
    "Button": {
        "background_color": 0x0,
    },
    "Button:hovered": {
        "background_color": 0x0,
    },
    "Button:pressed": {
        "background_color": 0x0,
    },
}

TAB_GROUP_STYLE = {
    "TabGroupBorder": {
        "background_color": ui.color.transparent,
    },
    "Rectangle::TabGroupHeader": {
        "background_color": ui.color.transparent,
    },
    "ZStack::TabGroupHeader": {"margin_width": 1},
}

TAB_STYLE = {
    "": {
        "background_color": ui.color(31),
        "corner_flag": ui.CornerFlag.TOP,
        "border_radius": 4,
        "color": ui.color(127),
    },
    ":selected": {"background_color": ui.color(56), "color": ui.color(203)},
    "Label": {
        "margin_width": 8,
        "margin_height": 6,
        "background_color": ui.color(220),
    },
    "Button": {
        "margin_width": 0,
        "margin_height": 0,
    },
}

SPLITTER_STYLE = {
    "Splitter": {"background_color": 0x0, "margin_width": 0},
    "Splitter:hovered": {"background_color": 0xFFB0703B},
    "Splitter:pressed": {"background_color": 0xFFB0703B},
}

ATTRIBUTE_STYLE = {
    "": {"margin_width": 4, "margin_height": 0, "color": 0xFFA0A0A0, "border_radius": 2},
    ":disabled": {
        "color": 0x44A0A0A0,
    },
    ":hovered": {
        "background_color": ui.color(46, 46, 46),
    },
}
