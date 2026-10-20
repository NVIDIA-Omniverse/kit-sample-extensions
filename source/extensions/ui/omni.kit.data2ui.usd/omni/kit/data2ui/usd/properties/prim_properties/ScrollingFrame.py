# Copyright (c) 2018-2023, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

from ..property_enums import PropertyMode, PropertyType

scrolling_frame_properties = {
    # "alignment": (PropertyType.ENUM, PropertyMode.RW, None),
    "scroll_x": (PropertyType.FLOAT, PropertyMode.RW, None),
    # "scroll_x_max" : (PropertyType.FLOAT, PropertyMode.RW, None),
    "scroll_y": (PropertyType.FLOAT, PropertyMode.RW, None),
    # "scroll_y_max" : (PropertyType.FLOAT, PropertyMode.RW, None),
    "horizontal_scrollbar_policy": (PropertyType.ENUM, PropertyMode.RW, 0),
    "vertical_scrollbar_policy": (PropertyType.ENUM, PropertyMode.RW, 0),
}

scrolling_frame_style_properties = []
