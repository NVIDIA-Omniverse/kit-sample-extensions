# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
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

# Use same context menu style with content browser
cl.context_menu_background = cl("#343432")
cl.context_menu_separator = cl("449E9E9E")
cl.context_menu_text = cl("#9E9E9E")

CONTEXT_MENU_STYLE = {
    "Menu": {"background_color": cl.context_menu_background, "color": cl.context_menu_text, "border_radius": 2},
    "Menu.Item": {"background_color": cl.transparent, "margin": 0},
    "Separator": {"background_color": cl.transparent, "color": cl.context_menu_separator},
}

cl.property_toolbar_selected = cl.shade(cl("1F2123"), light=cl("545353"))
cl.splitter_hover = cl("3B70B0")

PROPERTY_STYLES = {
    "PropertyToolBar.Button": {"background_color": cl.transparent, "padding": 3, "margin": 0},
    "PropertyToolBar.Button:selected": {"background_color": cl.property_toolbar_selected},
    "Splitter": {"background_color": cl.transparent, "margin_width": 0},
    "Splitter:hovered": {"background_color": cl.splitter_hover},
    "Splitter:pressed": {"background_color": cl.splitter_hover},
}
