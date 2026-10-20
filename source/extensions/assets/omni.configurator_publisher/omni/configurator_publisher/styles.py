# SPDX-FileCopyrightText: Copyright (c) 2024-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
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


class Colors:
    Higlight = 0xFF9E9E9E
    Disabled = 0xFF343432
    Background = cl("#1F2124")
    Text = cl("#CCCCCC")
    TextWarning = 0xFF3333A1


UI_STYLES = {
    "PublishButton": {"background_color": Colors.Background, "margin": 0, "padding": 3, "border_radius": 4},
    "PublishButton:hovered": {"background_color": Colors.Higlight},
    "PublishButton:disabled": {"background_color": Colors.Disabled},
    "PublishButton:pressed": {"background_color": Colors.Higlight},
    "PhaseLabel": {"color": Colors.Text},
    "PhaseLabel.Disabled": {"color": Colors.Disabled},
    "ProgressBar": {"color": cl("#76b900"), "secondary_color": Colors.Text},
    # "ProgressBar": {"color": cl("#76b900"), "secondary_color": cl("#bf2121")},
    "TimeElapsedLabel": {"color": Colors.Text},
    "TimeElapsedLabel.Warning": {"color": Colors.TextWarning},
}
