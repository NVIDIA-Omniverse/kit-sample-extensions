# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
from omni.kit.widgets.custom import COLORS, DarkColors, LightColors

LIGHT_STYLE = {
    "GridView.Frame": {
        "background_color": COLORS.TRANSPARENT,
        "secondary_color": COLORS.TRANSPARENT,
        "border_radius": 0,
        "scrollbar_size": 1,
    },
    "GridView.Grid": {"background_color": LightColors.Background},
    "GridView.Item": {"background_color": LightColors.Background, "color": LightColors.Text},
}

DARK_STYLE = {
    "GridView.Frame": {
        "background_color": COLORS.TRANSPARENT,
        "secondary_color": COLORS.TRANSPARENT,
        "border_radius": 0,
        "scrollbar_size": 1,
    },
    "GridView.Grid": {"background_color": DarkColors.Background},
    "GridView.Item": {"background_color": DarkColors.Background, "color": DarkColors.Text},
}

UI_STYLES = {"NvidiaLight": LIGHT_STYLE, "NvidiaDark": DARK_STYLE}
