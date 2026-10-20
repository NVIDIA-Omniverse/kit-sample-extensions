# Copyright (c) 2023, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.

from typing import Dict, List, Optional, Tuple

import carb
import omni.ext
import omni.kit.app
import omni.kit.commands
import omni.kit.undo
import omni.usd
from pxr import Gf, Sdf, Usd, UsdGeom

from .actions import _add_asset_to_stage_helper, configure_prim
from .asset import SimreadyAsset
from .browser_model import AssetDetailItem
from .extension import SimReadyBrowserExtension, get_instance


def get_selected_xformable_prim_paths(usd_context: omni.usd.UsdContext, stage: Usd.Stage) -> List[Sdf.Path]:
    """Get the list of selected Xformable prim paths in the stage.

    Args:
        usd_context (omni.usd.UsdContext): The USD context to get the selection from.
        stage (Usd.Stage): The stage to get the selection from.

    Returns:
        The list of prim paths of the selected Xformable prims in the stage,
        or an empty list if there's nothing selected.
    """

    if usd_context is None or stage is None:
        return []
    selection = usd_context.get_selection()
    return [
        path
        for path in selection.get_selected_prim_paths()
        if stage.GetPrimAtPath(path) and stage.GetPrimAtPath(path).IsA(UsdGeom.Xformable)
    ]


def get_average_position_of_prims(prims: List[Usd.Prim]) -> Gf.Vec3d:
    """Get the average position of a list of prims.

    Args:
        prims (List[Usd.Prim]): The list of prims to get the average position of.

    Returns:
      The average 3D position of the prims, or the origin if no prims provided.
    """

    position = Gf.Vec3d(0)
    for prim in prims:
        if prim.IsA(UsdGeom.Xformable):
            position += omni.usd.get_world_transform_matrix(prim).ExtractTranslation()
    if len(prims) > 0:
        position /= len(prims)
    return position


async def find_assets(search_words: Optional[List[str]] = None) -> List[SimreadyAsset]:
    """Search assets in the current asset library

    Filter the current asset library by a list of search words.
    Search words are not case sensitive, and are matched partially against asset names as tags.
    If no search words are provided, all assets are returned.

    Example: Analyzing the results of searching with ["residential", "chair", "wood"] will reveal
    that the found assets have "residential" and "chair" in their tags, and "wood" in their names.

    Args:
        search_words (Optional[List[str]]): List of search words to filter assets on.

    Returns:
        List[SimreadyAsset]: List of SimReady assets that match the search words.
    """
    ext: SimReadyBrowserExtension = get_instance()
    collections = ext.browser_model.get_item_children(None)
    # Tree mode, only has a default collection
    # First get categories to force traverse assets
    categories = ext.browser_model.get_item_children(collections[0])
    while True:
        for root_folder in ext.browser_model._root_folders:
            # Make sure all assets from all folders are loaded
            if not root_folder.prepared:
                await omni.kit.app.get_app().next_update_async()
                break
        else:
            # Reload categories after traverse done
            categories = ext.browser_model.get_item_children(collections[0])
            # First category "ALL" has all assets
            all_asset_items: List[AssetDetailItem] = ext.browser_model.get_item_children(categories[0])
            if search_words:
                filtered_assets: List[SimreadyAsset] = []
                for asset_item in all_asset_items:
                    if asset_item.filter(search_words):
                        filtered_assets.append(asset_item.asset)
                return filtered_assets
            else:
                all_assets: List[SimreadyAsset] = [item.asset for item in all_asset_items]
                return all_assets


def add_asset_to_stage(
    url: str,
    parent_path: Sdf.Path = Sdf.Path.emptyPath,
    position: Gf.Vec3d = Gf.Vec3d(0, 0, 0),
    variants: Optional[Dict[str, str]] = None,
    payload: bool = False,
    instanceable: bool = False,
) -> Tuple[bool, Sdf.Path]:
    """Adds an asset to the current stage.

    Args:
        url (str): Url of asset to add.
        parent_path (Sdf.Path): Path of parent prim to add asset to. If empty path, add to default prim or pseudo root.
        position (Gf.Vec3d): Position to add asset at.
        payload (bool): If True, add asset as payload, otherwise as reference.
        variants (Optional[Dict[str, str]]): Variants to set on added asset. Dictionary of variant set name and value.

    Returns:
        Tuple[bool, Sd.Path]: Tuple of success, and path to added prim.

    .. note::

        The actions of this function are undoable. If you want to add an asset without undo, use the following:

    .. code-block:: python

        with omni.kit.undo.disabled():
            add_asset_to_stage(...)
    """

    if not url:
        carb.log_error("Failed to add asset since url not defined!")
        return False, ""
    usd_context: omni.usd.UsdContext = omni.usd.get_context()
    stage: Usd.Stage = usd_context.get_stage() if usd_context else None
    if stage is None:
        carb.log_error(f"No valid stage found; cannot add {url}.")
        return False, ""

    # Creation and translation of the prim is done in a single undo group
    with omni.kit.undo.group():
        # Add the asset to the stage
        added_prim_path, _, _ = _add_asset_to_stage_helper(
            usd_context, stage, url, prim_path=parent_path, payload=payload, instanceable=instanceable
        )
        # Translate the added prim to the specified position
        omni.kit.commands.execute("TransformPrimSRTCommand", path=added_prim_path, new_translation=position)

    # Set the variants on the added prim
    if added_prim_path and variants:
        configure_prim(stage, added_prim_path, variants)

    return True, Sdf.Path(added_prim_path)


def add_asset_to_stage_using_prims(
    usd_context: omni.usd.UsdContext,
    stage: Usd.Stage,
    url: str,
    variants: Optional[Dict[str, str]] = None,
    replace_prims: bool = False,
    prim_paths: List[Sdf.Path] = [],
) -> Tuple[bool, Sdf.Path]:
    """Add an asset to a stage using a list of prims.

    The asset will be added to the average position of the provided prims, or the origin if no prims supplied.
    The asset will be added as a reference or payload based on whether the first provided prim has authored references or payloads.
    If no prims specified, the setting at "/persistent/app/stage/dragDropImport" is used.
    If the new asset is to replace the prims, the asset's parent will be the common ancestor of all prims.
    If no prims specified, the default prim or pseudo root will be used as the parent prim of the added asset.

    Args:
        usd_context (omni.usd.UsdContext): UsdContext to add asset to.
        stage (Usd.Stage): Stage to add asset to.
        url (str): Url of asset to add.
        variants (Optional[Dict[str, str]]): Variants to set on the added prim.
        replace_prims (bool): If True, replace the selection with the new asset.
        prim_paths (List[Sdf.Path]): List of prims to use for adding the asset.

    Returns:
        Tuple of success and added prim path.

    .. note::
        The actions of this function are undoable. If you want to add an asset without undo, use the following:

    .. code-block:: python

        with omni.kit.undo.disabled():
            add_asset_to_stage_using_prims(...)
    """
    if not url:
        carb.log_error("Failed to add asset since url not defined!")
        return False, ""
    if usd_context is None or stage is None:
        carb.log_error(f"No valid stage found; cannot add {url}.")
        return False, ""

    prims = [
        stage.GetPrimAtPath(path)
        for path in prim_paths
        if stage.GetPrimAtPath(path) and stage.GetPrimAtPath(path).IsA(UsdGeom.Xformable)
    ]

    # If replacing prims, all prims must be deletable\replaceable
    if replace_prims:
        for prim in prims:
            if not prim.IsValid() or (
                prim.GetMetadata("no_delete") is not None and prim.GetMetadata("no_delete") is True
            ):
                carb.log_error("Failed to add asset since cannot replace specified prims!")
                return False, ""

    # Get average position of prims
    position: Gf.Vec3d = get_average_position_of_prims(prims)

    # If prims specified, use the first prim's payload/reference status
    create_option = ""
    if prims and len(prims) > 0:
        for prim in prims:
            if prim.HasAuthoredReferences():
                create_option = "reference"
                break
            if prim.HasAuthoredPayloads():
                create_option = "payload"
                break

    # Determine parent path for new prim
    if replace_prims and prims and len(prims) > 0:
        parent_path: Sdf.Path = Sdf.Path.emptyPath
        for prim in prims:
            if parent_path == Sdf.Path.emptyPath:
                parent_path: Sdf.Path = prim.GetParent().GetPath()
            else:
                parent_path: Sdf.Path = parent_path.GetCommonPrefix(prim.GetParent().GetPath())
    elif stage.HasDefaultPrim():
        parent_path: Sdf.Path = stage.GetDefaultPrim().GetPath()
    else:
        parent_path: Sdf.Path = Sdf.Path.absoluteRootPath

    # Deletion, creation and translation of prims is done in a single undo group
    with omni.kit.undo.group():
        # If replacing prims, delete them before adding new ones to prevent potential name collision
        if replace_prims and prim_paths and len(prim_paths) > 0:
            omni.kit.commands.execute("DeletePrimsCommand", paths=prim_paths)
        # Add asset to stage
        added_prim_path, _, _ = _add_asset_to_stage_helper(
            usd_context, stage, url, prim_path=parent_path, payload=create_option, instanceable=""
        )
        # Translate the added prim to the specified position
        omni.kit.commands.execute("TransformPrimSRTCommand", path=added_prim_path, new_translation=position)

    # Set the variants on the added prim
    if added_prim_path and variants:
        configure_prim(stage, added_prim_path, variants)

    return True, added_prim_path


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
    ext: Optional[SimReadyBrowserExtension] = get_instance()
    # If the browser is not displayed, the browser_model is None
    if ext and ext.browser_model:
        ext.browser_model.refresh_current_asset_folder()
