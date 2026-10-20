# Copyright (c) 2018-2023, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

import enum
from typing import Callable, Union

import omni.ui as ui

StyleFloatProperties = [
    "border_radius",
    "border_width",
    "font_size",
    "margin",
    "margin_width",
    "margin_height",
    "padding",
    "padding_width",
    "padding_height",
    "secondary_padding",
    "scrollbar_size",
]

StyleColorProperties = [
    "background_color",
    "background_gradient_color",
    "background_selected_color",
    "border_color",
    "color",
    "selected_color",
    "secondary_color",
    "secondary_selected_color",
    "debug_color",
]

StyleEnumProperties = [
    "corner_flag",
    "alignment",
    "fill_policy",
    "draw_mode",
    "stack_direction",
    "horizontal_scrollbar_policy",
    "vertical_scrollbar_policy",
]

StyleStringProperties = ["custom"]  # custom is a temporary hack

StyleAssetProperties = ["image_url"]

StyleRelationshipProperties = ["binding"]

valid_style_properties = (
    StyleFloatProperties
    + StyleColorProperties
    + StyleEnumProperties
    + StyleStringProperties
    + StyleRelationshipProperties
)
valid_style_prim_properties = StyleFloatProperties + StyleColorProperties + StyleEnumProperties + StyleStringProperties


class PropertyType(enum.Enum):
    FLOAT = 0
    INT = 1
    COLOR3 = 2
    BOOL = 3
    STRING = 4
    DOUBLE3 = 5
    INT2 = 6
    DOUBLE2 = 7
    ENUM = 8
    CALLABLE = 9
    LENGTH = 10
    RELATIONSHIP = 11
    ASSET = 12


class PropertyMode(enum.Enum):
    RW = 0
    RO = 1
    STATIC = 2


class StylePropertyType(enum.Enum):
    ENUM = 0
    COLOR = 1
    FLOAT = 2
    STRING = 3
    RELATIONSHIP = 4
    ASSET = 5


def get_property_enum_class(property_name: str) -> Union[Callable, None]:  # pragma: no cover
    if property_name == "direction":
        return ui.Direction
    elif property_name in ("alignment", "arc"):
        return ui.Alignment
    elif property_name == "fill_policy":
        return ui.FillPolicy
    elif property_name == "raster_policy":
        return ui.RasterPolicy
    elif property_name == "size_policy":
        return ui.CircleSizePolicy
    elif property_name == "drag_axis":
        return ui.Axis
    elif property_name in ("horizontal_scrollbar_policy", "vertical_scrollbar_policy"):
        return ui.ScrollBarPolicy
    else:
        return None


def get_style_property_enum_class(property_name: str) -> Union[Callable, None]:  # pragma: no cover
    if property_name == "corner_flag":
        return ui.CornerFlag
    elif property_name == "alignment":
        return ui.Alignment
    elif property_name == "fill_policy":
        return ui.FillPolicy
    elif property_name == "draw_mode":
        return ui.SliderDrawMode
    elif property_name == "stack_direction":
        return ui.Direction
    else:
        return None


def get_style_property_enum_options(property_name: str) -> tuple:
    if property_name == "corner_flag":
        return (
            "NONE",
            "TOP_LEFT",
            "TOP_RIGHT",
            "BOTTOM_LEFT",
            "BOTTOM_RIGHT",
            "TOP",
            "BOTTOM",
            "LEFT",
            "RIGHT",
            "ALL",
        )
    elif property_name == "alignment":
        return (
            "UNDEFINED",
            "LEFT_TOP",
            "LEFT_CENTER",
            "LEFT_BOTTOM",
            "CENTER_TOP",
            "CENTER",
            "CENTER_BOTTOM",
            "RIGHT_TOP",
            "RIGHT_CENTER",
            "RIGHT_BOTTOM",
            "LEFT",
            "RIGHT",
            "H_CENTER",
            "TOP",
            "BOTTOM",
            "V_CENTER",
        )
    elif property_name == "fill_policy":
        return (
            "STRETCH",
            "PRESERVE_ASPECT_FIT",
            "PRESERVE_ASPECT_CROP",
        )
    elif property_name == "draw_mode":
        return (
            "FILLED",
            "HANDLE",
            "DRAG",
        )
    elif property_name == "stack_direction":
        return (
            "LEFT_TO_RIGHT",
            "RIGHT_TO_LEFT",
            "TOP_TO_BOTTOM",
            "BOTTOM_TO_TOP",
            "BACK_TO_FRONT",
            "FRONT_TO_BACK",
        )
    elif property_name in ("horizontal_scrollbar_policy", "vertical_scrollbar_policy"):
        return (
            "SCROLLBAR_AS_NEEDED",
            "SCROLLBAR_ALWAYS_ON",
            "SCROLLBAR_ALWAYS_OFF",
        )
    else:
        return ()


def get_property_enum_options(property_name: str) -> tuple:
    if property_name == "direction":
        return (
            "LEFT_TO_RIGHT",
            "RIGHT_TO_LEFT",
            "TOP_TO_BOTTOM",
            "BOTTOM_TO_TOP",
            "BACK_TO_FRONT",
            "FRONT_TO_BACK",
        )
    elif property_name == "alignment":
        return (
            "UNDEFINED",
            "LEFT_TOP",
            "LEFT_CENTER",
            "LEFT_BOTTOM",
            "CENTER_TOP",
            "CENTER",
            "CENTER_BOTTOM",
            "RIGHT_TOP",
            "RIGHT_CENTER",
            "RIGHT_BOTTOM",
            "LEFT",
            "RIGHT",
            "H_CENTER",
            "TOP",
            "BOTTOM",
            "V_CENTER",
        )
    elif property_name == "fill_policy":
        return (
            "STRETCH",
            "PRESERVE_ASPECT_FIT",
            "PRESERVE_ASPECT_CROP",
        )
    elif property_name == "raster_policy":
        return (
            "NEVER",
            "ON_DEMAND",
            "AUTO",
        )
    elif property_name == "arc":
        return (
            "UNDEFINED",
            "LEFT_TOP",
            "LEFT_CENTER",
            "LEFT_BOTTOM",
            "CENTER_TOP",
            "CENTER",
            "CENTER_BOTTOM",
            "RIGHT_TOP",
            "RIGHT_CENTER",
            "RIGHT_BOTTOM",
            "LEFT",
            "RIGHT",
            "H_CENTER",
            "TOP",
            "BOTTOM",
            "V_CENTER",
        )
    elif property_name == "size_policy":
        return (
            "STRETCH",
            "FIXED",
        )
    elif property_name == "drag_axis":
        return (
            "None",
            "X",
            "Y",
            "XY",
        )
    elif property_name in ("horizontal_scrollbar_policy", "vertical_scrollbar_policy"):
        return (
            "SCROLLBAR_AS_NEEDED",
            "SCROLLBAR_ALWAYS_ON",
            "SCROLLBAR_ALWAYS_OFF",
        )
    else:
        return ()


def get_style_property_type(property_name: str) -> StylePropertyType:
    if property_name in StyleRelationshipProperties:
        return StylePropertyType.RELATIONSHIP
    if property_name in StyleStringProperties:
        return StylePropertyType.STRING
    elif property_name in StyleEnumProperties:
        return StylePropertyType.ENUM
    elif property_name in StyleAssetProperties:
        return StylePropertyType.ASSET
    elif property_name in StyleColorProperties:
        return StylePropertyType.COLOR
    elif property_name in StyleFloatProperties:
        return StylePropertyType.FLOAT
    else:
        return StylePropertyType.FLOAT


def get_default_enum_property_value(enum):
    if not hasattr(enum, "__entries"):
        return
    return min((v[0] for v in enum.__entries.values()), key=lambda v: int(v))
