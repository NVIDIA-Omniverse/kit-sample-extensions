# Copyright (c) 2023-2025, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.

"""Package Explorer API

This module provides functionality for browsing and managing WRAPP (Workflow for Reusable Assets and Pipeline Packages) packages.
It allows users to search, install and update WRAPP assets in USD stages.
"""

__all__ = [
    "WrappAsset",
    "WrappAssetDetailItem",
    "WrappBrowserModel",
    "WrappBrowserExtension",
    "WrappBrowserWindow",
    "add_asset_from_drag",
    "add_wrapp_asset_to_stage",
    "get_instance",
    "find_assets",
    "refresh_browser",
    "WRAPP_EXPLORER_NAME",
    "WRAPP_EXPLORER_DRAG_PREFIX",
]

from .asset import WrappAsset
from .browser_api import add_wrapp_asset_to_stage, find_assets, refresh_browser
from .browser_model import WrappAssetDetailItem, WrappBrowserModel
from .consistents import WRAPP_EXPLORER_DRAG_PREFIX, WRAPP_EXPLORER_NAME
from .extension import WrappBrowserExtension, get_instance
from .utils import add_asset_from_drag
from .window import WrappBrowserWindow
