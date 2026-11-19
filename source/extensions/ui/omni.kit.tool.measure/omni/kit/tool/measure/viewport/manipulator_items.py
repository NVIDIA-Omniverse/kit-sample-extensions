# Copyright (c) 2022, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

from typing import Callable, List, Optional

import omni.usd as ou
from omni.ui import scene as sc
from pxr import Gf, Usd, UsdGeom


## Manipulator Items
class PositionItem(sc.AbstractManipulatorItem):
    def __init__(self, value: List[float] = [0.0, 0.0, 0.0], changed_fn: Optional[Callable[[], None]] = None):
        super().__init__()
        self._value: List[float] = value
        self._change_fn = changed_fn

    @property
    def vector(self) -> Gf.Vec3d:
        return Gf.Vec3d(self._value)

    @vector.setter
    def vector(self, value: Gf.Vec3d):
        self._value = [*value]

    @property
    def value(self) -> List[float]:
        return self._value

    @value.setter
    def value(self, value: List[float]) -> None:
        self._value = value
        self._on_value_changed()

    def _on_value_changed(self):
        if not self._change_fn:
            return
        self._change_fn()

    def add_value_changed_fn(self, function: Callable[[], None]):
        self._change_fn = function


class MultiPositionItem(sc.AbstractManipulatorItem):
    def __init__(self, value: List[List[float]] = [], changed_fn: Optional[Callable[[], None]] = None):
        super().__init__()
        self._value: List[List[float]] = value
        self._change_fn = changed_fn

    @property
    def length(self) -> int:
        return len(self._value)

    @property
    def vectors(self) -> List[Gf.Vec3d]:
        return [Gf.Vec3d(*v) for v in self._value]

    @property
    def value(self) -> List[List[float]]:
        return self._value

    def reset(self) -> None:
        """
        Reset item back to default.
        """
        self._value = []

    def append(self, value: List[float]) -> None:
        """
        Add entry to Item
        """
        self._value.append(value)
        self._on_value_changed()

    def update(self, value: List[float], index: int) -> None:
        """
        Update a value of an item.

        Args:
            value (List[float]): value to set
            index (int): Index of the item to update
        """
        self._value[index] = value
        self._on_value_changed()

    def remove(self, index: int) -> None:
        """
        Remove entry from Item

        Args:
            index (int): Index of the item to remove
        """
        try:
            self._value.pop(index)
            self._on_value_changed()
        except IndexError:
            return

    def _on_value_changed(self) -> None:
        if not self._change_fn:
            return
        self._change_fn()

    def add_value_changed_fn(self, function: Callable[[], None]):
        self._change_fn = function


class PrimRefItem(sc.AbstractManipulatorItem):
    def __init__(self, value: Optional[str] = None):
        super().__init__()
        self._path: Optional[str] = value
        self._prim: Optional[Usd.Prim] = self.update(self._path) if value else None

    @property
    def path(self):
        return self._path

    @property
    def prim(self) -> Optional[Usd.Prim]:
        return self._prim

    @property
    def local_xform(self) -> Optional[Gf.Matrix4d]:
        if not self.prim:
            return None
        xform = UsdGeom.Xformable(self._prim)
        return xform.GetLocalTransformation()

    @property
    def world_xform(self) -> Optional[Gf.Matrix4d]:
        if not self.prim:
            return None
        xform = UsdGeom.Xformable(self._prim)
        return xform.ComputeLocalToWorldTransform(Usd.TimeCode.Default())

    def reset(self) -> None:
        """
        Reset Item to default.
        """
        self._path = None
        self._prim = None

    def update(self, prim_path: str) -> None:
        """
        Update Item value.

        Args:
            prim_path (str): string path to Prim
        """
        from ..common import find_valid_ancestor

        if prim_path is None:
            return
        self._path = prim_path
        self._prim = find_valid_ancestor(prim_path, attribute="xformOpOrder")
