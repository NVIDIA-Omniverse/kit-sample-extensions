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
from omni.ui import color as cl

ICON_PATH = Path(__file__).parent.parent.parent.parent.parent.joinpath("icons")


class Colors:
    Background = ui.color.shade(0xFF23211F, light=0xFF535354)
    Selected = ui.color.shade(0xFFFFC734, light=0xFFC5911A)
    Edit = ui.color.shade(0xFF17BDEF)


WAYPOINT_BROWSER_WIDGET_STYLES = {
    "GridView.Image:selected": {"border_width": 0, "border_color": 0, "border_radius": 3.0},
    "GridView.Item.Selection": {"background_color": 0},
    "GridView.Item.Selection:checked": {"border_width": 2, "border_color": Colors.Edit, "border_radius": 3.0},
    "GridView.Item.Selection:selected": {"border_width": 2, "border_color": Colors.Selected, "border_radius": 3.0},
    "GridView.Hover.Frame": {"background_color": Colors.Background},
    "GridView.Hover.Button": {"background_color": 0, "padding": 0, "stack_direction": ui.Direction.TOP_TO_BOTTOM},
    "GridView.Hover.Button.Image::edit": {"image_url": f"{ICON_PATH}/lock_dark.svg", "alignment": ui.Alignment.CENTER},
    "GridView.Hover.Button.Image::delete": {
        "image_url": f"{ICON_PATH}/remove_dark.svg",
        "alignment": ui.Alignment.CENTER,
    },
    "GridView.Edit.Frame": {"background_color": 0x7F7F7F7F},
    "GridView.Edit.Button": {"background_color": 0, "padding": 0, "stack_direction": ui.Direction.TOP_TO_BOTTOM},
    "GridView.Edit.Button:hovered": {"background_color": 0xAFAFAFAF},
    "GridView.Edit.Button.Image::apply": {"image_url": f"{ICON_PATH}/apply.svg", "alignment": ui.Alignment.H_CENTER},
    "GridView.Edit.Button.Image::new": {
        "image_url": f"{ICON_PATH}/waypoint_add_viewport.svg",
        "alignment": ui.Alignment.H_CENTER,
    },
    "GridView.Edit.Button.Image::cancel": {"image_url": f"{ICON_PATH}/cancel.svg", "alignment": ui.Alignment.H_CENTER},
    "GridView.Edit.Button.Label": {"alignment": ui.Alignment.CENTER, "font_size": 12},
}


PEREFERENCE_WINDOW_STYLE = {
    "Window": {"background_color": cl("#25282AFF"), "padding": 0, "margin": 0},
    "Menu.Title": {"color": cl("#25282A"), "background_color": cl("#191A1B")},
    "Menu.Title:hovered": {
        "background_color": cl("#34C7FF3B"),
        "border_width": 1,
        "border_color": cl("#34C7FF"),
    },
    "Menu.Title:pressed": {"background_color": cl("#34C7FF3B")},
    "Menu.Item.CloseMark": {
        "image_url": "${kit}/resources/icons/CloseMark.svg",
        "margin": 3,
        "color": 0xFFCCCCCC,
    },
    "Label::key": {"color": 0xFF9E9E9E},
    "Line": {"color": 0xFF9E9E9E},
    "Rectangle::reset_invalid": {"background_color": 0xFF505050, "border_radius": 2},
    "Rectangle::reset": {"background_color": 0xFFA07D4F, "border_radius": 2},
    "CheckBox": {"border_radius": 1},
    "CheckBox:disabled": {"background_color": cl.viewport_menubar_medium},
}

LIST_WINDOW_STYLES = {
    "Window": {"background_color": Colors.Background, "padding": 0, "margin": 0},
    "Button": {"background_color": Colors.Background},
    "Separator": {"color": 0xFF535354, "border_width": 2},
    "Warning": {"background_color": Colors.Background, "color": 0xFF7C7C7C, "font_size": 20},
    "GridView.Image:selected": {"border_width": 0, "border_color": 0, "border_radius": 3.0},
    "Button.Close": {
        "stack_direction": ui.Direction.BACK_TO_FRONT,
        "background_color": cl.transparent,
        "border_width": 1,
        "border_radius": 2,
        "border_color": cl.transparent,
    },
    "Button.Close:hovered": {"border_color": 0xFF535354},
    "Button.Close.Image": {"image_url": f"{ICON_PATH}/close.svg"},
}

POSITIONER_STYLE = {"Rectangle": {"background_color": 0, "border_width": 0}}

EDIT_WINDOW_STYLES = {
    "Window": {"background_color": Colors.Background, "padding": 0, "margin": 0},
    **WAYPOINT_BROWSER_WIDGET_STYLES,
}

UI_STYLES = {
    "Add.Button": {
        "background_color": 0xFF343432,
        "padding": 4,
        "stack_direction": ui.Direction.LEFT_TO_RIGHT,
        "margin": 0,
        "border_radius": 2,
        "corner_flag": ui.CornerFlag.ALL,
    },
    "Add.Button.Image": {
        "image_url": f"{ICON_PATH}/waypoint_add.svg",
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
    "Add.Button:hovered": {"background_color": 0xAFAFAFAF},
    "Settings.Button": {
        "background_color": 0xFF343432,
        "padding": 2,
        "stack_direction": ui.Direction.BACK_TO_FRONT,
        "margin": 0,
        "border_radius": 2,
        "corner_flag": ui.CornerFlag.ALL,
    },
    "Settings.Button.Image": {
        "image_url": f"{ICON_PATH}/waypoint_settings.svg",
        "padding": 0,
        "margin": 0,
        "background_color": 0,
        "alignment": ui.Alignment.CENTER,
    },
    "Settings.Button.Label": {
        "padding": 0,
        "margin": 0,
        "background_color": 0,
        "alignment": ui.Alignment.CENTER,
    },
    "Settings.Button:hovered": {"background_color": 0xAFAFAFAF},
}
