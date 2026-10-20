# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

"""UI styles and color definitions for the reticle overlay and menu."""

import omni.ui as ui
from omni.ui import color as cl

ICON_PATH = "${omni.sample.reticle}/icons"

# Default colors for different reticle elements

cl.action_safe_default = cl.red  # Red for action safe area
cl.title_safe_default = cl.yellow  # Yellow for title safe area
cl.custom_safe_default = cl.green  # Green for custom safe area
cl.letterbox_default = cl(0.0, 0.0, 0.0, 0.75)  # Semi-transparent black for letterboxing
cl.comp_lines_default = cl(1.0, 1.0, 1.0, 0.6)  # Semi-transparent white for composition lines

# Style definitions for the safe areas control group
safe_areas_group_style = {
    "Label:disabled": {"color": cl(1.0, 1.0, 1.0, 0.2)},  # Dimmed white for disabled labels
    "FloatSlider:enabled": {
        "draw_mode": ui.SliderDrawMode.HANDLE,
        "background_color": cl(0.75, 0.75, 0.75, 1),  # Light gray background
        "color": cl.black,
    },
    "FloatSlider:disabled": {
        "draw_mode": ui.SliderDrawMode.HANDLE,
        "background_color": cl(0.75, 0.75, 0.75, 0.2),  # Transparent gray background
        "color": cl(0.0, 0.0, 1.0, 0.2),  # Dimmed blue
    },
    "CheckBox": {"background_color": cl(0.75, 0.75, 0.75, 1), "color": cl.black},  # Light gray background
    "Rectangle::ActionSwatch": {"background_color": cl.action_safe_default},  # Red swatch for action safe area
    "Rectangle::TitleSwatch": {"background_color": cl.title_safe_default},  # Yellow swatch for title safe area
    "Rectangle::CustomSwatch": {"background_color": cl.custom_safe_default},  # Green swatch for custom safe area
}

# Style definitions for the composition mode buttons
comp_group_style = {
    "Button.Image::Off": {"image_url": f"{ICON_PATH}/off.png"},  # Icon for disabled composition mode
    "Button.Image::Thirds": {"image_url": f"{ICON_PATH}/thirds.png"},  # Icon for rule of thirds grid
    "Button.Image::Quad": {"image_url": f"{ICON_PATH}/quad.png"},  # Icon for quad composition grid
    "Button.Image::Crosshair": {"image_url": f"{ICON_PATH}/crosshair.png"},  # Icon for crosshair mode
    "Button:checked": {"background_color": cl(1.0, 1.0, 1.0, 0.2)},  # Semi-transparent white for selected button
}
