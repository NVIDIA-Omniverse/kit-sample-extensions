# SPDX-FileCopyrightText: Copyright (c) 2018-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
from functools import lru_cache
from pathlib import Path

import carb
import omni.ui as ui


@lru_cache()
def get_style():
    CURRENT_PATH = Path(__file__).parent.absolute()
    ICON_PATH = CURRENT_PATH.parent.parent.parent.parent.joinpath("icons")

    UI_THEME = carb.settings.get_settings().get_as_string("/persistent/app/window/uiStyle") or "NvidiaDark"

    UI_STYLE = {
        "ZoomBar": {"background_color": ui.color.shade(0xFF454545, light=0x0), "border_radius": 2},
        "ZoomBar.Slider": {
            "draw_mode": ui.SliderDrawMode.HANDLE,
            "background_color": ui.color.shade(0xDD23211F, light=0xFF23211F),
            "secondary_color": ui.color.shade(0xFF9E9E9E, light=0xFF9D9D9D),
            "color": 0x0,
            "alignment": ui.Alignment.CENTER,
            "padding": 0,
            "margin": 0,
        },
        "ZoomBar.Button.Thumbnail": {"background_color": 0x0, "margin": 0, "padding": 0},
        "ZoomBar.Button.Thumbnail.Image": {
            "image_url": f"{ICON_PATH}/{UI_THEME}/thumbnail.svg",
            "color": 0xFFFFFFFF,
            "alignment": ui.Alignment.CENTER,
        },
        "ZoomBar.Button.List": {"background_color": 0x0, "margin": 0, "padding": 0},
        "ZoomBar.Button.List.Image": {
            "image_url": f"{ICON_PATH}/{UI_THEME}/list.svg",
            "color": 0xFFFFFFFF,
            "alignment": ui.Alignment.CENTER,
        },
    }

    return UI_STYLE
