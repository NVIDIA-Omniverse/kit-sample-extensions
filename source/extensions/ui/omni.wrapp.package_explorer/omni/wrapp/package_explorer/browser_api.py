# Copyright (c) 2023-2025, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.

from typing import List, Optional

import omni.ext
import omni.kit.app
import omni.kit.commands
import omni.kit.undo
import omni.usd
from pxr import Usd

from .asset import WrappAsset
from .browser_model import WrappAssetDetailItem
from .extension import WrappBrowserExtension, get_instance
from .utils import add_wrapp_asset_to_stage as utils_add_wrapp_asset_to_stage


async def find_assets(search_words: Optional[List[str]] = None) -> List[WrappAsset]:
    """Search assets in the current asset library

    Filter the current asset library by a list of search words.
    Search words are not case sensitive, and are matched partially against asset names as tags.
    If no search words are provided, all assets are returned.

    Example: Analyzing the results of searching with ["residential", "chair", "wood"] will reveal
    that the found assets have "residential" and "chair" in their tags, and "wood" in their names.

    Args:
        search_words (Optional[List[str]]): List of search words to filter assets on.

    Returns:
        List[WrappAsset]: List of WRAPP assets that match the search words.
    """
    ext: WrappBrowserExtension = get_instance()
    if not ext:
        return []
    collections = ext.browser_model.get_item_children(None)
    if not collections:
        return []
    # Tree mode, only has a default collection
    # First get categories to force traverse assets
    categories = ext.browser_model.get_item_children(collections[0])
    while True:
        for folder in ext.browser_model.folders_to_traverse:
            # Make sure all assets from all folders are loaded
            if not folder.prepared:
                await omni.kit.app.get_app().next_update_async()
                break
        else:
            # Reload categories after traverse done
            categories = ext.browser_model.get_item_children(collections[0])
            # First category "ALL" has all assets
            all_asset_items: List[WrappAssetDetailItem] = ext.browser_model.get_item_children(categories[0])
            if search_words:
                filtered_assets: List[WrappAsset] = []
                for asset_item in all_asset_items:
                    if asset_item.filter(search_words):
                        filtered_assets.append(asset_item.asset)
                return filtered_assets
            else:
                all_assets: List[WrappAsset] = [item.asset for item in all_asset_items]
                return all_assets


async def add_wrapp_asset_to_stage(
    stage: Usd.Stage, asset: WrappAsset, parent_path: str, as_payload: bool = False
) -> str:
    """Add a WRAPP asset to a stage at a specific path.

    Args:
        stage (Usd.Stage): The stage to add the asset to
        asset (WrappAsset): The WRAPP asset to add
        parent_path (str): The path to add the asset under
        as_payload (bool, optional): Whether to add as payload. Defaults to False.

    Returns:
        str: The path to the asset in the stage

    Raises:
        Exception: If adding the asset to stage fails
        ValueError: If stage or asset is invalid
    """
    return await utils_add_wrapp_asset_to_stage(stage, asset, parent_path, as_payload)


def refresh_browser():
    """Refreshes the assets and categories displayed in the browser.
    If the assets don't seem to be updating, try waiting for a few updates cycles:

    .. code-block:: python

            # Wait for new assets to load
        for _ in range(5):
            await omni.kit.app.get_app().next_update_async()
    """
    # TODO: Needs to report success/failure
    # TODO: Make it async
    ext: Optional[WrappBrowserExtension] = get_instance()
    # If the browser is not displayed, the browser_model is None
    if ext and ext.browser_model:
        ext.browser_model.refresh_asset_folders()
