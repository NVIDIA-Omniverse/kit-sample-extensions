# SPDX-FileCopyrightText: Copyright (c) 2022-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

"""
Tools module providing utility functions for the metrics assembler UI.

This module contains functions for:
- Managing anonymous layers for metrics assembly
- Resolving layer hierarchies and references
- Storing and retrieving resolve information in layer metadata
- Handling viewport settings and paths
"""

import hashlib

import carb.settings
import omni.usd
from omni.metrics.assembler.core import get_metrics_assembler_interface
from pxr import Ar, Gf, Sdf, Usd, UsdUtils


def add_anonymous_layer(stage: Usd.Stage) -> Sdf.Layer:
    """Create and add an anonymous layer to the stage for metrics assembly.

    Args:
        stage (Usd.Stage): The USD stage to add the layer to.

    Returns:
        Sdf.Layer: The created anonymous layer, or None if creation failed.
    """
    if stage:
        h = hashlib.new("md5")
        ma_layer_name = stage.GetRootLayer().identifier
        h.update(ma_layer_name.encode())
        ma_layer_name = "UnitsAdjust-" + h.hexdigest()

        layer_identifier = f"metrics:{ma_layer_name}.metricsAssembler"
        metrics_layer = Sdf.Layer.Find(layer_identifier)
        if metrics_layer:
            return metrics_layer

        file_format = Sdf.FileFormat.FindById("metricsAssembler")
        if file_format:
            # Use Sdf.Layer.New over Sdf.Layer.CreateNew so we don't try to write the URL to disk
            # We should be able to save the identifier into the root layer but we don't need to write
            # anything out
            metrics_layer = Sdf.Layer.New(file_format, layer_identifier)
            root_layer = stage.GetRootLayer()
            root_layer.subLayerPaths.insert(0, metrics_layer.identifier)
            return metrics_layer
    return None


def has_metrics_assembler_layer(stage: Usd.Stage) -> bool:
    """Check if the stage has a metrics assembler layer.

    Args:
        stage (Usd.Stage): The USD stage to check.

    Returns:
        bool: True if a metrics layer is found, False otherwise.
    """
    layer_stack = stage.GetLayerStack(False)
    layer_found = False
    for ly in layer_stack:
        if "metrics:" in ly.identifier:
            layer_found = True
            break

    return layer_found


def remove_anonymous_layer(stage: Usd.Stage, layer: Sdf.Layer) -> None:
    """Remove an anonymous layer from the stage.

    Args:
        stage (Usd.Stage): The USD stage containing the layer.
        layer (Sdf.Layer): The layer to remove.
    """
    if stage and layer:
        root_layer = stage.GetRootLayer()
        root_layer.subLayerPaths.remove(layer.identifier)


def resolve_layer_hierarchy(
    stage: Usd.Stage, stage_id: int, check_path: Sdf.Path, layer_id: str, remove_empty: bool
) -> Sdf.Layer:
    """Resolve a layer hierarchy for the given stage and path.

    Args:
        stage (Usd.Stage): The USD stage.
        stage_id (int): The stage cache ID.
        check_path (Sdf.Path): The path to check.
        layer_id (str): The layer identifier.
        remove_empty (bool): Whether to remove empty layers.

    Returns:
        Sdf.Layer: The resolved write layer, or None if resolution failed.
    """
    write_layer = None
    if layer_id:
        write_layer = Sdf.Layer.FindOrOpen(layer_id)

    if not write_layer:
        return None

    get_metrics_assembler_interface().set_resolve_layer(write_layer.identifier)
    get_metrics_assembler_interface().resolve_hierarchy(stage_id, str(check_path))
    get_metrics_assembler_interface().set_resolve_layer(None)
    if write_layer and remove_empty:
        if write_layer.empty:
            root_layer = stage.GetRootLayer()
            root_layer.subLayerPaths.remove(write_layer.identifier)
            write_layer = None
    return write_layer


def get_ref_url_from_path(stage: Usd.Stage, check_path: Sdf.Path) -> str:
    """Get the reference URL for a given path in the stage.

    Args:
        stage (Usd.Stage): The USD stage.
        check_path (Sdf.Path): The path to check.

    Returns:
        str: The reference URL, or None if not found.
    """
    asset_path = None
    if stage and check_path:
        prim = stage.GetPrimAtPath(check_path)

        ref_and_layers = omni.usd.get_composed_payloads_from_prim(prim, False)
        if len(ref_and_layers) == 0:
            ref_and_layers = omni.usd.get_composed_references_from_prim(prim, False)
        if len(ref_and_layers) > 0:
            ref, layer = ref_and_layers[0]
            asset_path = ref.assetPath
    return asset_path


# Metadata information format
# Version0:
#         dictionary metricsAssembler = {
#           dictionary "W:/cube_physics_m_ref_cm.usda" = {
#               dictionary "/World/cube_physics_m_ref_cm" = {
#                   string path = "/World/cube_physics_m_ref_cm"
#                   string write_layer = "metrics:root_layer_resolve.metricsAssembler"
#               }
#           }
#         }
# Version1:
#         dictionary metricsAssembler = {
#           dictionary "/World/cube_physics_m_ref_cm" = {
#              string write_layer = "metrics:root_layer_resolve.metricsAssembler"
#           }
#           dictionary "/World/cube_physics_m_ref_cm2" = {
#           }
#           int version = 1
#         }


def update_version0_to_version1(dict_v0: dict) -> dict:
    """Update metadata from version 0 to version 1 format.

    Args:
        dict_v0 (dict): Version 0 metadata dictionary.

    Returns:
        dict: Updated version 1 metadata dictionary.
    """
    out_dict = dict()
    out_dict["version"] = int(1)

    for entry_key in dict_v0:
        url_dict = dict_v0[entry_key]
        for url_key in url_dict:
            ma_entry = url_dict[url_key]
            write_layer = ma_entry.get("write_layer")
            check_path = ma_entry["path"]
            path_entry = dict()
            if write_layer:
                path_entry["write_layer"] = write_layer
            out_dict[check_path] = path_entry

    return out_dict


def store_resolve_information(stage: Usd.Stage, check_path: Sdf.Path, write_layer: Sdf.Layer) -> None:
    """Store resolve information in the stage metadata.

    Args:
        stage (Usd.Stage): The USD stage.
        check_path (Sdf.Path): The path to store information for.
        write_layer (Sdf.Layer): The write layer to store.
    """
    with Usd.EditContext(stage, stage.GetRootLayer()):
        metrics_assembler_dict = stage.GetMetadataByDictKey("customLayerData", "metricsAssembler")
        if metrics_assembler_dict is None:
            metrics_assembler_dict = dict()
            metrics_assembler_dict["version"] = int(1)

        path_dict = metrics_assembler_dict.get(check_path)
        if path_dict is None:
            path_dict = dict()
        if write_layer:
            path_dict["write_layer"] = write_layer.identifier
        metrics_assembler_dict[str(check_path)] = path_dict
        stage.SetMetadataByDictKey("customLayerData", "metricsAssembler", metrics_assembler_dict)


def remove_resolve_information(stage: Usd.Stage, check_path: Sdf.Path) -> None:
    """Remove resolve information from the stage metadata.

    Args:
        stage (Usd.Stage): The USD stage.
        check_path (Sdf.Path): The path to remove information for.
    """
    metrics_assembler_dict = stage.GetMetadataByDictKey("customLayerData", "metricsAssembler")
    if metrics_assembler_dict is None:
        return

    del_entry = metrics_assembler_dict.pop(str(check_path), None)
    if del_entry:
        with Usd.EditContext(stage, stage.GetRootLayer()):
            stage.SetMetadataByDictKey("customLayerData", "metricsAssembler", metrics_assembler_dict)


def rename_resolve_information(stage: Usd.Stage, pre_path: Sdf.Path, post_path: Sdf.Path) -> None:
    """Rename resolve information in the stage metadata.

    Args:
        stage (Usd.Stage): The USD stage.
        pre_path (Sdf.Path): The original path.
        post_path (Sdf.Path): The new path.
    """
    metrics_assembler_dict = stage.GetMetadataByDictKey("customLayerData", "metricsAssembler")
    if metrics_assembler_dict is None:
        return

    del_entry = metrics_assembler_dict.pop(str(pre_path), None)
    if del_entry:
        metrics_assembler_dict[str(post_path)] = del_entry

        with Usd.EditContext(stage, stage.GetRootLayer()):
            stage.SetMetadataByDictKey("customLayerData", "metricsAssembler", metrics_assembler_dict)


def read_resolve_layer(top_stage: Usd.Stage, layer: Sdf.Layer, notice_listener) -> None:
    """Read and resolve layers from stage metadata.

    Args:
        top_stage (Usd.Stage): The top-level USD stage.
        layer (Sdf.Layer): The layer to read from.
        notice_listener: The notice listener to update.
    """
    metrics_assembler_dict = layer.customLayerData.get("metricsAssembler")
    if metrics_assembler_dict is None:
        return

    if not has_metrics_assembler_layer(top_stage):
        return

    # put together the stage
    stage = top_stage
    if layer != top_stage.GetRootLayer():
        stage = Usd.Stage.Open(layer.identifier)
        cache = UsdUtils.StageCache.Get()
        cache.Insert(stage)

    # version check
    version = metrics_assembler_dict.get("version")
    if not version:
        updated_dict = update_version0_to_version1(metrics_assembler_dict)
        layerData = layer.customLayerData
        layerData["metricsAssembler"] = updated_dict
        layer.customLayerData = layerData
        metrics_assembler_dict = updated_dict

    # first get all the sub layers for recursive parse
    url_set = set()
    url_map = {}
    for entry_key in metrics_assembler_dict:
        if entry_key == "version":
            continue

        url = get_ref_url_from_path(stage, entry_key)
        if url:
            url_set.add(url)
            url_map[entry_key] = url

    for url in url_set:
        asset_id = Sdf.ComputeAssetPathRelativeToLayer(stage.GetRootLayer(), url)
        resolved_path = Ar.GetResolver().Resolve(asset_id)
        recursive_layer = Sdf.Layer.Find(resolved_path)
        if recursive_layer:
            read_resolve_layer(stage, recursive_layer, notice_listener)

    for entry_key in metrics_assembler_dict:
        if entry_key == "version":
            continue

        ma_entry = metrics_assembler_dict.get(entry_key)
        write_layer = ma_entry.get("write_layer")
        check_path = Sdf.Path(entry_key)
        url = url_map.get(entry_key)
        if write_layer and url:
            layer_stack = stage.GetLayerStack(False)
            layer_found = False
            for ly in layer_stack:
                if write_layer in ly.identifier:
                    layer_found = True
                    break

            if layer_found:
                stage_id = UsdUtils.StageCache.Get().GetId(stage).ToLongInt()
                out_write_layer = resolve_layer_hierarchy(stage, stage_id, check_path, write_layer, False)
                if stage == top_stage:
                    notice_listener.add_path(check_path, url, out_write_layer)

    if stage != top_stage:
        cache.Erase(stage)


def read_and_resolve_metrics_assembler(stage: Usd.Stage, notice_listener) -> None:
    """Read and resolve metrics assembler information for a stage.

    Args:
        stage (Usd.Stage): The USD stage to process.
        notice_listener: The notice listener to update.
    """
    layer = stage.GetRootLayer()
    read_resolve_layer(stage, layer, notice_listener)


def clean_layer_path(stage: Usd.Stage, layer: Sdf.Layer, path: Sdf.Path) -> None:
    """Remove a prim at the given path from a layer.

    Args:
        stage (Usd.Stage): The USD stage.
        layer (Sdf.Layer): The layer to clean.
        path (Sdf.Path): The path to remove.
    """
    if stage and layer and path:
        with Usd.EditContext(stage, layer):
            stage.RemovePrim(path)


def re_resolve_layer(stage: Usd.Stage, ma_manager, url: str, check_path: Sdf.Path, write_layer_id_in: str) -> Sdf.Layer:
    """Re-resolve a layer for the given stage and path.

    Args:
        stage (Usd.Stage): The USD stage.
        ma_manager: The metrics assembler manager.
        url (str): The reference URL.
        check_path (Sdf.Path): The path to check.
        write_layer_id_in (str): The input write layer ID.

    Returns:
        Sdf.Layer: The resolved write layer, or None if resolution failed.
    """
    write_layer = None
    write_layer_id = write_layer_id_in
    if write_layer_id:
        write_layer = Sdf.Layer.FindOrOpen(write_layer_id)
        clean_layer_path(stage, write_layer, check_path)

    if not write_layer:
        write_layer = ma_manager.get_resolve_layer()
        if not write_layer:
            write_layer = add_anonymous_layer(stage)
            write_layer_id = write_layer.identifier
            ma_manager.set_resolve_layer(write_layer)

    if write_layer:
        asset_id = Sdf.ComputeAssetPathRelativeToLayer(stage.GetRootLayer(), url)
        resolved_path = Ar.GetResolver().Resolve(asset_id)
        sdf_layer = Sdf.Layer.Find(resolved_path)
        if sdf_layer:
            stage_id = UsdUtils.StageCache.Get().GetId(stage).ToLongInt()
            write_layer = resolve_layer_hierarchy(stage, stage_id, check_path, write_layer_id, False)
            if write_layer and write_layer.empty:
                remove_anonymous_layer(stage, write_layer)
                write_layer = None
                ma_manager.set_resolve_layer(None)
            store_resolve_information(stage, check_path, write_layer)
    return write_layer


def get_viewport_defaults_setting_path(setting_name: str) -> str:
    """Get the default viewport settings path.

    Args:
        setting_name (str): The setting name.

    Returns:
        str: The full settings path.
    """
    return f"/app/viewport/defaults/{setting_name}"


def get_per_viewport_setting_path(viewport_id: str, setting_name: str) -> str:
    """Get the per-viewport settings path.

    Args:
        viewport_id (str): The viewport ID.
        setting_name (str): The setting name.

    Returns:
        str: The full settings path.
    """
    return f"/app/viewport/{viewport_id}/{setting_name}"


def get_persistent_per_viewport_setting_path(viewport_id: str, setting_name: str) -> str:
    """Get the persistent per-viewport settings path.

    Args:
        viewport_id (str): The viewport ID.
        setting_name (str): The setting name.

    Returns:
        str: The full settings path.
    """
    return f"/persistent{get_per_viewport_setting_path(viewport_id, setting_name)}"


def resolve_viewport_setting(viewport_id: str, setting_name: str):
    """Resolve a viewport setting by checking persistent, per-viewport and default paths.

    Args:
        viewport_id (str): The viewport ID.
        setting_name (str): The setting name.

    Returns:
        The resolved setting value.
    """
    default_path = get_viewport_defaults_setting_path(setting_name)
    viewport_path = get_per_viewport_setting_path(viewport_id, setting_name)
    persistent_viewport_path = get_persistent_per_viewport_setting_path(viewport_id, setting_name)
    value = carb.settings.get_settings().get(persistent_viewport_path)
    if value is not None:
        return value
    value = carb.settings.get_settings().get(viewport_path)
    if value is not None:
        return value
    value = carb.settings.get_settings().get(default_path)
    return value
