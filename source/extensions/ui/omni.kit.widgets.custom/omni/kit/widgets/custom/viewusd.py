# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
import carb
import omni.usd
from pxr import Sdf, Usd, UsdGeom

VIEW_TOOL_LAYER = ".view.usd"


class ViewUsd:
    def __init__(self):
        self._layer = None
        self.update_stage(omni.usd.get_context().get_stage())

    @property
    def edit_context(self) -> Usd.EditContext:
        return Usd.EditContext(self._stage, Usd.EditTarget(self._layer))

    def update_stage(self, stage):
        self._stage = stage
        if not self._stage:
            return
        self._layer = stage.GetRootLayer()
        layer_stack = stage.GetLayerStack()
        for layer in layer_stack:
            if layer.identifier.endswith(VIEW_TOOL_LAYER):
                self._layer = layer
                break
        carb.log_info(f"Using {self._layer.identifier}")

    def get_prim(self, path, create=True, type_name=None):
        if not self._stage:
            return
        self._set_edit_target()
        if path:
            prim = self._stage.GetPrimAtPath(path)
        else:
            prim = None
        if not prim and create:
            if type_name:
                prim = self._stage.DefinePrim(path, type_name)
            else:
                prim = self._stage.DefinePrim(path)
            if not prim:
                carb.log_error("Faile to create prim at '{path}'! {self._layer.identifier} may be READONLY!")
                return None
        return prim

    def remove_prim(self, path):
        self._stage.RemovePrim(path)

    def set_prim_attribute(self, prim, name, value, type_name=Sdf.ValueTypeNames.String, create=True):
        if prim.HasAttribute(name):
            attribute = prim.GetAttribute(name)
        elif create:
            attribute = prim.CreateAttribute(name, type_name)
        else:
            return
        attribute.Set(value)

    def get_prim_attribute(self, prim, name, default):
        if prim.HasAttribute(name):
            attribute = prim.GetAttribute(name)
            value = attribute.Get()
            if value is None:
                return default
            else:
                return value
        else:
            return default

    def _set_edit_target(self):
        edit_target = Usd.EditTarget(self._layer)
        self._stage.SetEditTarget(edit_target)

    def move_prim(self, path_from, path_to):
        self._set_edit_target()
        self._stage.DefinePrim(path_to)
        Sdf.CopySpec(self._layer, path_from, self._layer, path_to)
        self._stage.RemovePrim(path_from)
