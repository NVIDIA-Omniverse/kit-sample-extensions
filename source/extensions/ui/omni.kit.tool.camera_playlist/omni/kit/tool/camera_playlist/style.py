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
from omni.kit.widgets.custom import COLORS, DarkColors, LightColors

CURRENT_PATH = Path(__file__).parent
ICON_PATH = CURRENT_PATH.parent.parent.parent.parent.joinpath("icons")

LIGHT_STYLE = {
    "Rectangle": {"background_color": LightColors.Background},
    "TreeView.Button": {
        "background_color": 0xFF707070,
        "stack_direction": ui.Direction.LEFT_TO_RIGHT,
        "color": LightColors.Text,
        "border_radius": 0,
        "margin": 0,
    },
    "TreeView.Button:hovered": {"background_color": LightColors.ButtonHovered},
    "TreeView.Button:pressed": {"background_color": LightColors.ButtonPressed},
    "TreeView.Button.Image": {
        "image_url": f"{ICON_PATH}/add_dark.svg",
        "alignment": ui.Alignment.CENTER,
        "color": 0xFF76A371,
    },
    "TreeView.Button.Label": {"color": LightColors.Text, "alignment": ui.Alignment.LEFT_CENTER},
    "TreeView.Button.Label:disabled": {"color": LightColors.TextDisabled, "alignment": ui.Alignment.LEFT_CENTER},
    "Separator": {"color": 0xFF989898},
}

DARK_STYLE = {
    "Rectangle": {"background_color": DarkColors.Background},
    "TreeView": {"border_width": 4},
    "TreeView.Button": {
        "background_color": 0xFF707070,
        "stack_direction": ui.Direction.LEFT_TO_RIGHT,
        "color": DarkColors.Text,
        "border_radius": 0,
        "margin": 0,
    },
    "TreeView.Button:hovered": {"background_color": DarkColors.ButtonHovered},
    "TreeView.Button:pressed": {"background_color": DarkColors.ButtonPressed},
    "TreeView.Button.Image": {
        "image_url": f"{ICON_PATH}/add_dark.svg",
        "alignment": ui.Alignment.CENTER,
        "color": 0xFF76A371,
    },
    "TreeView.Button.Label": {"color": DarkColors.Text, "alignment": ui.Alignment.LEFT_CENTER},
    "TreeView.Button.Label:disabled": {"color": DarkColors.TextDisabled, "alignment": ui.Alignment.LEFT_CENTER},
    "TreeView:drop": {"background_color": 0xFFC5911A},
}
WINDOW_STYLE = {"NvidiaLight": LIGHT_STYLE, "NvidiaDark": DARK_STYLE}
