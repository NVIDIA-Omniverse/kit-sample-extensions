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


class MarkupUsd:
    def __init__(self, *, sidecar_data=None):
        self._layer = None
        self.__sidecar_data = sidecar_data
        self.update_stage(omni.usd.get_context().get_stage())

    @property
    def edit_context(self) -> Usd.EditContext:
        return (
            self.__sidecar_data.edit_context
            if self.__sidecar_data
            else Usd.EditContext(omni.usd.get_context().get_stage(), Usd.EditTarget(None))
        )

    def update_stage(self, stage):
        self._stage = stage
        if not self._stage:
            return
        self._layer = stage.GetRootLayer()
        carb.log_info(f"Using {self._layer.identifier}")

    def get_prim(self, path, create=True, type_name=None):
        if not self._stage:
            return
        if path:
            prim = self._stage.GetPrimAtPath(path)
        else:
            prim = None
        if not prim and create:
            if type_name:
                prim = self._stage.DefinePrim(path, type_name)
            else:
                from .commands import create_data_only_prim

                prim = create_data_only_prim(self._stage, path)
            if not prim:  # pragma: no cover
                carb.log_error(f"Failed to create prim at '{path}'! {self._layer.identifier} may be READ ONLY!")
                return
        return prim

    def remove_prim(self, path):
        self._stage.RemovePrim(path)

    def get_prim_attribute(self, prim, name, default):
        if prim.HasAttribute(name):
            attribute = prim.GetAttribute(name)
            value = attribute.Get()
            if value is None:  # pragma: no cover
                return default
            else:
                return value
        else:
            return default

    def move_prim(self, path_from, path_to):
        from .commands import create_data_only_prim

        create_data_only_prim(self._stage, path_to)
        Sdf.CopySpec(self._layer, path_from, self._layer, path_to)
        self._stage.RemovePrim(path_from)
