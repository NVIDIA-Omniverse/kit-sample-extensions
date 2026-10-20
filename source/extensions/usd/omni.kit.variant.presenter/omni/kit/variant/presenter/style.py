# Copyright (c) 2022, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

from pathlib import Path

import omni.kit.app
import omni.ui as ui

PATH_EXTENSION = omni.kit.app.get_app().get_extension_manager().get_extension_path_by_module(__name__)
CURRENT_PATH = Path(__file__).parent

LABEL_COLOR = 0xFF8F8E86
WINDOW_BACKGROUND_COLOR = 0xFF444444
HEADER_BACKGROUND_COLOR = 0xFF23211F
HEADER_HOVERED_BACKGROUND_COLOR = 0xFF2E2E2B
LOCKED_OVERLAY_COLOR = 0x8023211F
ITEM_BACKGROUND_COLOR = 0xFF343432
ITEM_HOVERED_COLOR = 0xFF9E9E9E
ITEM_HOVERED_TEXT_COLOR = 0xFF8A8777
RED = 0xFF5555AA
GREEN = 0xFF77A278

UI_STYLE = {
    "Label": {"font_size": 14, "color": LABEL_COLOR, "margin_width": 6},
    "Label::search": {"color": 0xFF808080, "margin_width": 4},
    "SearchField": {
        "background_color": HEADER_BACKGROUND_COLOR,
        "color": 0xFFA2A2A2,
        "border_radius": 0,
        "font_size": 16,
        "margin": 0,
        "padding": 5,
    },
    "TreeView.ScrollingFrame": {"background_color": 0x0},
    "TreeView": {
        "background_color": HEADER_BACKGROUND_COLOR,
        "color": LABEL_COLOR,
        "font_size": 14,
    },
    "TreeView.Header": {
        "background_color": HEADER_BACKGROUND_COLOR,
        "color": LABEL_COLOR,
        "font_size": 14,
    },
    "TreeView:drop": {"background_color": 0x0},
    "TreeView:hovered": {"background_color": 0x0},
    "TreeView:selected": {"background_color": 0x0},
    "TreeView.Header:drop": {"background_color": HEADER_HOVERED_BACKGROUND_COLOR},
    "TreeView.Header:hovered": {"background_color": HEADER_HOVERED_BACKGROUND_COLOR},
    "TreeView.Header:selected": {"background_color": HEADER_HOVERED_BACKGROUND_COLOR},
    "TreeView.Button": {"background_color": HEADER_BACKGROUND_COLOR},
    "TreeView.Button:hovered": {"background_color": HEADER_HOVERED_BACKGROUND_COLOR},
    "TreeView.Item": {"background_color": ITEM_BACKGROUND_COLOR, "border_radius": 4, "color": LABEL_COLOR},
    "TreeView.Item:selected": {"background_color": ITEM_HOVERED_COLOR, "color": HEADER_BACKGROUND_COLOR},
    "TreeView.Item:hovered": {"background_color": ITEM_HOVERED_COLOR, "color": HEADER_BACKGROUND_COLOR},
    "TreeView.Item:drop": {"background_color": ITEM_HOVERED_COLOR},
    "Button": {"background_color": ITEM_BACKGROUND_COLOR, "margin": 0, "padding": 3, "border_radius": 4},
    "Button:hovered": {"background_color": ITEM_HOVERED_COLOR},
    "Button:pressed": {"background_color": ITEM_HOVERED_COLOR},
    "Button.Image::RemoveVariant": {"image_url": f"{PATH_EXTENSION}/data/icons/remove.svg"},
    "Button.Image::RemoveGroup": {"image_url": f"{PATH_EXTENSION}/data/icons/close.svg", "color": 0xFF5555AA},
    "Button::EditVariant": {"background_color": HEADER_BACKGROUND_COLOR},
    "Button::EditVariant:hovered": {"background_color": HEADER_HOVERED_BACKGROUND_COLOR},
    "Button::EditVariant:pressed": {"background_color": HEADER_HOVERED_BACKGROUND_COLOR},
    "Button.Image::EditVariant": {"image_url": f"{PATH_EXTENSION}/data/icons/edit_dark.svg"},
    "Button::EditVariantOptions": {"background_color": HEADER_BACKGROUND_COLOR},
    "Button::EditVariantOptions:hovered": {"background_color": HEADER_HOVERED_BACKGROUND_COLOR},
    "Button::EditVariantOptions:pressed": {"background_color": HEADER_HOVERED_BACKGROUND_COLOR},
    "Button.Image::EditVariantOptions": {"image_url": f"{PATH_EXTENSION}/data/icons/edit_dark_with_options.svg"},
    "Button.Image::LockedVariant": {"image_url": f"{PATH_EXTENSION}/data/icons/lock.svg", "color": RED},
    "Button.Image::UnlockedVariant": {"image_url": f"{PATH_EXTENSION}/data/icons/unlock.svg", "color": LABEL_COLOR},
}

TABS = {
    "RadioButton": {
        "margin": 2,
        "border_radius": 2,
        "font_size": 16,
        "color": 0xFF444444,
        "background_color": HEADER_BACKGROUND_COLOR,
    },
    "RadioButton:checked": {"background_color": 0xFF777777, "color": 0xFF222222},
}
RECT = {"border_radius": 4, "background_color": HEADER_BACKGROUND_COLOR}
ADD = {
    "image_url": f"{PATH_EXTENSION}/data/icons/add.svg",
    "color": GREEN,
    "alignment": ui.Alignment.CENTER,
    "margin_width": 1.5,
}
REMOVE = {
    "image_url": f"{PATH_EXTENSION}/data/icons/close.svg",
    "color": RED,
    "alignment": ui.Alignment.CENTER,
    "margin_width": 4.0,
}
REFRESH = {"image_url": f"{PATH_EXTENSION}/data/icons/refresh.svg", "alignment": ui.Alignment.CENTER}
RADIO = {
    "background_color": 0x0,
    "image_url": f"{PATH_EXTENSION}/data/icons/radio_off.svg",
    ":checked": {"image_url": f"{PATH_EXTENSION}/data/icons/radio_on.svg"},
}
HANDLE = {"image_url": f"{PATH_EXTENSION}/data/icons/handle.svg", "margin_height": 3, "margin_width": 2}
BUTTON = {
    "Button": {"background_color": 0x1A444444, "margin": 0, "padding": 3, "border_radius": 4},
    "Button:hovered": {"background_color": 0x269E9E9E},
    "Button:pressed": {"background_color": 0x26444444},
    "Button.Label:disabled": {"color": 0xFF606060},
}
