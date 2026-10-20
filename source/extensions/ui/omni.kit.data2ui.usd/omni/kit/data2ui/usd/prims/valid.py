# Copyright (c) 2018-2023, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

valid_ui_prim_categories = {
    "Containers": [
        "Frame",
        "ScrollingFrame",
        "CollapsableFrame",
        "HStack",
        "VStack",
        "ZStack",
        "Placer",
    ],
    "Widgets": [
        "Button",
        "Image",
        "Rectangle",
        "Spacer",
        "Label",
        "Line",
        "Circle",
        "Triangle",
    ],
    "Style": [
        "StyleContainer",
        "Style",
    ],
    "Viewport": {
        "ViewportButton",
        "ViewportCircle",
    },
}

valid_ui_prim_types = []
for category, prim_types in valid_ui_prim_categories.items():
    valid_ui_prim_types += prim_types

valid_selector_states = ["hovered", "pressed", "selected", "disabled", "checked", "drop"]
