# Copyright (c) 2018-2023, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

from ..property_enums import PropertyMode, PropertyType

viewport_button_properties = {
    "visible": (PropertyType.BOOL, PropertyMode.RW, True),
    "enabled": (PropertyType.BOOL, PropertyMode.RW, True),
    "selected": (PropertyType.BOOL, PropertyMode.RW, False),
    # "checked": (PropertyType.BOOL, PropertyMode.RW, False),
    "target_path": (PropertyType.RELATIONSHIP, PropertyMode.RW, None),
    "clicked_fn": (PropertyType.CALLABLE, PropertyMode.RW, None),
}

viewport_button_style_properties = [
    "background_color",
    "border_color",
    "border_width",
    "height",
    "width",
    "image_url",
    "binding",  # Will be a relationship to StyleContainer
]
