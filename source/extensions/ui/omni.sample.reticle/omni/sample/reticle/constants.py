# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

"""Constants used by the CameraReticleExtension"""

import enum


class CompositionGuidelines(enum.IntEnum):
    """Enum representing all of the composition modes.

    These guidelines help frame shots according to common cinematography rules:

    OFF: No composition guidelines are shown

    THIRDS: Rule of thirds grid - divides the frame into 9 equal sections using
            two horizontal and two vertical lines. Important elements should be
            placed along these lines or at their intersections.

    QUAD: Quad composition grid - divides the frame into 4 equal sections using
          one horizontal and one vertical line. Useful for symmetrical compositions
          or when centering subjects.

    CROSSHAIR: Simple crosshair in the center of the frame. Useful for precise
               centering of subjects or for technical alignment.
    """

    OFF = 0
    THIRDS = 1
    QUAD = 2
    CROSSHAIR = 3


# Default values for safe area percentages
DEFAULT_ACTION_SAFE_PERCENTAGE = 93  # Standard action safe area percentage for broadcast
DEFAULT_TITLE_SAFE_PERCENTAGE = 90  # Standard title safe area percentage for broadcast
DEFAULT_CUSTOM_SAFE_PERCENTAGE = 85  # Default custom safe area percentage
DEFAULT_LETTERBOX_RATIO = 2.35  # Standard widescreen cinema aspect ratio
DEFAULT_COMPOSITION_MODE = CompositionGuidelines.OFF
