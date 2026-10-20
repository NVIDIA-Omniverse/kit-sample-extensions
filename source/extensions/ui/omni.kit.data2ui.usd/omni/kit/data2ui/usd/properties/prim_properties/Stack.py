# Copyright (c) 2018-2023, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

from ..property_enums import PropertyMode, PropertyType

stack_properties = {
    # "direction": (PropertyType.ENUM, PropertyMode.RW),
    "content_clipping": (PropertyType.BOOL, PropertyMode.RW, False),
    "spacing": (PropertyType.FLOAT, PropertyMode.RW, 0.0),
    # "send_mouse_events_to_back": (PropertyType.BOOL, PropertyMode.RW),
}

stack_style_properties = ["debug_color"]
