# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

"""
Centralized styling for omni.kit.markup.core extension.

This module defines all colors, constants, and styles following best practices:
- Uses omni.ui.color, omni.ui.constant, and omni.ui.url for all styling values
- Extension-specific prefixes (markup_*) prevent conflicts with other extensions
- Single centralized STYLES dictionary for all widget styling
- Proper Type::Name:State selector hierarchy
"""

from omni import ui
from omni.ui import color as cl
from omni.ui import constant as fl
from omni.ui import url

# ==============================================================================
# Color Constants - Extension-specific with 'markup_' prefix
# ==============================================================================
# Background colors
cl.markup_background_dark = cl("1F2123")
cl.markup_background_medium = cl("323434")
cl.markup_background_light = cl("545353")
cl.markup_background = ui.color.shade(cl.markup_background_dark, light=cl.markup_background_light)
cl.markup_background_button_hover = cl("AFAFAFAF")
cl.markup_background_collapsableframe_hovered = cl("2B2E2E")

cl.markup_button_image_disabled = cl("6E6E6E")
cl.markup_selection_checked = cl("EFBD17")
cl.markup_highlight_dark = cl("34C7FF")
cl.markup_highlight_light = cl("1A91C5")
cl.markup_selection_selected = ui.color.shade(cl.markup_highlight_dark, light=cl.markup_highlight_light)

cl.markup_stringfield = cl("EEEEEE")
cl.markup_text = cl("CCCCCC")

# ==============================================================================
# Float Constants - Extension-specific with 'markup_' prefix
# ==============================================================================
# Border radius
fl.markup_border_radius_small = 2.0
fl.markup_border_radius = 3.0

# Font sizes
FONT_SIZE = 14.0
fl.markup_font_size_small = 12.0
fl.markup_font_size_medium = FONT_SIZE

# ==============================================================================
# URL Constants - Extension-specific with 'markup_' prefix
# ==============================================================================
url.markup_icon_lock = "${omni.kit.markup.core}/icons/lock_dark.svg"
url.markup_icon_remove = "${omni.kit.markup.core}/icons/remove_dark.svg"
url.markup_icon_apply = "${omni.kit.markup.core}/icons/apply.svg"
url.markup_icon_add_viewport = "${omni.kit.markup.core}/icons/markup_add_viewport.svg"
url.markup_icon_cancel = "${omni.kit.markup.core}/icons/cancel.svg"
url.markup_icon_add = "${omni.kit.markup.core}/icons/markup_add.svg"
url.markup_icon_export = "${omni.kit.markup.core}/icons/markup_export.svg"
url.markup_icon_step_backward = "${omni.kit.markup.core}/icons/StepBackward.svg"
url.markup_icon_play = "${omni.kit.markup.core}/icons/Play.svg"
url.markup_icon_pause = "${omni.kit.markup.core}/icons/Pause.svg"
url.markup_icon_step_forward = "${omni.kit.markup.core}/icons/StepForward.svg"
url.markup_icon_close_mark = "${kit}/resources/icons/CloseMark.svg"


MARKUP_BROWSER_WIDGET_STYLES = {
    "GridView.Hover.Frame": {"background_color": cl.markup_background},
    "GridView.Image:selected": {
        "border_width": 0,
        "border_color": cl.transparent,
        "border_radius": fl.markup_border_radius,
    },
    # ==========================================================================
    # GridView.Edit.Button Styles
    # ==========================================================================
    "GridView.Edit.Button": {
        "background_color": cl.transparent,
        "padding": 0,
        "stack_direction": ui.Direction.TOP_TO_BOTTOM,
    },
    "GridView.Edit.Button:hovered": {"background_color": cl.markup_background_button_hover},
    "GridView.Edit.Button.Image::apply": {
        "image_url": url.markup_icon_apply,
        "alignment": ui.Alignment.H_CENTER,
    },
    "GridView.Edit.Button.Image::new": {
        "image_url": url.markup_icon_add_viewport,
        "alignment": ui.Alignment.H_CENTER,
    },
    "GridView.Edit.Button.Image::cancel": {
        "image_url": url.markup_icon_cancel,
        "alignment": ui.Alignment.H_CENTER,
    },
    "GridView.Edit.Button.Label": {"alignment": ui.Alignment.CENTER, "font_size": fl.markup_font_size_small},
    # ==========================================================================
    # GridView.Hover.Button Styles
    # ==========================================================================
    "GridView.Hover.Button": {
        "background_color": cl.transparent,
        "padding": 0,
        "stack_direction": ui.Direction.TOP_TO_BOTTOM,
    },
    "GridView.Hover.Button.Image::edit": {
        "image_url": url.markup_icon_lock,
        "alignment": ui.Alignment.CENTER,
    },
    "GridView.Hover.Button.Image::delete": {
        "image_url": url.markup_icon_remove,
        "alignment": ui.Alignment.CENTER,
    },
    # ==========================================================================
    # GridView.Item.Selection Styles
    # ==========================================================================
    "GridView.Item.Selection": {"background_color": cl.transparent},
    "GridView.Item.Selection:checked": {
        "border_width": 2,
        "border_color": cl.markup_selection_checked,
        "border_radius": fl.markup_border_radius,
    },
    "GridView.Item.Selection:selected": {
        "border_width": 2,
        "border_color": cl.markup_selection_selected,
        "border_radius": fl.markup_border_radius,
    },
}


LIST_WINDOW_STYLES = {
    "Window": {"background_color": cl.markup_background, "padding": 0, "margin": 0},
    # ==========================================================================
    # Button Styling
    # ==========================================================================
    "Button": {"padding": 4, "background_color": cl.markup_background},
    "Button:hovered": {"background_color": cl.transaprent},
    "Button:pressed": {"background_color": cl.transaprent},
    # ==========================================================================
    # Add.Button Styling
    # ==========================================================================
    "Add.Button": {
        "background_color": cl.markup_background_medium,
        "padding": 4,
        "stack_direction": ui.Direction.LEFT_TO_RIGHT,
        "margin": 0,
        "border_radius": fl.markup_border_radius_small,
        "corner_flag": ui.CornerFlag.ALL,
    },
    "Add.Button.Image": {
        "image_url": url.markup_icon_add,
        "padding": 0,
        "margin": 0,
        "background_color": 0,
        "alignment": ui.Alignment.CENTER,
    },
    "Add.Button.Label": {
        "padding": 0,
        "margin": 0,
        "background_color": 0,
        "alignment": ui.Alignment.CENTER,
    },
    "Add.Button:hovered": {"background_color": cl.markup_background_button_hover},
    # ==========================================================================
    # Export.Button Styling
    # ==========================================================================
    "Export.Button": {
        "background_color": cl.markup_background_medium,
        "padding": 2,
        "stack_direction": ui.Direction.BACK_TO_FRONT,
        "margin": 0,
        "border_radius": fl.markup_border_radius_small,
        "corner_flag": ui.CornerFlag.ALL,
    },
    "Export.Button.Image": {
        "image_url": url.markup_icon_export,
        "padding": 4,
        "margin": 0,
        "background_color": cl.transparent,
        "alignment": ui.Alignment.CENTER,
    },
    "Export.Button.Label": {
        "padding": 4,
        "margin": 0,
        "background_color": cl.transparent,
        "alignment": ui.Alignment.CENTER,
    },
    "Export.Button:hovered": {"background_color": cl.markup_background_button_hover},
    # ==========================================================================
    # PlayBar Button Styling
    # ==========================================================================
    "Button.Image:disabled": {
        "color": cl.markup_button_image_disabled,
    },
    "Button.Image::previous": {
        "image_url": url.markup_icon_step_backward,
    },
    "Button.Image::play": {
        "image_url": url.markup_icon_play,
    },
    "Button.Image::pause": {
        "image_url": url.markup_icon_pause,
        "color": cl.markup_highlight_dark,
    },
    "Button.Image::next": {
        "image_url": url.markup_icon_step_forward,
    },
    # ==========================================================================
    # CollapsableFrame Styling
    # ==========================================================================
    "CollapsableFrame": {
        "background_color": cl.markup_background_medium,
        "secondary_color": cl.markup_background_medium,
        "color": cl.markup_text,
        "border_radius": fl.markup_border_radius,
        "border_color": cl.markup_border_collapsable,
        "border_width": 1,
        "font_size": fl.markup_font_size_medium,
        "padding": 6,
    },
    "CollapsableFrame:hovered": {"secondary_color": cl.markup_background_collapsableframe_hovered},
    "CollapsableFrame:pressed": {"secondary_color": cl.markup_background_collapsableframe_hovered},
    "CollapsableFrame.Header": {
        "font_size": fl.markup_font_size_medium,
        "background_color": cl.markup_text,
        "color": cl.markup_text,
    },
    "Menu.Item.CloseMark": {
        "image_url": url.markup_icon_close_mark,
        "margin": 3,
        "color": cl.markup_text,
    },
    "Menu.Title:hovered": {
        "background_color": cl.viewport_menubar_selection,
        "border_width": 1,
        "border_color": cl.viewport_menubar_selection_border,
    },
    "Menu.Title:pressed": {"background_color": cl.viewport_menubar_selection},
    "Separator": {"color": cl.markup_background_light, "border_width": 2},
    "StringField": {
        "color": cl.markup_stringfield,
        "font_size": fl.markup_font_size_medium,
    },
    **MARKUP_BROWSER_WIDGET_STYLES,
}
