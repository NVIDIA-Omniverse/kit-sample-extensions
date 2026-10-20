# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
import json
from typing import Any, List, Optional

import carb
import omni.usd
from pxr import Sdf, Usd


class AbstractWaypointSetting:
    """
    Abstract base class for Waypoint data, could be: Camera, Render, Sunstudy, etc.
    """

    def __init__(self, edit_context=None):
        self._data = {}
        self.__edit_context = edit_context
        self.valid = True
        self.prim: Optional[Usd.Prim] = None

    @property
    def edit_context(self) -> Usd.EditContext:
        # Override the edit context with either sidecar or WaypointExtension edit context if necessary
        if self.__edit_context:
            return self.__edit_context
        return Usd.EditContext(omni.usd.get_context().get_stage(), Usd.EditTarget(None))

    def __del__(self):
        self.destroy()

    def destroy(self):
        pass

    @property
    def info(self) -> Optional[List[List[str]]]:
        return None

    def get_name(self) -> str:  # pragma: no cover
        carb.log_warn("Call virtual function (get_name) in AbstractWaypointSetting")
        return "default"

    def is_valid(self) -> bool:
        return self.valid

    def is_dirty(self) -> bool:
        """Called to check if waypoint setting different from current scene"""
        if not self.valid:
            return False
        else:
            return False

    def create(self, valid: bool = True) -> None:
        """Called when creating a waypoint"""
        self.valid = valid

    def delete(self) -> None:
        """Called when deleting a waypoint"""
        pass

    def recall(self, prim: Usd.Prim) -> None:
        """Called to recall waypoint to current stage"""
        pass

    async def save_async(self, prim: Usd.Prim) -> None:
        """Called when saving waypoint to usd file"""
        self.prim = prim
        if hasattr(self, "save_to_usd_async"):
            await self.save_to_usd_async(prim)
        else:
            self.save_to_usd(prim)

    def save(self, prim: Usd.Prim) -> None:
        """Called when saving waypoint to usd file"""
        self.prim = prim
        self.save_to_usd(prim)

    def load(self, prim: Usd.Prim) -> bool:
        """Called to load waypoint from a prim"""
        self.prim = prim
        self.load_from_usd(prim)

    def update(self, prim: Usd.Prim) -> None:
        """Called when root prim changed (for example, rename waypoint)"""
        self.prim = prim

    def get_data(self):
        return self._data

    def subscribe_changes(self, enable) -> None:
        pass

    def _save_data_to_usd(self, prim: Usd.Prim, attr_name: str) -> None:
        self._save_attribute(prim, attr_name, json.dumps(self._data))

    def _load_data_from_usd(self, prim: Usd.Prim, attr_name: str) -> bool:
        attr = prim.GetAttribute(attr_name)
        if attr:
            self.valid = True
            json_str = prim.GetAttribute(attr_name).Get()
            if json_str is not None:
                self._data = json.loads(json_str)
                return True
            else:
                self._data = {}
                return False
        else:
            self.valid = False
            return False

    def _save_attribute(self, prim: Usd.Prim, name: str, value: Any, type_name=Sdf.ValueTypeNames.String, create=True):
        if prim.HasAttribute(name):
            attribute = prim.GetAttribute(name)
        elif create:
            attribute = prim.CreateAttribute(name, type_name)
        else:
            return
        attribute.Set(value)

    @staticmethod
    def equal_data(d1, d2) -> bool:
        tp = type(d1)
        if tp != type(d2):
            return False
        if tp.__name__ == "tuple" or tp.__name__ == "list":
            length = len(d1)
            if length != len(d2):
                return False
            for i in range(length):
                if d1[i] != d2[i]:
                    return False

            return True

        return d1 == d2
