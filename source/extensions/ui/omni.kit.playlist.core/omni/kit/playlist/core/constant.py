# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
"""This module defines a playlists root path and a class encapsulating constants that represent different play modes for camera playlist tools."""

PLAYLISTS_ROOT = "/View/Tools/CameraPlaylists"


class PlayMode:
    """A class for representing play modes.

    This class serves as a container for constants that define various play modes used in camera playlist tools. It provides a simple way to reference different transition styles applicable in camera playback.

    Note:
        No arguments or keyword arguments are required when using this class.

    """

    TRANSITION_CUT = "Cut"
    """str: Constant representing the cut transition mode."""
    TRANSITION_SMOOTH = "Smooth"
    """str: Constant representing the smooth transition mode."""
