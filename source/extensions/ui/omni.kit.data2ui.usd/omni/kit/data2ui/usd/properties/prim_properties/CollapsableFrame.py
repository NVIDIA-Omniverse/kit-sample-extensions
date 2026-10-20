# Copyright (c) 2018-2023, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

from ..property_enums import PropertyMode, PropertyType

collapsable_frame_properties = {
    # "alignment": (PropertyType.ENUM, PropertyMode.RW, None),
    "title": (PropertyType.STRING, PropertyMode.RW, ""),
    "collapsed": (PropertyType.BOOL, PropertyMode.RW, False),
}

collapsable_frame_style_properties = []
