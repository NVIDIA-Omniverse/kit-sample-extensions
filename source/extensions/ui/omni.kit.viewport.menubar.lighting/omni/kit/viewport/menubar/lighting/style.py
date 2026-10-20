# Copyright (c) 2021-2022, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#
from pathlib import Path

import carb.tokens
from omni.ui import color as cl
from omni.ui import constant as fl

ICON_PATH = (
    Path(carb.tokens.get_tokens_interface().resolve("${omni.kit.viewport.menubar.lighting}"))
    .joinpath("data")
    .joinpath("icons")
    .absolute()
)
ICON_CORE_PATH = (
    Path(carb.tokens.get_tokens_interface().resolve("${omni.kit.viewport.menubar.core}"))
    .joinpath("data")
    .joinpath("icons")
    .absolute()
)

UI_STYLE = {
    "Menu.Item.Icon::Lighting": {"image_url": f"{ICON_PATH}/menu_icon.svg"},
    "Menu.Item.Icon::ToggleIcon": {"image_url": f"{ICON_PATH}/button_icon.svg"},
    "Menu.Item.Button": {
        "background_color": 0x00000000,
    },
    "Menu.Item.Button.Image::ToggleButtonOn": {"image_url": f"{ICON_PATH}/toggle_button_on.svg"},
    "Menu.Item.Button.Image::ToggleButtonOff": {"image_url": f"{ICON_PATH}/toggle_button_off.svg"},
    "Menu.Item.Icon::Add": {"image_url": f"{ICON_PATH}/add.svg", "color": cl.viewport_menubar_selection_border},
    "MenuBar.Item.Separator": {
        "background_color": cl.viewport_menubar_light,
        "margin_height": 6,
    },
}
