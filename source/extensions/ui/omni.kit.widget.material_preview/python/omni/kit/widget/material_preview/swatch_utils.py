# Copyright (c) 2021, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#
__all__ = ["get_swatch_layer", "get_default_camera"]

from pathlib import Path
from typing import Optional

from pxr import Sdf, Usd

CURRENT_PATH = Path(__file__).parent
SWATCH = CURRENT_PATH.parent.parent.parent.parent.joinpath("data/swatch.usda")


def get_swatch_layer(material_path: Sdf.Path, swatch_layer_path: Optional[str] = None) -> Sdf.Layer:
    """Form the layer to send for swatch rendering"""
    # TODO: This is better but it crashes Kit:
    # layer = Sdf.Layer.CreateAnonymous("swatch_for_preview.usda")
    # layer.subLayerPaths.append(f"{SWATCH}")
    # As workaround we send the full scene
    layer = Sdf.Layer.FindOrOpen(swatch_layer_path or f"{SWATCH}")
    stage = Usd.Stage.Open(layer)
    # Get default prim
    if layer.HasDefaultPrim():
        default_prim_name = layer.defaultPrim
    else:
        children = stage.GetRootLayer().pseudoRoot.nameChildren
        if not children:
            # There are no prims
            return layer
        default_prim_name = children[0]
    default_prim_path = Sdf.Path.absoluteRootPath.AppendChild(default_prim_name)

    # Bind material to the default prim
    stage.SetEditTarget(layer)
    swatch = stage.GetPrimAtPath(default_prim_path)
    rel = swatch.CreateRelationship("material:binding", False)
    rel.SetTargets([material_path])
    rel.SetMetadata("bindMaterialAs", "weakerThanDescendants")

    # Pre-create parents of material
    for parent in material_path.GetParentPath().GetPrefixes():
        stage.DefinePrim(parent, "Scope")

    return layer


def get_default_camera(layer: Sdf.Layer) -> Optional[Sdf.Path]:
    """Returns the name of the default camera of the layer"""
    if layer and layer.HasCustomLayerData():
        data = layer.customLayerData or {}
        camera_settings = data.get("cameraSettings", {})
        bound_camera = camera_settings.get("boundCamera", None)
        if bound_camera:
            return Sdf.Path(bound_camera)
