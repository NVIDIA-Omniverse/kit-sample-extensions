# SPDX-FileCopyrightText: Copyright (c) 2018-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
"""This module defines constants for timeline minibar configuration and imports the TimelineMinibarExtension for managing timeline minibar settings."""

__all__ = [
    "MINIBAR_VISIBLE_PATH",
    "MINIBAR_BOTTOM_SETTINGS_PATH",
    "MINIBAR_TOGGLE_BY_HOVER_PATH",
]

from .extension import TimelineMinibarExtension
from .minibar_scene import MINIBAR_BOTTOM_SETTINGS_PATH, MINIBAR_TOGGLE_BY_HOVER_PATH, MINIBAR_VISIBLE_PATH
