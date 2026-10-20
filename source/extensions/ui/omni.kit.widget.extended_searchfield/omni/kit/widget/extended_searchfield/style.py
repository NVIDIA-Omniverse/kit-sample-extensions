# SPDX-FileCopyrightText: Copyright (c) 2021-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
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

CURRENT_PATH = Path(__file__).parent.absolute()
ICON_PATH = CURRENT_PATH.parent.parent.parent.parent.joinpath("icons")
DATA_PATH = CURRENT_PATH.parent.parent.parent.parent.joinpath("data")


class Colors:
    Background = ui.color.shade(0xFF454545, light=0xFF535354)
    Border = ui.color.shade(0xFFC9974C)
    Hint = ui.color.shade(0xFF4A4A4A, light=0xFFD6D6D6)
    Hover = ui.color.shade(0xFF3A3A3A, light=0xFFB8B8B8)
    Close = ui.color.shade(0xFF858585)
    WordText = ui.color.shade(0xFF8D760D)
    WordBackground = ui.color.shade(0xFFD9D4BC)
    UnsupportedWordBackground = ui.color.shade(0xFF9999D9)
    DateText = ui.color.shade(0xFFD9D4BC)
    DropArea = ui.color.shade(0xDD454545)
    DropAreaBorder = ui.color.shade(0x55ADAC9F)
    SearchfieldFrame = ui.color.shade(0xFF23211F, light=0xFF535354)
    Transparent = ui.color.shade(0x00000000)
    Button = ui.color.shade(0xFF9A9A9A)
    ButtonHover = ui.color.shade(0xFFD8D8D8)
    ButtonPress = ui.color.shade(0xFFC5911A)
    SearchButton = ui.color.shade(0xFFC9974C)
    SearchButtonHover = ui.color.shade(0xFFE9B76C)
    SearchButtonPress = ui.color.shade(0xFFA9772C)


UI_STYLE = {
    "ImagePathField": {"background_color": Colors.SearchfieldFrame, "border_radius": 4, "border_width": 0},
    "Background": {
        "background_color": Colors.Background,
        "border_radius": 0,
        "border_width": 0,
        "border_color": Colors.Background,
    },
    "ErrorMessages": {
        "background_color": ui.color.shade(0xFF2A2A54),
        "border_radius": 0,
        "border_width": 0,
        "border_color": Colors.Background,
        "margin": 5,
    },
    "ErrorMessages.Label": {"color": ui.color.shade(0xFF6A6AD4), "margin": 10},
    "DropArea": {
        "background_color": Colors.Transparent,
        "border_radius": 0,
        "border_width": 0,
        "border_color": Colors.DropAreaBorder,
        # "image_url": f"{DATA_PATH}/DragImageHereSmall.PNG"
    },
    "DropArea.Label": {},
    "ExtendedSearchField": {
        "background_color": 0,
        "border_radius": 0,
        "border_width": 0,
        "background_selected_color": 0xFF535354,
    },
    "ExtendedSearchField.Frame": {
        "background_color": Colors.SearchfieldFrame,
        "border_radius": 0.0,
        "border_color": 0,
        "border_width": 2,
    },
    "ExtendedSearchField.Frame:selected": {
        "background_color": Colors.SearchfieldFrame,
        "border_radius": 0,
        "border_color": Colors.Border,
        "border_width": 2,
    },
    "SearchProgress.Button": {"background_color": Colors.Transparent, "margin_width": 2, "padding": 4},
    "ExtendedSearchField.Hint": {"color": Colors.Hint},
    "ExtendedSearchField.Word": {"background_color": Colors.WordBackground},
    "ExtendedSearchField.Word.Label": {"color": Colors.WordText},
    "ExtendedSearchField.Word.Button": {"background_color": 0, "padding": 2},
    "ExtendedSearchField.Word.Button.Image": {"image_url": f"{ICON_PATH}/close.svg", "color": Colors.WordText},
    "ExtendedSearchField.Word.Unsupported": {"background_color": Colors.UnsupportedWordBackground},
    "ExtendedSearchField.Word.Unsupported.Label": {"color": Colors.WordText},
    "ExtendedSearchField.Word.Unsupported.Button": {"background_color": 0, "padding": 2},
    "ExtendedSearchField.Word.Unsupported.Button.Image": {
        "image_url": f"{ICON_PATH}/close.svg",
        "color": Colors.WordText,
    },
    "ExtendedSearchField.Image": {
        "background_color": Colors.Transparent,
        "border_radius": 9,
        "border_color": 0xFF858585,
        "border_width": 1,
    },
    "ExtendedSearchField.Image.Label": {"color": 0xFF858585},
    "ExtendedSearchField.Image.Button": {"background_color": Colors.Transparent, "padding": 2},
    "ExtendedSearchField.Image.Button.Image": {"image_url": f"{ICON_PATH}/close.svg", "color": 0xFF858585},
    "ExtendedSearchField.LargeImage": {
        "background_color": 0xFF3A3A3A,
        "border_radius": 10,
        "border_color": 0xFF858585,
        "border_width": 1,
    },
    "ExtendedSearchField.LargeImage.Label": {"color": 0xFF858585},
    "ExtendedSearchField.LargeImage.Button": {"background_color": Colors.Transparent, "padding": 2},
    "ExtendedSearchField.LargeImage.Button.Image": {"image_url": f"{ICON_PATH}/close.svg", "color": 0xFF858585},
    "ExtendedSearchField.CalendarHint": {"color": Colors.DateText},
    "ExtendedSearchField.CalendarStringField": {"background_color": Colors.Transparent, "color": Colors.DateText},
    "Calendar.Button": {"background_color": Colors.Transparent},
    "ToolBar.Button": {"background_color": Colors.SearchfieldFrame},
    "ToolBar.Button:hovered": {"background_color": Colors.Hover},
    "ToolBar.Button:pressed": {"background_color": Colors.Background},
    "SearchField.Button": {"background_color": Colors.Transparent, "margin_width": 2, "padding": 4},
    "SearchField.Button.Image": {"image_url": f"{ICON_PATH}/search_dark.svg", "color": Colors.Button},
    "SearchField.Button.Image:hovered": {"color": Colors.ButtonHover},
    "SearchField.Button.Image:pressed": {"color": Colors.ButtonPress},
    "SearchField.ClearButton": {"padding": 0, "margin": 0, "background_color": Colors.Transparent},
    "SearchField.ClearButton.Image": {"image_url": f"{ICON_PATH}/close.svg", "color": Colors.Button},
    "SearchField.ClearButton:hovered": {"color": Colors.ButtonHover},
    "SearchField.ClearButton:pressed": {"color": Colors.ButtonPress},
    "ImageMenu.Button": {"padding": 0, "margin": 0, "background_color": Colors.Transparent},
    "ImageMenu.Button.Image": {"image_url": f"{ICON_PATH}/picture_dark.svg", "color": Colors.Button},
    "ImageMenu.Button.Image:hovered": {"color": Colors.ButtonHover},
    "ImageMenu.Button.Image:pressed": {"color": Colors.ButtonPress},
    "SearchMenu.Button": {"padding": 0, "margin": 0, "background_color": Colors.Transparent},
    "SearchMenu.Button.Image": {"image_url": f"{ICON_PATH}/more_options.svg", "color": Colors.Button},
    "SearchMenu.Button.Image:hovered": {"color": Colors.ButtonHover},
    "SearchMenu.Button.Image:pressed": {"color": Colors.ButtonPress},
    "Separate.Button": {"background_color": Colors.Background},
    "Separate.Button:hovered": {"background_color": Colors.SearchfieldFrame},
    "Separate.Button:pressed": {"background_color": Colors.SearchfieldFrame},
    "MeButton.Button": {"padding": 0, "margin": 0, "background_color": Colors.SearchfieldFrame},
    "MeButton.Button:hovered": {"padding": 0, "margin": 0, "background_color": Colors.Button},
    "MeButton.Button:pressed": {"padding": 0, "margin": 0, "background_color": Colors.ButtonHover},
    "ImageMenu.Image": {"margin": 2},
    "ImageMenu.ImageButton": {
        "padding": 10,
        "margin": 2,
        "background_color": Colors.DropArea,
        "border_radius": 1,
        "border_width": 1,
        "border_color": Colors.DropAreaBorder,
    },
    "ImageMenu.ImageButton:pressed": {
        "padding": 10,
        "margin": 2,
        "background_color": Colors.ButtonHover,
        "border_radius": 1,
        "border_width": 1,
        "border_color": Colors.DropAreaBorder,
    },
    "SearchButton.Background": {
        "background_color": Colors.SearchButton,
        "border_radius": 3,
        "color": 0xFF123456,
        "border_width": 10,
    },
    "SearchButton.Background:hovered": {"background_color": Colors.SearchButtonHover, "border_radius": 3},
    "SearchButton.Background:pressed": {"background_color": Colors.SearchButtonPress, "border_radius": 3},
    "SearchButton.Image": {
        "alignment": ui.Alignment.RIGHT_CENTER,
        "image_url": f"{ICON_PATH}/arrow.svg",
        "color": 0xFFFFFFFF,
    },
    "SearchButton.Label": {
        "alignment": ui.Alignment.CENTER,
        "color": 0xFFFFFFFF,
        "background_color": 0x00000000,
        "padding": 0,
        "margin": 0,
        "border_width": 1,
        "border_color": 0xFFFFFFFF,
    },
}
