# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
import base64
import zlib
from typing import List, Optional

import carb
import omni.stageupdate
import omni.usd
from pxr import Sdf, Tf, Trace, Usd, UsdGeom

from ..common import WAYPOINT_ROOT_PRIM_PATH
from .abstract_setting import AbstractWaypointSetting

WAYPOINT_ATTR_PRIM_VISIBILITY = "visibility:prims"

# NOTE: PrimVisibilitySetting has some explicit tests, but we are removing it from coverage metrics as it is currently always off.


class PrimVisibilitySetting(AbstractWaypointSetting):  # pragma: no cover
    def __init__(self, edit_context: Usd.EditContext = None):
        super().__init__(edit_context)
        self._visible_prims: List[str] = []

        self._stage: Optional[Usd.Stage] = None
        self._listener = None
        self.__is_dirty = False

    def destroy(self):
        self._stage_subscription = None

    def get_name(self):
        return "Prim Visibility"

    def is_dirty(self) -> bool:
        if not self.valid:
            return False

        return self.__is_dirty

    def create(self, valid: bool = True) -> None:
        super().create(valid)
        if valid:
            self._visible_prims = self._get_visible_prims()

    def recall(self, prim: Usd.Prim) -> None:
        if not self.valid:
            return

        def __recall_prim_visibility(prim: Usd.Prim):
            imageable = UsdGeom.Imageable(prim)
            if imageable:
                path = prim.GetPath().pathString
                if path.startswith(WAYPOINT_ROOT_PRIM_PATH):
                    return
                if path in self._visible_prims:
                    # set visible
                    if imageable.ComputeVisibility() == UsdGeom.Tokens.invisible:
                        imageable.MakeVisible()
                else:
                    # set to visible
                    if imageable.ComputeVisibility() != UsdGeom.Tokens.invisible:
                        imageable.MakeInvisible()

        self._traverse_all_prims(__recall_prim_visibility)

    def save_to_usd(self, prim: Usd.Prim) -> None:
        if prim.HasAttribute(WAYPOINT_ATTR_PRIM_VISIBILITY):
            attr = prim.GetAttribute(WAYPOINT_ATTR_PRIM_VISIBILITY)
        else:
            attr = prim.CreateAttribute(WAYPOINT_ATTR_PRIM_VISIBILITY, Sdf.ValueTypeNames.String)
        data = ",".join(self._visible_prims).encode("utf-8")
        packed = zlib.compress(bytes(data))
        attr.Set(base64.a85encode(packed))

    def load_from_usd(self, prim: Usd.Prim) -> bool:
        attr = prim.GetAttribute(WAYPOINT_ATTR_PRIM_VISIBILITY)
        if not attr:
            self._visible_prims = []
            self.valid = False
            return False
        packed = base64.a85decode(attr.Get())
        data = zlib.decompress(packed).decode("utf-8")
        self._visible_prims = data.split(",")

        return True

    def subscribe_changes(self, enable) -> None:
        if not self.valid:
            return

        if enable:
            # Start tracing in stage.
            self.__is_dirty = False
            stage = omni.usd.get_context().get_stage()
            if not stage:
                return

            self._stage_subscription = omni.stageupdate.get_stage_update_interface().create_stage_update_node(
                "WaypointPrimVisibility",
                None,
                None,
                None,
                self.__on_prim_created,
                self.__on_prim_changed,
                self.__on_prim_removed,
            )
        else:
            self._stage_subscription = None

    def __on_prim_created(self, path) -> None:
        if not path.startswith(WAYPOINT_ROOT_PRIM_PATH):
            self.__is_dirty = True

    def __on_prim_removed(self, path) -> None:
        if not path.startswith(WAYPOINT_ROOT_PRIM_PATH):
            if path in self._visible_prims:
                self.__is_dirty = True

    def __on_prim_changed(self, path) -> None:
        if not path.startswith(WAYPOINT_ROOT_PRIM_PATH):
            stage = omni.usd.get_context().get_stage()
            if stage:
                prim = stage.GetPrimAtPath(path)
                if self._is_prim_hidden(prim):
                    if path in self._visible_prims:
                        self.__is_dirty = True
                else:
                    if path not in self._visible_prims:
                        self.__is_dirty = True

    def _get_visible_prims(self) -> List[str]:
        prims: List[str] = []

        # Enum all prims and check visibility
        def __find_visible_prim(prim: Usd.Prim):
            if not self._is_prim_hidden(prim):
                path = prim.GetPath().pathString
                if not path.startswith(WAYPOINT_ROOT_PRIM_PATH):
                    prims.append(path)

        self._traverse_all_prims(__find_visible_prim)

        carb.log_info(f"[Waypoint] {len(prims)} visible prims")

        return prims

    def _is_prim_hidden(self, prim: Usd.Prim) -> bool:
        imageable = UsdGeom.Imageable(prim)
        if imageable:
            return imageable.ComputeVisibility() == UsdGeom.Tokens.invisible
        else:
            return False

    def _traverse_all_prims(self, callback: callable) -> None:
        # Caution: OMFP-3172 visibility handling is extremely slow
        # TODO: Consider USDRT instead https://docs.omniverse.nvidia.com/kit/docs/usdrt/latest/docs/usdrt_query.html
        stage = omni.usd.get_context().get_stage()
        if stage:
            for child_prim in stage.TraverseAll():
                callback(child_prim)
