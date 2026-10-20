# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
from omni.ui import color as cl


class Colors:
    CalendarBackground = cl.shade(0xFF24211F, light=0xFF444444)
    CalendarHovered = cl.shade(0x889E9E9E, light=0xFF535354)
    CalendarPressed = cl.shade(0xFF777777, light=0xFF777777)
    CalendarSelected = cl.shade(0x44E3B524, light=0x44E3B524)
    CalendarDay = cl.shade(0x0, light=0x0)
    CalendarText = cl.shade(0xFF9E9E9E, light=0xFF444444)
    CalendarComboBox = cl.shade(0xFF24211F, light=0xFFD6D6D6)


FontSize = 16
BORDER_RADIUS = 2
UI_STYLE = {
    "ComboBox::calendar": {
        "color": Colors.CalendarText,  # Color text in popup list
        "secondary_color": Colors.CalendarHovered,  # Color for scrollbar button
        "background_color": Colors.CalendarComboBox,
        "selected_color": Colors.CalendarSelected,  # Color for selected items
    },
    "Button::calendar": {"background_color": Colors.CalendarBackground, "border_radius": BORDER_RADIUS, "padding": 0},
    "Button::calendar:hovered": {"background_color": Colors.CalendarPressed},
    "Button::calendar:pressed": {"background_color": Colors.CalendarPressed},
    "Button::day": {"background_color": Colors.CalendarDay, "border_radius": BORDER_RADIUS},
    "Button::day:hovered": {"background_color": Colors.CalendarHovered},
    "Button::day:pressed": {"background_color": Colors.CalendarPressed},
    "Button::day:selected": {"background_color": Colors.CalendarSelected},
    "Label::calendar": {"color": Colors.CalendarText, "font_size": FontSize},
}
