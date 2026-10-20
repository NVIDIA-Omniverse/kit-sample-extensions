# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
from enum import Enum

MARKUP_ROOT_PRIM_PATH = "/Viewport_Markups"
SETTINGS_MARKUP_ROOT = "/exts/omni.kit.markup.core/"
APPLICATION_MODE = "/app/application_mode"
CURRENT_TOOL_PATH = "/app/viewport/currentTool"
SETTINGS_MARKUP_ACTIVE = SETTINGS_MARKUP_ROOT + "active_markup"
SETTINGS_MARKUP_EDITING = SETTINGS_MARKUP_ROOT + "editing_markup"


class ApproveType(Enum):
    NONE = -1
    REJECTED = 0
    APPROVED = 1
