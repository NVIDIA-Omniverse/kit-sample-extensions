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

CURRENT_PATH = Path(__file__).parent
ICON_PATH = CURRENT_PATH.parent.parent.parent.parent.joinpath("icons")


class ConstSize:
    IconSize = 14
    Radius = 2


class Colors:
    Background = ui.color.shade(0xFF23211F, light=0xFF535354)
    Scrollbar = ui.color.shade(0xFF808080, light=0xFF9E9E9E)
    Selected = ui.color.shade(0xFFFFC734, light=0xFFC5911A)
    Text = ui.color.shade(0xFFA1A1A1, light=0xFFE0E0E0)
    DarkText = ui.color.shade(0xFF504F50, light=0xFFA1A1A1)
    ImageDisable = ui.color.shade(0xFF696969)
    Image = ui.color.shade(0xFF9E9E9E)
    Hover = ui.color.shade(0xFFF4F9FE)
    ResetInvalid = ui.color.shade(0xFF505050)
    Reset = ui.color.shade(0xFFA07D4F)
    Line = ui.color.shade(0x338A8777)


PREFERENCE_PAGE_STYLES = {
    "Reset_invalid.Rect": {"background_color": Colors.ResetInvalid, "border_radius": ConstSize.Radius},
    "Reset.Rect": {"background_color": Colors.Reset, "border_radius": ConstSize.Radius},
    "Setting.Button.Image": {"background_color": 0x0, "image_url": f"{ICON_PATH}/open_dark.svg"},
    "Setting.Button.Image:disabled": {"color": Colors.ImageDisable},
    "Setting.Button": {"background_color": 0x0},
    "Setting.Field": {"color": Colors.Text, "background_color": Colors.Background},
    "Setting.Field:disabled": {"color": Colors.DarkText},
    "ComboBox": {"color": Colors.Text, "background_color": Colors.Background},
    "ComboBox:disabled": {"color": Colors.DarkText},
    "Setting.Label": {"color": Colors.Text},
    "Setting.Label:disabled": {"color": Colors.DarkText},
    "Seperator": {"color": Colors.Line},
    "TypeOption": {"background_color": 0x0, "padding": 0},
    "TypeOption.Image": {
        "image_url": f"{ICON_PATH}/radio_off.svg",
        "image_width": ConstSize.IconSize,
        "image_height": ConstSize.IconSize,
    },
    "TypeOption.Image:checked": {"image_url": f"{ICON_PATH}/radio_on.svg"},
}

PLAY_STYLES = {
    "PlayButton": {"background_color": 0, "padding": 4},
    "PlayButton.Image": {"image_url": f"{ICON_PATH}/play_dark.svg"},
    "PlayButton.Image:checked": {"image_url": f"{ICON_PATH}/pause_dark.svg"},
    "PlayButton.Image:disabled": {"color": Colors.DarkText},
    "PlayRateButton": {"background_color": 0, "padding": 4},
    "PlayRateButton.Image::rate_1x": {"image_url": f"{ICON_PATH}/rate_1x_dark.svg"},
    "PlayRateButton.Image::rate_2x": {"image_url": f"{ICON_PATH}/rate_2x_dark.svg"},
    "PlayRateButton.Image::rate_4x": {"image_url": f"{ICON_PATH}/rate_4x_dark.svg"},
    "PlayRateButton.Image::rate_8x": {"image_url": f"{ICON_PATH}/rate_8x_dark.svg"},
    "PlayLoopButton": {"background_color": 0, "padding": 4},
    "PlayLoopButton:selected": {"background_color": 0xFF292929},
    "PlayLoopButton.Image": {"image_url": f"{ICON_PATH}/loop_dark.svg"},
}

CLOCK_STYLES = {
    "Spinner": {"background_color": Colors.Text, "border_width": 0},
    "Spinner:hovered": {"background_color": Colors.Hover},
    "Spinner:pressed": {"background_color": Colors.Text},
    "Number": {"font_size": 40},
    "AMPM": {"font_size": 20},
    "Circle": {"background_color": Colors.Text},
}

cl.hotkey_hint = cl.shade(cl("#5A5A5A"))
cl.hotkey_warning = cl.shade(cl("#DFCB4A"))
cl.hotkey_text_active = cl.shade(cl("#CCCCCC"))
cl.hotkey_window_background = cl.shade(cl("#444444"))
cl.actions_text = cl.shade(cl("#848484"))
cl.actions_background = cl.shade(cl("#1F2123"))


WARNING_WINDOW_STYLE = {
    "Window": {"secondary_background_color": 0x0},
    "Titlebar.Background": {"background_color": cl.actions_background},
    "Titlebar.Title": {"color": cl.actions_text},
    "Titlebar.Image": {"image_url": f"{ICON_PATH}/warning.svg"},
    "Warning.Text": {"color": cl.actions_text},
    "Warning.Text::highlight": {"color": cl.hotkey_text_active},
    "Warning.Button": {"background_color": cl.actions_background},
    "Warning.Button.Label": {"color": cl.hotkey_text_active},
    "CheckBox": {"background_color": cl.actions_text, "font_size": 12},
    "CheckBox.Text": {"color": cl.actions_text, "font_size": 12},
    "Warning.Button:hovered": {"background_color": Colors.DarkText},
    "Warning.Button:pressed": {"background_color": 0xFF79776C},
}
