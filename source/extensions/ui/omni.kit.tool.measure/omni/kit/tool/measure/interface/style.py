# Copyright (c) 2022, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

from pathlib import Path
from typing import Dict


# Support Functions
def __get_icon(name: str, extension: str = "svg") -> str:
    """
    Collects the icon string path from the correct folder by its name

    Args:
        name: Name of the image (*.svg)
    Returns:
        Full path of the image
    """
    current_path = Path(__file__).parent
    icon_path = current_path.parent.parent.parent.parent.parent.joinpath("data")

    icons = {icon.stem: icon for icon in icon_path.glob(f"*.{extension}")}
    found = icons.get(name, "")
    return str(found)


# TODO: This is temporary
def get_icon_path(name: str, as_png: bool = False) -> str:
    return __get_icon(name, extension="png" if as_png else "svg")


def generate_toolbar_button_style(name: str) -> Dict:
    return {
        "Button": {"margin": 0, "background_color": 0x0, "border_radius": 4},
        "Button.Image": {"image_url": __get_icon(f"tool_{name}"), "color": _CLR_LABEL},
        "Button:hovered": {"background_color": 0xFF383838},
        "Button.Image:disabled": {"color": _CLR_DISABLED},
        "Button.Image:checked": {"color": _CLR_ACTIVE},
        "Button:checked": {"background_color": 0xFF1F2123},
    }


# Tooltip Descriptions
# -- Placement
TOOLTIP_SNAP_TO = "Custom snaps or Perpendicular mode. Perpendicular mode locks a point along the normal of first selection. Point to Point only."
TOOLTIP_CONSTRAINT = "Constrains points to Axis. Area Tool only."
TOOLTIP_PIVOT = "Snap to object pivot."
TOOLTIP_CENTER = "Snap to object bound center."
TOOLTIP_VERTEX = "Snap to object vertices."
TOOLTIP_MIDPOINT = "Snap to object edge midpoint."
TOOLTIP_EDGE = "Snap to object edge."
TOOLTIP_NONE = "Do not snap"
# -- Display
TOOLTIP_AXIS = "Visualize Axis Dimensions. Point to Point Tool only."
TOOLTIP_UNIT = "Measurement display units."
TOOLTIP_PRECISION = "Number of decimal points to display."
TOOLTIP_LABEL_SIZE = "Font Size for the Label."
TOOLTIP_COLOR = "Line and point display color."
TOOLTIP_RESET = "Value different from default"
# -- MANAGER
TOOLTIP_FILTER = "Filter Measurements by type"
TOOLTIP_OPTIONS = "Management Options"
TOOLTIP_VISIBILITY = "Toggle Visibility"
TOOLTIP_NAME = "Double click to rename measurement"
TOOLTIP_LOCK = "Lock the measurement"
TOOLTIP_DELETE = "Delete the measurement"
# -- EXPORT PANEL
TOOLTIP_DIRECTORY = "Browse and select directory"

# UI Styles

# UI COLOR CONSTANTS
_CLR_ACTIVE = 0xFFFFC734
_CLR_LABEL = 0xFF9E9E9E
_CLR_DISABLED = 0xFF333333
_CLR_DISABLED_ALT = 0xFF2E2E2B
_CLR_VP_BACKGROUND = 0xA0000000

# Manager Panel
STYLE_BUTTON_FILTER = {
    "Button": {"margin": 0, "background_color": 0x0},
    "Button.Image": {"image_url": __get_icon("filter"), "color": _CLR_LABEL},
    "Button:hovered": {"background_color": 0xFF383838},
}

STYLE_BUTTON_OPTIONS = {
    "Button": {"margin": 0, "background_color": 0x0},
    "Button.Image": {"image_url": __get_icon("options"), "color": _CLR_LABEL},
    "Button:hovered": {"background_color": 0xFF383838},
}

STYLE_BUTTON_VISIBILITY = {
    "Rectangle": {"margin": 0, "background_color": 0x0},
    "Rectangle:hovered": {"background_color": 0xFF383838},
    "ImageWithProvider": {"color": _CLR_LABEL},
    "ImageWithProvider:checked": {"color": _CLR_DISABLED},
}

STYLE_BUTTON_GO_TO = {
    "Rectangle": {"margin": 0, "background_color": 0x0},
    "ImageWithProvider": {"color": _CLR_LABEL},
}

STYLE_BUTTON_LOCK = {
    "Rectangle": {"margin": 0, "background_color": 0x0},
    "Button.Image": {"image_url": __get_icon("locked"), "color": _CLR_LABEL},
    "Button.Image:checked": {"image_url": __get_icon("unlocked"), "color": _CLR_DISABLED},
    "Button:hovered": {"background_color": 0xFF383838},
}

STYLE_BUTTON_DELETE = {
    "Rectangle": {"margin": 0, "background_color": 0x0},
    "ImageWithProvider": {"color": _CLR_LABEL},
}

# Export Panel
STYLE_BUTTON_DIRECTORY = {
    "Button": {"margin": 0, "background_color": 0x0},
    "Button.Image": {"image_url": __get_icon("folder"), "color": _CLR_LABEL},
    "Button:hovered": {"background_color": 0xFF383838},
}

# Styles

STYLE_VP_BUTTON = {
    "Button": {"margin": 0, "padding": 4, "background_color": _CLR_VP_BACKGROUND},
    "Button:hovered": {"background_color": _CLR_VP_BACKGROUND, "border_width": 1, "border_color": 0x30808080},
    "Button.Label": {"color": _CLR_ACTIVE},
}

STYLE_BUTTON_RESET = {
    "VStack::container": {"margin": 0},
    "Rectangle::reset_invalid": {"background_color": 0xFF4F4F4F},
    "Rectangle::reset_valid": {"color": 0xFFFFFFFF, "background_color": 0xFFA07D4F, "border_radius": 2},
    "Rectangle::reset_valid:disabled": {"background_color": _CLR_DISABLED_ALT},
}

STYLE_COLLAPSABLE_FRAME = {
    "CollapsableFrame": {
        "background_color": 0xFF343432,
        "secondary_color": 0xFF343432,
        "color": 0xFFCCCCCC,
        "border_radius": 4.0,
        "border_color": 0x0,
        "border_width": 0,
        "font_size": 14,
        "padding": 5,
        "margin": 0,
    },
    "HStack::header": {"margin": 5},
    "CollapsableFrame:hovered": {"secondary_color": 0xFF2E2E2B},
    "CollapsableFrame:pressed": {"secondary_color": 0xFF2E2E2B},
    "ComboBox": {
        "color": _CLR_LABEL,
        "background_color": 0xFF23211F,
        "secondary_color": 0xFF23211F,
        "border_radius": 2,
    },
    "ComboBox:disabled": {"color": _CLR_DISABLED},
}

STYLE_COMBO_BOX = {
    "ComboBox": {
        "color": _CLR_LABEL,
        "background_color": 0xFF23211F,
        "secondary_color": 0xFF23211F,
        "border_radius": 2,
    },
    "ComboBox:disabled": {"color": _CLR_DISABLED},
}

STYLE_COMBO_BOX_ALT = {
    "ComboBox": {
        "color": _CLR_LABEL,
        "background_color": 0xFF343432,
        "secondary_color": 0xFF343432,
        "border_radius": 2,
    },
    "ComboBox:disabled": {"color": _CLR_DISABLED_ALT},
}

STYLE_LINE = {"color": 0xFF454540}
STYLE_CHECKBOX = {
    "Label": {"color": _CLR_LABEL},
    "Label::disabled": {"color": _CLR_DISABLED},
    "CheckBox": {"color": 0xFF000000, "background_color": 0xFF9A9A9A, "font_size": 12, "border_radius": 2},
}

STYLE_RADIO_BUTTON = {
    "RadioButton": {
        "background_color": 0x0,
        "border_color": 0x0,
        "border_radius": 0,
        "border_width": 0,
        "margin": 0,
        "padding": 0,
    },
    "RadioButton:checked": {
        "background_color": 0x0,
    },
    "RadioButton:hovered": {
        "background_color": 0x0,
    },
    "RadioButton:pressed": {
        "background_color": 0x0,
    },
    "RadioButton.Image": {"image_url": __get_icon("radio_off")},
    "RadioButton.Image:checked": {"image_url": __get_icon("radio_on")},
}

STYLE_SEARCH_FIELD = {
    "StringField::search": {"color": _CLR_LABEL, "background_color": 0xFF23211F, "border_radius": 2},
    "StringField::search:pressed": {"background_color": 0xFF23211F},
    "Label::overlay": {"margin_width": 8, "color": _CLR_DISABLED},
}

STYLE_GROUP_BOX = {
    "ZStack::group_root": {"margin": 0, "padding": 0},
    "Rectangle::group_bounds": {
        "margin_width": 0,
        "margin_height": 8,
        "background_color": 0x0,
        "border_color": 0xFF666666,
        "border_radius": 4,
        "border_width": 1,
    },
    "Rectangle::snap_group_bounds": {
        "margin_width": 0,
        "margin_height": 0,
        "background_color": 0x0,
        "border_color": 0xFF666666,
        "border_radius": 4,
        "border_width": 1,
    },
    "VStack::group_text": {"margin": 0, "padding": 0},
    "Rectangle::label_back": {"background_color": 0xFF23211F},
    "Label::group_label": {"margin_width": 4, "margin_height": 0},
    "HStack::group_content": {"margin_width": 8, "margin_height": 16},
    "HStack::snap_group_content": {"margin_width": 24, "margin_height": 12},
}

STYLE_PLACEMENT_PANEL = {
    "CollapsableFrame::frame": {
        "background_color": 0xFF23211F,
        "secondary_color": 0xFF23211F,
        "color": 0xFFCCCCCC,
        "border_radius": 4.0,
        "border_color": 0x0,
        "border_width": 0,
        "font_size": 14,
        "padding": 5,
        "margin": 0,
    },
    "HStack::header": {"margin": 5},
    "CollapsableFrame::frame:hovered": {"secondary_color": 0xFF2E2E2B},
    "CollapsableFrame::frame:pressed": {"secondary_color": 0xFF2E2E2B},
    "CollapsableFrame": {
        "background_color": 0xFF343432,
        "secondary_color": 0xFF343432,
        "color": 0xFFAAAAAA,
        "border_radius": 4.0,
        "border_color": 0x0,
        "border_width": 0,
        "font_size": 14,
        "padding": 5,
        "margin": 0,
    },
    "CollapsableFrame:hovered": {"secondary_color": 0xFF2E2E2B},
    "CollapsableFrame:pressed": {"secondary_color": 0xFF2E2E2B},
    "VStack::container": {"margin": 8},
    "ComboBox": {
        "color": _CLR_LABEL,
        "background_color": 0xFF23211F,
        "secondary_color": 0xFF23211F,
        "border_radius": 2,
    },
    "ComboBox:disabled": {"color": _CLR_DISABLED},
}

STYLE_DISPLAY_PANEL = {
    **STYLE_COLLAPSABLE_FRAME,
    **{
        "VStack::container": {"margin": 8},
        "ComboBox": {
            "color": _CLR_LABEL,
            "background_color": 0xFF23211F,
            "secondary_color": 0xFF23211F,
            "border_radius": 2,
        },
        "ComboBox:disabled": {"color": _CLR_DISABLED},
    },
}
