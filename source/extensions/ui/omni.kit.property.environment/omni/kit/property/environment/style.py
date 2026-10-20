# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
from pathlib import Path

from omni import ui

CURRENT_PATH = Path(__file__).parent
ICON_PATH = CURRENT_PATH.parent.parent.parent.parent.joinpath("data").joinpath("icons")


class Colors:
    Disabled = 0xFF50504E
    Background = 0xFF23211F
    Text = 0xFFB7B2AF
    Slider = 0xFF454545


SLIDER_STYLE = {
    "Rectangle::drag": {"background_color": Colors.Background, "border_width": 0, "border_radius": 2},
    "Label::drag": {"color": Colors.Text},
    "Triangle::drag": {"background_color": Colors.Text},
    "Rectangle::end": {"background_color": 0xFF454545},
    "Circle::cursor": {"background_color": Colors.Text},
    "Seperator": {"color": Colors.Text},
    "Rectangle::start": {"background_color": Colors.Background},
    "Rectangle::end": {"background_color": Colors.Slider},
}


PROPERTY_STYLES = {
    "Label::label:disabled": {"color": Colors.Disabled},
    "Field::models:disabled": {"color": Colors.Disabled, "background_color": 0xFF302F2D},
    "Slider::models:pressed": {"background_color": 0xFF23211F, "secondary_color": 0xFF23211F},
    "Slider::models:disabled": {"color": Colors.Disabled},
    "Slider::location": {"background_color": 0xFF23211F, "secondary_color": 0xFF535354},
    "Slider::weather": {"color": 0, "draw_mode": ui.SliderDrawMode.DRAG},
    "Slider::weather:disabled": {"secondary_color": Colors.Disabled},
    "Rectangle::mixed_overlay:disabled": {"background_color": Colors.Disabled},
    "CheckBox::greenCheck:disabled": {"background_color": Colors.Disabled},
    "Field.Frame": {"background_color": 0xFF23211F},
    "Material.Frame": {"background_color": 0xFF4A4A4A},
    "Date.Calendar": {"background_color": 0x0, "padding": 0},
    "Date.Calendar.Image": {"image_url": f"{ICON_PATH}/set_date_time.svg"},
    "TypeOption": {"background_color": 0x0, "padding": 0},
    "TypeOption.Image": {"image_url": f"{ICON_PATH}/radio_off.svg"},
    "TypeOption.Image:checked": {"image_url": f"{ICON_PATH}/radio_on.svg"},
    "Button": {"stack_direction": ui.Direction.RIGHT_TO_LEFT},
    "Button:pressed": {"background_color": 0xFF23211F},
    "Button.Image": {"alignment": ui.Alignment.RIGHT},
}
