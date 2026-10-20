# Copyright (c) 2023, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.

from pathlib import Path

from omni import ui
from omni.ui import color as cl

__all__ = ["ICON_PATH", "Colors", "UI_STYLES", "PROPERTY_STYLES"]


CURRENT_PATH = Path(__file__).parent
ICON_PATH = CURRENT_PATH.parent.parent.parent / "data" / "icons"


class Colors:
    Window = cl.shade(0xFF353535)
    Selected = cl.shade(0xFFDDDDDD)
    Text = cl.shade(0xFF929292)
    Hint = cl.shade(0xFF6A6A6A)
    Error = cl.shade(0xCC2222FF)
    Image = cl.shade(0xFFA8A8A8)
    Background = cl.shade(0xFF23211F, light=0xFF535354)
    medium_gray = 0xFF454545
    dark_green = 0xFF458545
    dark_blue = 0xFF552525
    pale_blue = 0xFF884444
    transparent = 0x0
    light_gray = 0xFFDDDDDD
    white = 0xFFFFFFFF
    black = 0xFF000000
    Disabled = cl.shade(0xFF323535)
    Warn = cl.shade(0xFFFFC734, light=0xFFC5911A)
    Install = "pink"


class Property:
    margin = "margin"
    margin_width = "margin_width"
    margin_height = "margin_height"
    border_radius = "border_radius"
    corner_flag = "corner_flag"
    background_color = "background_color"
    padding = "padding"
    color = "color"
    font_size = "font_size"
    font_weight = "font_weight"


CONTEXT_MENU_STYLE = {
    "Menu": {"background_color": cl.context_menu_background_color, "color": cl.context_menu_text, "border_radius": 2},
    "Menu.Item": {"background_color": 0x0, "margin": 0},
    "Separator": {"background_color": 0x0, "color": cl.context_menu_separator},
}


UI_STYLES = {
    "NvidiaLight": {},
    "NvidiaDark": {
        "CollapsableFrame": {
            Property.margin_width: 10,
            Property.font_size: 15,
            "color": Colors.Text,
        },
        "Button": {
            "color": Colors.Text,
            "margin": 1,
            "padding": 10,
            "alignment": ui.Alignment.CENTER,
            "background_color": Colors.Background,
        },
        "Button:disabled": {"background_color": Colors.Disabled},
        "Label": {
            "color": Colors.white,
            "font_size": 15,
            "font_weight": "bold",
            "alignment": ui.Alignment.V_CENTER,
            "background_color": Colors.Error,
            "background": Colors.Image,
        },
        "LabelField": {
            "background_color": Colors.dark_blue,
            "color": Colors.Text,
            "font_size": 15,
            "font_weight": "normal",
        },
        "TreeViewItemError": {
            "color": Colors.Error,
        },
        "TreeViewItemCanUpgrade": {
            "color": Colors.Warn,
        },
        "LoadingLabel": {
            "color": Colors.Text,
            "font_size": 20,
            "alignment": ui.Alignment.V_CENTER,
        },
        "LoadingError": {
            "color": Colors.Error,
            "font_size": 20,
            "alignment": ui.Alignment.V_CENTER,
        },
        "TreeViewItemInstalling": {
            "color": Colors.Install,
            "font_size": 15,
            "margin_width": 5,
            "margin_height": 3,
        },
        "TreeViewItemVersion": {
            "alignment": ui.Alignment.CENTER,
            "margin_width": 5,
            "margin_height": 3,
            "font_size": 15,
        },
        "TreeViewItemInstallingVersion": {
            "alignment": ui.Alignment.CENTER,
            "color": Colors.Install,
            "font_size": 15,
        },
        "TreeView.Item": {
            "margin_width": 5,
            "margin_height": 3,
            "font_size": 15,
        },
        "TreeView.Item:hovered": {
            "color": Colors.white,
            "font_size": 15,
        },
    },
    # Search bar
    "SearchBar.Button": {
        "background_color": 0,
        "padding": 3,
        "margin": 0,
        "stack_direction": ui.Direction.LEFT_TO_RIGHT,
    },
    "SearchBar.Button:hovered": {"background_color": 0xFF3A3A3A},
    "SearchBar.Button:pressed": {"background_color": Colors.Background},
    "SearchBar.Button:selected": {"background_color": Colors.Background},
    "SearchBar.Button.Image::navigation": {"image_url": f"{ICON_PATH}/navtree.svg", "color": Colors.Image},
    "SearchBar.Button.Image::settings": {"image_url": f"{ICON_PATH}/settings.svg", "color": Colors.Image},
    "SearchBar.Button.Image::refresh": {"image_url": f"{ICON_PATH}/none.svg", "color": Colors.Image},
    "SearchBar.Button.Label": {"color": 0xFFACACAC},
}

PROPERTY_STYLES = {
    "Asset.Title": {"font_size": 18, "color": 0xFF9E9E9E, "font-weight": 900},
    "Asset.Label": {"font_size": 14, "font_weight": 1200, "text-align": "left"},
    "Asset.Value": {"font_size": 14, "font_weight": 1, "text-align": "right"},
    "Asset.ButtonLinks": {"background_color": "transparent", "padding": 0},
    "Asset.ButtonLinks:hovered": {"background_color": 0xFF9E9E9E, "border_color": cl("#0078D7")},
    "Asset.ButtonLinks:pressed": {
        "background_color": cl("#CCE4F7"),
        "border_color": cl("#005499"),
        "border_width": 1.0,
    },
}
