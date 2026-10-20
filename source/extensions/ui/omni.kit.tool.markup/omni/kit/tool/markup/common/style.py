# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
from omni import ui
from omni.ui import color as cl


class ConstSize:
    Radius = 2


class Colors:
    window = cl.shade(0xA0000000, light=0xA0000000)
    transparent = cl.shade(0x0, light=0x0)
    line = cl.shade(0xFF9E9E9E, light=0xFF9E9E9E)
    tooltip = cl.shade(0xFFA5C5CA, light=0xFFA5C5CA)
    shortcut = cl.shade(0xFF444444, light=0xFF444444)
    shortcut_white = cl.shade(0xFFCCCCCC, light=0xFFCCCCCC)
    Background = ui.color.shade(0xFF23211F, light=0xFF535354)
    Text = ui.color.shade(0xFFA1A1A1, light=0xFFE0E0E0)
    DarkText = ui.color.shade(0xFF504F50, light=0xFFA1A1A1)
    ResetInvalid = ui.color.shade(0xFF505050)
    Reset = ui.color.shade(0xFFA07D4F)
    Line = ui.color.shade(0x338A8777)


PREFERENCE_PAGE_STYLES = {
    "Reset_invalid.Rect": {"background_color": Colors.ResetInvalid, "border_radius": ConstSize.Radius},
    "Reset.Rect": {"background_color": Colors.Reset, "border_radius": ConstSize.Radius},
    "Setting.Field": {"color": Colors.Text, "background_color": Colors.Background},
    "Setting.Field:disabled": {"color": Colors.DarkText},
    "Setting.Label": {"color": Colors.Text},
    "Setting.Label:disabled": {"color": Colors.DarkText},
    "Seperator": {"color": Colors.Line},
}
