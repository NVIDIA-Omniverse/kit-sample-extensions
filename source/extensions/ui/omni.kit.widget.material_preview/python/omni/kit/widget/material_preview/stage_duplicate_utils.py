# Copyright (c) 2021, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#
__all__ = ["copy_meta", "copy_property", "copy_prim"]

from pathlib import Path
from typing import List, Optional

from omni.usd.commands import UsdStageHelper
from pxr import Sdf, Usd

CURRENT_PATH = Path(__file__).parent
DATA_PATH = CURRENT_PATH.parent.parent.parent.parent.joinpath("data")


def copy_meta(object: Usd.Object, object_to: Usd.Object):
    meta = object.GetAllAuthoredMetadata()
    for meta_key, value in meta.items():
        target_value = object_to.GetMetadata(meta_key)
        if value != target_value:
            object_to.SetMetadata(meta_key, value)


def copy_property(property: Usd.Object, stage_to: Usd.Stage, context_name: str):
    """Copies property to the given stage"""
    path = Sdf.Path("/" + context_name + str(property.GetPath()))
    if isinstance(property, Usd.Attribute):
        target = stage_to.GetObjectAtPath(path)
        attribute_type = property.GetTypeName()
        if not target:
            # Get/create parent prim
            parent_path = path.GetParentPath()
            parent = stage_to.GetPrimAtPath(parent_path)
            if not parent:
                parent = stage_to.OverridePrim(parent_path)

            target = parent.CreateAttribute(path.name, attribute_type)

        # Copy default value
        default_value = property.Get()

        # Use the resolved absolute path, because relative path
        # or manual contructed local path might not be the path we want
        # since the path could be from the server
        # We need it to let preview stage use the hdr texture.
        if attribute_type == Sdf.ValueTypeNames.Asset and default_value:
            # Use full path because the preview is from anonymous layer
            default_value = Sdf.AssetPath(default_value.resolvedPath)

        if default_value is None:
            # TODO: delete
            pass
        elif default_value != target.Get():
            target.Set(default_value)

        # TODO: Copy animation

        # Copy connections
        connections = property.GetConnections()
        if connections is not None and connections != target.GetConnections():
            connections = [Sdf.Path("/" + context_name + str(c)) for c in connections]
            target.SetConnections(connections)

    elif isinstance(property, Usd.Relationship):
        connections = property.GetTargets()
        if not connections:
            # TODO: Delete
            return

        target = stage_to.GetObjectAtPath(path)
        if not target:

            # Get/create parent prim
            parent_path = path.GetParentPath()
            parent = stage_to.GetPrimAtPath(parent_path)
            if not parent:
                parent = stage_to.OverridePrim(parent_path)

            target = parent.CreateRelationship(path.name, property.IsCustom())

        target.SetTargets(connections)

    copy_meta(property, target)


# add context_name of stage_to as the workaround for OM-33643. Create an extra
# root layer for the target stage, so that when we change the same attribute
# on different stages, hydra knows that when we are tweaking different prims
def copy_prim(prim: Usd.Prim, stage_to: Usd.Stage, context_name: str):
    """Copies prim and its children to the given stage"""
    if not prim or not prim.IsActive():
        # TODO: Delete
        return

    path = prim.GetPath()
    if path == Sdf.Path.absoluteRootPath:
        target = stage_to.GetPseudoRoot()
    else:
        path = Sdf.Path("/" + context_name + str(path))
        target = stage_to.GetPrimAtPath(path)

    if not target:
        specifier = prim.GetSpecifier()
        if specifier == Sdf.SpecifierOver:
            target = stage_to.OverridePrim(path)
        else:
            target = stage_to.DefinePrim(path, prim.GetTypeName())

    copy_meta(prim, target)

    for prop in prim.GetProperties():
        copy_property(prop, stage_to, context_name)

    for child in prim.GetChildren():
        copy_prim(child, stage_to, context_name)
