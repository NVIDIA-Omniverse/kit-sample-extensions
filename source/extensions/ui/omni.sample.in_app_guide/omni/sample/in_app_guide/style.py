# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

"""UI style definitions for the In-App Guide.

This module contains style dictionaries and constants that define the visual appearance
of the In-App Guide UI components, including colors, fonts, icons, and widget styles.
"""

import omni.ui as ui
from omni.ui import color as cl
from omni.ui import constant as fl
from omni.ui import url

cl.dark_color = cl("#a9974a")
cl.light_color = cl("#c9bb7f")
fl.button_font_size = 18
cl.button_hovered_background = cl("#827127")
cl.button_pressed_background = cl("#665715")
url.close_icon_url = "${omni.sample.in_app_guide}/data/close.svg"
url.next_icon_url = "${omni.sample.in_app_guide}/data/next.svg"
url.next_disabled_icon_url = "${omni.sample.in_app_guide}/data/next_disabled.svg"
url.previous_icon_url = "${omni.sample.in_app_guide}/data/previous.svg"
url.previous_disabled_icon_url = "${omni.sample.in_app_guide}/data/previous_disabled.svg"
fl.button_padding = 2

step_ui = {
    "Window": {"margin": 0, "padding": 0, "border_width": 0},
    "Rectangle::title_bar_background": {"background_color": cl.dark_color},
    "HStack::title_stack": {
        "margin": 10,
    },
    "Rectangle::content_background": {
        "background_color": cl.light_color,
    },
    "VStack::content_stack": {
        "margin": 10,
    },
    "Label::header": {
        "font_size": 20,
        "color": cl("#211b03"),
    },
    "Label::description": {
        "font_size": 14,
        "color": cl.black,
    },
    "Button::close": {"background_color": cl.transparent},
    "Button::close:hovered": {"background_color": cl.transparent},
    "Button::close:pressed": {"background_color": cl.transparent},
    "Button.Image::close": {
        "image_url": url.close_icon_url,
        "alignment": ui.Alignment.CENTER,
    },
    "Button::link": {"background_color": cl.transparent},
    "Button::link:hovered": {"background_color": cl.transparent},
    "Button::link:pressed": {"background_color": cl.transparent},
    "Button.Label::link": {"color": cl("#211b03"), "alignment": ui.Alignment.LEFT},
    "Button.Label::link:hovered": {"color": cl("#e5ddba")},
    "Button.Label::link:pressed": {"color": cl.white},
    "Rectangle::button_bar_background": {"background_color": cl("#a9974a")},
    "HStack::button_bar_stack": {"margin": 4},
    "Button::enabled_next": {
        "padding": fl.button_padding,
        "stack_direction": ui.Direction.FRONT_TO_BACK,
        "background_color": cl.transparent,
    },
    "Button.Image::enabled_next": {
        "image_url": url.next_icon_url,
        "alignment": ui.Alignment.CENTER,
    },
    "Button::enabled_next:hovered": {"background_color": cl.button_hovered_background},
    "Button::enabled_next:pressed": {"background_color": cl.button_pressed_background},
    "Button::disabled_next": {
        "stack_direction": ui.Direction.FRONT_TO_BACK,
        "padding": fl.button_padding,
        "background_color": cl.transparent,
    },
    "Button.Image::disabled_next": {
        "image_url": url.next_disabled_icon_url,
        "alignment": ui.Alignment.CENTER,
    },
    "Button::enabled_previous": {
        "padding": fl.button_padding,
        "stack_direction": ui.Direction.FRONT_TO_BACK,
        "background_color": cl.transparent,
    },
    "Button.Image::enabled_previous": {
        "image_url": url.previous_icon_url,
        "alignment": ui.Alignment.LEFT_CENTER,
    },
    "Button::enabled_previous:hovered": {"background_color": cl.button_hovered_background},
    "Button::enabled_previous:pressed": {"background_color": cl.button_pressed_background},
    "Button::disabled_previous": {
        "stack_direction": ui.Direction.FRONT_TO_BACK,
        "padding": fl.button_padding,
        "background_color": cl.transparent,
    },
    "Button.Image::disabled_previous": {
        "image_url": url.previous_disabled_icon_url,
        "alignment": ui.Alignment.CENTER,
    },
    "Button::steps_toggle": {
        "background_color": cl.light_color,
    },
    "Button::steps_toggle:hovered": {"background_color": cl.button_hovered_background},
    "Button::steps_toggle:pressed": {"background_color": cl.button_pressed_background},
    "Button.Label::steps_toggle": {
        "color": cl.black,
    },
    "Button.Label::steps_toggle:hovered": {"color": cl.light_color},
    "Button.Label::steps_toggle:pressed": {"color": cl.light_color},
    "TreeView": {
        "background_color": cl.transparent,
        "background_selected_color": cl.dark_color,
        "secondary_color": cl.dark_color,
    },
    "TreeView.Item": {"color": cl.black},
    "TreeView.Item:disabled": {"color": cl.grey},
    "TreeView.Item::object_name_grey": {"color": cl.grey},
    "TreeView.Item::object_name_missing": {"color": cl.grey},
    "TreeView.Item:selected": {"color": cl.black},
    "TreeView:selected": {"background_color": cl.dark_color},
    "TreeView.ScrollingFrame": {"background_color": cl.transparent},
}

overlay_ui = {
    "Window": {"margin": 0, "padding": 0, "border_width": 0},
    "Rectangle::mouse_blocker": {"background_color": cl.transparent, "border_width": 0},
    "Rectangle::highlight": {"background_color": cl.transparent, "border_color": cl.light_color, "border_width": 4},
}
