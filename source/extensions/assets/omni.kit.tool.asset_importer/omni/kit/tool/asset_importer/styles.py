# Copyright (c) 2022, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

import omni.kit.app

__all__ = ["PATH_EXTENSION", "TT_EXPORT_SF", "TT_EXPORT_BTN", "OPTIONS_STYLE"]

PATH_EXTENSION = "${omni.kit.tool.asset_importer}"

"""
TOOLTIPS
##########
    SF: string field
    BTN: button
"""
TT_EXPORT_SF = "Left this empty will export USD to the folder that assets are under."
TT_EXPORT_BTN = "Choose folder."

OPTIONS_STYLE = {
    "Button.Image::folder": {
        "image_url": "resources/glyphs/folder.svg",
        "color": 0xFF9E9E9E,
        "image_width": 20,
        "image_height": 20,
        "background_color": 0x0,
    },
    "Button.Image::folder:hovered": {"image_url": "resources/glyphs/folder_open.svg"},
    "Button::folder": {"background_color": 0x0, "margin": 0},
    "Field": {"background_color": 0xFF23211F},
    "RadioButton": {"background_color": 0x0},
    "RadioButton:checked": {"background_color": 0x0},
    "RadioButton:hovered": {"background_color": 0x0},
    "RadioButton:pressed": {"background_color": 0x0},
    "RadioButton.Image": {
        "image_url": f"{PATH_EXTENSION}/data/icons/radio_off.svg",
        "color": 0xFF9E9E9E,
    },
    "RadioButton.Image:checked": {
        "image_url": f"{PATH_EXTENSION}/data/icons/radio_on.svg",
    },
    "RadioButton.Image:hovered": {
        "image_url": f"{PATH_EXTENSION}/data/icons/radio_on.svg",
    },
}
