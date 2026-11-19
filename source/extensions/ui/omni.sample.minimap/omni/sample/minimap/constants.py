# SPDX-FileCopyrightText: Copyright (c) 2024 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

ICON_PATH = ""  # Set at extension startup from extension path
SETTINGS_ROOT = "/exts/omni.sample.minimap/"

# Navigation tool settings
NAV_BOTTOM_OFFSET = SETTINGS_ROOT + "bottom_offset"  # Vertical offset from bottom in pixels
NAV_IS_LARGE = SETTINGS_ROOT + "is_large"  # Whether navigation tool is in large mode
NAV_LARGE_SIZE = SETTINGS_ROOT + "large_size"  # Size in pixels when in large mode
NAV_SMALL_SIZE = SETTINGS_ROOT + "small_size"  # Size in pixels when in small mode
NAV_IS_VISIBLE = SETTINGS_ROOT + "isVisible"  # Whether navigation tool is visible
NAV_DEFAULT_OP = SETTINGS_ROOT + "defaultOperation"  # Default navigation operation
