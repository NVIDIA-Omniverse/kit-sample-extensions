# Copyright (c) 2018-2023, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

from ..property_enums import PropertyMode, PropertyType

button_properties = {
    "text": (PropertyType.STRING, PropertyMode.RW, "Button"),
    "image_url": (PropertyType.ASSET, PropertyMode.RW, None),
    "image_width": (PropertyType.INT, PropertyMode.RW, 100),
    "image_height": (PropertyType.INT, PropertyMode.RW, 100),
    "spacing": (PropertyType.FLOAT, PropertyMode.RW, None),
    "clicked_fn": (PropertyType.CALLABLE, PropertyMode.RW, None),
}

button_style_properties = [
    "background_color",
    "border_color",
    "border_radius",
    "border_width",
    "color",
    "padding",
    "font_size",
    "stack_direction",
    "image_url",
]
