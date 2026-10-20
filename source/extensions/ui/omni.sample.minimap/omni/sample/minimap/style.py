# SPDX-FileCopyrightText: Copyright (c) 2024 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

import omni.ui as ui
from omni.ui import color as cl

# Color definitions
head_bg = cl.shade(cl("#090909c0"))  # Header/background dark overlay
tool_bg = cl.shade(cl("#303030ff"))  # Tool panel background
item_sel = cl.shade(cl("#d0d6dd"))  # Item selected state
item_label = cl.shade(cl("#b5b5b5"))  # Default label text color
item_dis = cl.shade(cl("#868686"))  # Disabled item color
item_hover = cl.shade(cl("#d4d4d4"))  # Item hover state
btn_bg = cl.shade(cl("#242424ff"))  # Button default background
btn_border = cl.shade(cl("#5a5858ff"))  # Button border color
btn_bg_clear = cl.shade(cl("#00000000"))  # Transparent button background
btn_bg_sel = cl.shade(cl("#515151ff"))  # Button selected background
btn_bg_hover = cl.shade(cl("#535353db"))  # Button hover background
btn_reset = cl.shade(cl("#81adfecc"))  # Reset button accent color
menu_bg = cl.shade(cl("#2a2a2aef"))  # Context menu background
menu_bg_sel = cl.shade(cl("#090909e9"))  # Menu item selected background
menu_label = cl.shade(cl("#ebebebff"))  # Menu text color
menu_border = cl.shade(cl("#b9b9b9e8"))  # Menu border color
label_sel = cl.shade(cl("#ffffffff"))  # Selected label text (white)
item_press = cl.shade(cl("#e5eef7"))  # Item pressed state
item_label_dim = cl.shade(cl("#c2c2c2"))  # Dimmed label text

# Shared tooltip style; use .copy() when assigning so per-dict mutations don't affect others
TOOLTIP_STYLE = {
    "background_color": menu_bg,
    "color": menu_label,
    "border_radius": 8,
    "border_width": 2,
    "padding": 2,
    "font_size": 13,
    "border_color": menu_border,
}

style = {  # Default UI style for main window elements
    "Label": {"color": item_label},
    "Button": {
        "color": item_label,
        "background_color": btn_bg,
        "border_color": btn_border,
        "border_radius": 20,
        "border_width": 1,
        "padding": 0,
        "margin": 0,
    },
    "Button:hovered": {
        "color": item_hover,
        "background_color": btn_bg_hover,
        "border_color": item_hover,
    },
    "ComboBox": {
        "color": item_label,
        "background_color": btn_bg,
        "border_color": btn_border,
        "border_radius": 20,
        "border_width": 1,
    },
    "ComboBox:hovered": {
        "color": item_hover,
        "background_color": btn_bg_hover,
        "border_color": item_hover,
    },
    "Tooltip": TOOLTIP_STYLE.copy(),
    "Rectangle": {
        "background_color": head_bg,
        "border_radius": 12,
    },
}

menu_style = {  # Style for context menus and dropdowns
    "border_width": 1,
    "border_radius": 6,
    "background_color": menu_bg,
    "border_color": menu_border,
    "margin": 0,
    "padding": 8,
    "MenuItem": {
        "alignment": ui.Alignment.CENTER,
        "color": menu_label,
        "background_selected_color": menu_bg_sel,
    },
    "MenuItem:hovered": {"color": label_sel},
    "MenuItem:pressed": {"color": item_press},
}

btn_style = {  # Style for icon buttons (normal state)
    "Button.Image": {"color": item_label, "alignment": ui.Alignment.CENTER},
    "background_color": btn_bg,
    "border_radius": 16,
    "border_width": 1,
    "border_color": item_hover,
    "margin": 0,
    "padding": 1.5,
    "image_height": 12,
    ":hovered": {"color": item_hover, "background_color": btn_bg_hover, "border_color": item_hover},
    ":selected": {"color": label_sel, "background_color": btn_bg_sel, "border_color": label_sel},
    "Tooltip": TOOLTIP_STYLE.copy(),
}

btn_style_dim = {  # Style for icon buttons (dimmed/disabled state)
    "Button.Image": {"color": cl("#404040"), "alignment": ui.Alignment.CENTER},
    "Button.Label": {"color": cl("#404040")},
    "background_color": btn_bg,
    "border_radius": 16,
    "border_width": 1,
    "border_color": cl("#404040"),
    "margin": 0,
    "padding": 1.5,
    "image_height": 12,
    "Button.Label:hovered": {"color": item_label},
    ":hovered": {"background_color": btn_bg, "border_color": item_label},
    "Button.Label:selected": {"color": label_sel},
    ":selected": {"background_color": btn_bg_sel, "border_color": label_sel},
    "Tooltip": TOOLTIP_STYLE.copy(),
}

base_style = {  # Base style for settings panel container
    "Label": {"color": item_label_dim},
    "ZStack": {
        "margin": 0,
        "padding": 0,
        "border_radius": 10,
        "border_width": 0,
        "font_size": 12,
    },
    "Rectangle": {
        "background_color": head_bg,
        "border_radius": 6,
    },
    "VStack": {
        "margin": 1,
        "padding": 2,
        "spacing": 0,
        "border_radius": 10,
    },
    "HStack": {
        "margin": 0,
        "padding": 0,
        "spacing": 0,
        "background_color": btn_bg,
    },
    "ComboBox:disabled": {"color": item_dis},
    "Label:disabled": {"color": item_dis},
    "Tooltip": TOOLTIP_STYLE.copy(),
    "CollapsableFrame": {
        "background_color": head_bg,
        "secondary_color": head_bg,
        "border_width": 0,
        "padding": 4,
        "margin": 2,
        "spacing": 0,
    },
    "CollapsableFrame:pressed": {
        "background_color": head_bg,
        "secondary_color": head_bg,
        "border_width": 0,
        "padding": 4,
        "margin": 2,
        "spacing": 0,
    },
    "CollapsableFrame:hovered": {"secondary_color": head_bg},
}
