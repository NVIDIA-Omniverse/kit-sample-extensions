# Copyright (c) 2023, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
"""SimReady Explorer API

This module contains the API for the SimReady Explorer extension.
"""

__all__ = [
    # Asset related
    "AssetFactory",
    "AssetType",
    "SimreadyAsset",
    "PropAsset",
    # Browser API functions
    "find_assets",
    "add_asset_to_stage",
    "add_asset_to_stage_using_prims",
    "get_average_position_of_prims",
    "get_selected_xformable_prim_paths",
    "refresh_browser",
    # Actions
    "add_asset_from_drag",
    "add_asset_with_variant_to_stage",
    "configure_prim",
    "deregister_actions",
    # Browser components
    "SimReadyDetailDelegate",
    "AssetFolder",
    "AssetDetailItem",
    "SimReadyBrowserModel",
    "SimReadyBrowserWidget",
    "ComboBoxModel",
    "ContextMenu",
    "EmptyPropertyDelegate",
    "SimReadyBrowserExtension",
    "get_instance",
    "MultiPropertyDelegate",
    "SimReadyFolderOptionsMenu",
    "PropAssetPropertyDelegate",
    "PropAssetTagsWidget",
    # Constants and styles
    "ICON_PATH",
    "PROPERTY_STYLES",
    "UI_STYLES",
    "CONTEXT_MENU_STYLE",
    # Drag and drop
    "SimReadyDragDropObject",
]

# All imports below are re-exported symbols (noqa: F401, F403)

from .actions import add_asset_from_drag, add_asset_with_variant_to_stage, configure_prim, deregister_actions
from .asset import AssetFactory, AssetType, PropAsset, SimreadyAsset
from .browser_api import (
    add_asset_to_stage,
    add_asset_to_stage_using_prims,
    configure_prim,
    find_assets,
    get_average_position_of_prims,
    get_selected_xformable_prim_paths,
    refresh_browser,
)
from .browser_delegate import SimReadyDetailDelegate
from .browser_folder import AssetFolder
from .browser_model import AssetDetailItem, SimReadyBrowserModel
from .browser_widget import SimReadyBrowserWidget
from .combobox_model import ComboBoxModel
from .context_menu import ContextMenu
from .empty_property_delegate import EmptyPropertyDelegate
from .extension import SimReadyBrowserExtension, get_instance
from .multi_property_delegate import MultiPropertyDelegate
from .options_menu import SimReadyFolderOptionsMenu
from .prop_property_delegate import PropAssetPropertyDelegate, PropAssetTagsWidget
from .style import CONTEXT_MENU_STYLE, ICON_PATH, PROPERTY_STYLES, UI_STYLES
from .viewport_drop_delegate import SimReadyDragDropObject
