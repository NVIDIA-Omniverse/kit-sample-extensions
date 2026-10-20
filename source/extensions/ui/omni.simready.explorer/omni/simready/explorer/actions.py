# Copyright (c) 2023, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.

import json
import os
from typing import Dict, List, Optional, Tuple

import carb
import carb.settings
import omni.client
import omni.kit.commands
import omni.usd
from pxr import Gf, Sdf, Tf, Usd, UsdGeom

from .style import SIMREADY_DRAG_PREFIX


def normalize_sdf_path(sdf_layer_path: str):
    return sdf_layer_path.replace("\\", "/")


def make_relative_to_layer(stage: Usd.Stage, url: str) -> str:
    # XXX: PyBind omni::usd::UsdUtils::makePathRelativeToLayer
    stage_layer = stage.GetEditTarget().GetLayer()
    if not stage_layer.anonymous and not Sdf.Layer.IsAnonymousLayerIdentifier(url):
        stage_layer_path = stage_layer.realPath
        if normalize_sdf_path(stage_layer_path) == url:
            carb.log_warn(f"Cannot reference {url} onto itself")
            return url
        relative_url = omni.client.make_relative_url(stage_layer_path, url)
        if relative_url:
            # omniverse path can have '\'
            return relative_url.replace("\\", "/")
    return url


def make_prim_path(stage: Usd.Stage, url: str, prim_path: Sdf.Path = None, prim_name: str = None):
    """Make a new/unique prim path for the given url"""
    if prim_path is None or prim_path.isEmpty:
        if stage.HasDefaultPrim():
            prim_path = stage.GetDefaultPrim().GetPath()
        else:
            prim_path = Sdf.Path.absoluteRootPath

    if prim_name is None:
        prim_name = Tf.MakeValidIdentifier(os.path.basename(os.path.splitext(url)[0]))

    return Sdf.Path(omni.usd.get_stage_next_free_path(stage, prim_path.AppendChild(prim_name).pathString, False))


def _add_asset_to_stage_helper(
    usd_context: omni.usd.UsdContext,
    stage: Usd.Stage,
    url: str,
    prim_path: Sdf.Path = None,
    payload: str = "",
    instanceable: str = "",
) -> Tuple[Sdf.Path, Usd.EditContext, str]:
    """Add a Usd.Prim to an exiting Usd.Stage, pointing to the url
    Args:
        usd_context (omni.usd.UsdContext): Usd context to add asset to.
        stage (Usd.Stage): Usd stage to add asset to.
        url (str): Url to asset to add.
    Kwargs:
        prim_path (Sdf.Path): Parent prim path to add asset to.
        payload (str): "payload" or "reference". If empty, use the setting at "/persistent/app/stage/dragDropImport".
        instanceable (str): "instanceable" or "noninstanceable". If empty (default), use the setting at "/persistent/app/stage/instanceableOnCreatingReference".
        selected_prims (List[Usd.Prim]): List of selected prims. If not empty (default), use the first prim's payload/reference status.
    """
    # Get a realtive URL if possible
    relative_url = make_relative_to_layer(stage, url)

    # When in auto authoring mode, don't create it in the current edit target
    # as it will be cleared each time to be moved to default edit layer.
    edit_context = None
    try:
        import omni.kit.usd.layers as layers

        layers_interface = layers.get_layers(usd_context)
        edit_mode = layers_interface.get_edit_mode()
        if edit_mode == layers.LayerEditMode.AUTO_AUTHORING:
            default_identifier = layers.get_default_edit_layer_identifier()
            edit_layer = Sdf.Layer.Find(default_identifier)
            if edit_layer is None:
                edit_layer = stage.GetRootLayer()
            edit_context = Usd.EditContext(stage, edit_layer)
    except ImportError:
        pass

    new_prim_path = make_prim_path(stage, url, prim_path=prim_path)
    if not instanceable:
        as_instanceable = carb.settings.get_settings().get("/persistent/app/stage/instanceableOnCreatingReference")
    else:
        as_instanceable = instanceable == "instanceable"

    # Determine if we should create a payload or reference
    if not payload:
        create_as_payload = carb.settings.get_settings().get("/persistent/app/stage/dragDropImport") == "payload"
    else:
        create_as_payload = payload == "payload"

    # Add asset to stage
    cmd_name = "CreatePayloadCommand" if create_as_payload else "CreateReferenceCommand"
    omni.kit.commands.execute(
        cmd_name, usd_context=usd_context, path_to=new_prim_path, asset_path=url, instanceable=as_instanceable
    )

    return (new_prim_path, edit_context, relative_url)


def set_prim_variants(stage: Usd.Stage, prim_path: Sdf.Path, variants: Dict[str, str]):
    """
    Set the variants on the provided prim.
    """
    prim = stage.GetPrimAtPath(prim_path)
    if prim:
        vsets = prim.GetVariantSets()
        for name, value in variants.items():
            carb.log_info(f"Try to set variant for {prim_path}: {name} -> {value}")
            vset = vsets.GetVariantSet(name)
            if vset:
                vset.SetVariantSelection(value)


def find_inst_prim(start_prim: Usd.Prim) -> Optional[Usd.Prim]:
    """Find the prim from the given prim path wose name ends in '_inst'."""
    if not start_prim:
        return None
    if start_prim.GetName().endswith("_inst"):
        return start_prim
    for child in start_prim.GetChildren():
        inst_prim = find_inst_prim(child)
        if inst_prim:
            return inst_prim
    return None


def is_physics_variant_enabled(variants: Dict[str, str]) -> bool:
    """Check if the physics variant is found and  enabled (not 'None').
    Args:
        variants (Dict[str, str]): Dictionary of variant name and value.
    """
    if variants and "PhysicsVariant" in variants and variants["PhysicsVariant"] != "":
        return True
    return False


def configure_prim(stage: Usd.Stage, prim_path: Sdf.Path, variants: Dict[str, str]) -> None:
    """Configure the variants of the given prim."""
    if not stage or not prim_path or prim_path.emptyPath or not variants:
        return
    # Set the variants on the prim at prim_path
    set_prim_variants(stage, prim_path, variants)


def add_asset_with_variant_to_stage(
    raw_data: dict, context: str = "", prim_path: Optional[Sdf.Path] = None
) -> Tuple[bool, str]:
    """Add simready asset to stage from raw data.

    Args:
        raw_data (dict): Json data decribe asset to add. See more in SimReadyBrowserModel.get_drag_mime_data()

    Kwargs:
        context (str): Name of usd content. Default ""
        prim_path (Optional[Sdf.Path]): Parent prim path to add asset. Default None means default prim.

    Returns:
        Tuple of success and added prim path.

    """
    usd_context = omni.usd.get_context(context)
    if not usd_context:
        carb.log_error("Failed to drop asset since usd context not found!")
        return False, ""
    stage = usd_context.get_stage()
    if not stage:
        carb.log_error("Failed to drop asset since usd stage not found!")
        return False, ""
    url = raw_data.get("url", "")
    if not url:
        carb.log_error("Failed to drop asset since url not defined!")
        return False, ""
    payload = raw_data.get("payload", "")
    instanceable = raw_data.get("instanceable", "")

    # Add the asset to stage
    dropped_path, _, _ = _add_asset_to_stage_helper(
        usd_context, stage, url, prim_path=prim_path, payload=payload, instanceable=instanceable
    )

    # Set variants on the added asset
    if dropped_path:
        variants = raw_data.get("variants", {})
        configure_prim(stage, dropped_path, variants)

    return True, dropped_path


def add_single_asset_from_drag(drag_mime_data: str, context: str = "", prim_path: Optional[Sdf.Path] = None) -> bool:
    """
    Add simready asset to stage from drag mime data.
    Args:
        drag_mime_data (str): Mime data decribe asset to add. See more in SimReadyBrowserModel.get_drag_mime_data()
    Kwargs:
        context (str): Name of usd content. Default ""
        prim_path (Optional[Sdf.Path]): Parent prim path to add asset. Default None means default prim.
    """
    if drag_mime_data.startswith(SIMREADY_DRAG_PREFIX):
        drag_mime_data = drag_mime_data[len(SIMREADY_DRAG_PREFIX) :]
    raw_data = json.loads(drag_mime_data)
    res, _ = add_asset_with_variant_to_stage(raw_data, context=context, prim_path=prim_path)
    return res


def add_asset_from_drag(drag_mime_data: str, context: str = "", prim_path: Optional[Sdf.Path] = None) -> bool:
    mime_datas = drag_mime_data.split("\n")
    for data in mime_datas:
        add_single_asset_from_drag(data, context=context, prim_path=prim_path)


def register_actions(extension_id: str, extension_instance):
    """
    Register actions.
    Args:
        extension_id (str): Extension ID whcih actions belongs to
    """
    try:
        import omni.kit.actions.core

        action_registry = omni.kit.actions.core.get_action_registry()
        actions_tag = "SimReady"

        action_registry.register_action(
            extension_id,
            "toggle_window",
            lambda: extension_instance._toggle_window(),
            display_name="SimReady Explorer show/hide window",
            description="SimReady Explorer show/hide window",
            tag=actions_tag,
        )

        action_registry.register_action(
            extension_id,
            "add_asset",
            lambda raw_data, context="", path_to=None: add_asset_with_variant_to_stage(raw_data, context, path_to),
            display_name="SimReady->Add Asset",
            description="Add SimReady asset to stage",
            tag=actions_tag,
        )

        action_registry.register_action(
            extension_id,
            "add_asset_from_drag",
            lambda drag_mime_data, context="", path_to=None: add_asset_from_drag(drag_mime_data, context, path_to),
            display_name="SimReady->Add Asset From Drag",
            description="Add SimReady asset to stage from dragging mime data",
            tag=actions_tag,
        )
    except ImportError:
        pass


def deregister_actions(extension_id: str):
    """
    Deregister actions.
    Args:
        extension_id (str): Extension ID whcih actions belongs to
    """
    try:
        import omni.kit.actions.core

        action_registry = omni.kit.actions.core.get_action_registry()
        action_registry.deregister_all_actions_for_extension(extension_id)
    except ImportError:
        pass
