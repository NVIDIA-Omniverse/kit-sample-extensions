# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
import re
from typing import List

import carb
import carb.tokens
import omni.client
import omni.kit.commands
import omni.kit.usd.layers as layers
from pxr import Sdf, Usd


def get_environment_edit_target_layer(stage: Usd.Stage) -> Sdf.Layer:
    """Return a writable layer for environment edits so they apply immediately (OMPE-64890)."""
    live_syncing = layers.get_live_syncing()
    if live_syncing.is_in_live_session():
        # OM-62555: In living mode, ENV should be in .live file
        root_live_layer = Sdf.Find(live_syncing.get_current_live_session().root)
        if root_live_layer is not None:
            return root_live_layer
    root_layer = stage.GetRootLayer()
    if root_layer.permissionToEdit:
        # OM-57577: Otherwise, create ENV in root layer
        return root_layer
    return stage.GetSessionLayer()


def get_environment_edit_context(stage: Usd.Stage) -> Usd.EditContext:
    """Return an edit context every environment write has to be authored in (OMPE-64890).

    Only redirects when the root layer is not writable, so a live session keeps authoring where it
    did and the removal, which edits the root layer, stays consistent with it.
    """
    if can_remove_environment_content(stage):
        return Usd.EditContext(stage, stage.GetEditTarget())
    return Usd.EditContext(stage, get_environment_edit_target_layer(stage))


def can_remove_environment_content(stage: Usd.Stage) -> bool:
    """Whether environment content can be removed rather than only hidden (OMPE-64890).

    Removing edits every local layer directly, so it takes a writable root layer. A live session
    does not help: its .live layer is writable, but what the root layer contributes can only be
    hidden from there. This is the rule delete_environment_prims() removes or hides by.
    """
    return stage.GetRootLayer().permissionToEdit


def delete_environment_prims(stage: Usd.Stage, paths: List[str]) -> None:
    """Remove environment prims, hiding them when they cannot be removed (OMPE-64890)."""
    if not paths:
        return

    if can_remove_environment_content(stage):
        omni.kit.commands.execute("DeletePrimsCommand", paths=paths)
        return

    layer = get_environment_edit_target_layer(stage)
    with Usd.EditContext(stage, layer):
        for path in paths:
            _hide_prim_in_layer(stage, layer, Sdf.Path(path))


def _hide_prim_in_layer(stage: Usd.Stage, layer: Sdf.Layer, path: Sdf.Path) -> None:
    prim = stage.GetPrimAtPath(path)
    if not prim:
        return

    # Deactivating alone is not enough: the new environment is authored at the same path right
    # after and activates the prim again, so hide the children and block the arcs too. The
    # properties are handled by block_replaced_environment_properties(), once the new environment
    # is authored and it is known which of them it provides again.
    for child in prim.GetAllChildren():
        # Blocking the arcs already removes the children they bring in, and hiding those would
        # outlive the removal: the arc of the new environment often provides the same paths.
        if _is_authored_in_layer_stack(stage, layer, child.GetPath()):
            _hide_prim_in_layer(stage, layer, child.GetPath())

    spec = Sdf.CreatePrimInLayer(layer, path)
    spec.referenceList.ClearEditsAndMakeExplicit()
    spec.payloadList.ClearEditsAndMakeExplicit()
    spec.active = False


def _is_authored_in_layer_stack(stage: Usd.Stage, exclude_layer: Sdf.Layer, path: Sdf.Path) -> bool:
    """Whether a layer of the stage holds the prim itself, rather than an arc bringing it in."""
    return any(layer.GetPrimAtPath(path) for layer in stage.GetLayerStack() if layer != exclude_layer)


def restore_environment_prim(stage: Usd.Stage, path: str) -> None:
    """Make a prim hidden by delete_environment_prims() visible again (OMPE-64890)."""
    prim = stage.GetPrimAtPath(path)
    if prim and not prim.IsActive():
        prim.SetActive(True)


def block_replaced_environment_properties(stage: Usd.Stage, path: str) -> None:
    """Block what the environment that could not be removed still contributes (OMPE-64890).

    Runs once the new environment is authored, so a property it or its arcs provide is left alone.
    A property every opinion of which comes from another layer of the stage is one the previous
    environment left behind. A property the previous environment authored in one of those layers
    and the new one only gets from an arc still resolves to the old value: a stronger layer can
    mask a weaker one, but not one weaker layer while keeping another.
    """
    if can_remove_environment_content(stage):
        return

    prim = stage.GetPrimAtPath(path)
    if not prim:
        return

    layer = get_environment_edit_target_layer(stage)
    replaced_layers = [candidate for candidate in stage.GetLayerStack() if candidate != layer]
    for prop in prim.GetProperties():
        specs = prop.GetPropertyStack(Usd.TimeCode.Default())
        if not specs or any(spec.layer not in replaced_layers for spec in specs):
            continue
        if isinstance(prop, Usd.Relationship):
            prop.SetTargets([])
        else:
            prop.Block()


async def get_subidentifier_from_mdl_async(mdl_file: str) -> List[str]:
    if not mdl_file:
        return []

    mdl_file = carb.tokens.get_tokens_interface().resolve(mdl_file)
    result, _, content = await omni.client.read_file_async(mdl_file)
    if result != omni.client.Result.OK:
        carb.log_error(f"get_subidentifier_from_material: Failed to read file {mdl_file}")
        return []

    re_material_in_mdl = re.compile(r"export\s+material\s+([^\s]+)\s*\(")
    mtl_list = []
    try:
        for line in memoryview(content).tobytes().decode("utf-8").splitlines():
            # get material names from MDL file
            for match in re.finditer(re_material_in_mdl, line):
                mtl_list.append(match.group(1))
    except UnicodeDecodeError:
        carb.log_error(f"Failed to parse {mdl_file}")

    return mtl_list
