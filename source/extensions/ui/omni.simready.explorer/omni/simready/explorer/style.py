# Copyright (c) 2023, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.

from pathlib import Path

from omni.ui import color as cl

CURRENT_PATH = Path(__file__).parent
ICON_PATH = CURRENT_PATH.parent.parent.parent.joinpath("data/icons")
SIMREADY_DRAG_PREFIX = "SimReady::"

# Use same context menu style with content browser
cl.context_menu_background = cl.shade(cl("#343432"))
cl.context_menu_separator = cl.shade(0x449E9E9E)
cl.context_menu_text = cl.shade(cl("#9E9E9E"))
cl.simready_background = cl.shade(cl("#23211F"))

CONTEXT_MENU_STYLE = {
    "Menu": {"background_color": cl.context_menu_background_color, "color": cl.context_menu_text, "border_radius": 2},
    "Menu.Item": {"background_color": 0x0, "margin": 0},
    "Separator": {"background_color": 0x0, "color": cl.context_menu_separator},
}

UI_STYLES = {
    "ToolBar.Button": {"background_color": 0x0, "padding": 3, "margin": 0},
    "ToolBar.Button:selected": {"background_color": cl.simready_background},
    "Splitter": {"background_color": 0x0, "margin_width": 0},
    "Splitter:hovered": {"background_color": 0xFFB0703B},
    "Splitter:pressed": {"background_color": 0xFFB0703B},
    "Property.Path": {"background_color": cl.simready_background},
    "Property.Path::mixed": {"color": 0xFFCC9E61},
    "Property.Frame": {"padding": 0},
    "GridView.Item.Badge.Image": {
        "image_url": f"{ICON_PATH}/physx.png",
    },
    "GridView.Item.Badge.Background": {"background_color": 0xFFC2C2C2},
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
