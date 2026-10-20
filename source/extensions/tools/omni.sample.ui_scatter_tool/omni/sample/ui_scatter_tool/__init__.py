# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

"""
Scatter Tool Extension for Omniverse Kit.

This extension provides a UI tool for scattering and duplicating objects in a USD scene,
with support for grid layouts, randomization, and efficient PointInstancer-based duplication.
"""

__all__ = ["ScatterCreatePointInstancerCommand"]

from .commands import ScatterCreatePointInstancerCommand
from .extension import ScatterWindowExtension  # Imported for extension system, not public API
