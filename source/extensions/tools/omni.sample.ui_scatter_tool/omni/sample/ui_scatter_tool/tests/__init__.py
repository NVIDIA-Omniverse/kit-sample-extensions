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
Test suite for omni.sample.ui_scatter_tool extension.

This package contains comprehensive unit, integration, and UI tests for the scatter tool,
covering extension lifecycle, scatter algorithms, USD commands, and UI components.
"""

# Tests the USD commands for creating PointInstancers
from .test_commands import TestScatterCreatePointInstancerCommand

# Tests the main extension registration and initialization
from .test_extension import TestScatterExtension

# Tests end-to-end integration of different components
from .test_integration import TestScatterIntegration

# Tests the core scatter functionality and algorithms
from .test_scatter import TestScatterFunction

# Tests the UI window creation with with golden image comparison
from .test_window import TestWindow

from .test_utils import TestUtils
