# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
"""This module provides classes and functions for browsing, loading, and managing USD and MDL material files within Omniverse Kit, including asynchronous file reading, sub-material extraction, thumbnail handling, and drag-and-drop support."""

from .delegate import MaterialDetailDelegate
from .extension import *
from .model import MaterialBrowserModel, MaterialDetailItem, MaterialFile
from .options_menu import MaterialOptionsMenu

__all__ = [
    "MaterialBrowserModel",
    "MaterialDetailItem",
    "MaterialFile",
    "MaterialDetailDelegate",
    "MaterialOptionsMenu",
]
