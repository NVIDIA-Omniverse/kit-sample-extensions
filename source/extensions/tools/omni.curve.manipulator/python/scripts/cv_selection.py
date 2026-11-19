# Copyright (c) 2021, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

from __future__ import annotations

import weakref
from enum import Enum, auto
from typing import Callable, Dict, List, Set, Tuple

import carb.profiler
from pxr import UsdGeom


class Subscription:
    def __init__(self, unsubscribe_fn: Callable):
        self._unsubscribe_fn = unsubscribe_fn

    def __del__(self):
        self.unsubscribe()

    def unsubscribe(self):
        if self._unsubscribe_fn:
            self._unsubscribe_fn()
            self._unsubscribe_fn = None


class SelectMode(Enum):
    RESET_AND_SELECT = auto()
    MERGE_SELECTION = auto()
    INVERT_SELECTION = auto()
    CONTEXT_MENU = auto()


class CvSelection:
    def __init__(self):
        super().__init__()
        self._enabled = True
        self._selection_changed_fn: Dict[int, Callable] = {}
        self._selection_changed_fn_id: int = 0
        self._selected_cvs: Set[Tuple[UsdGeom.BasisCurves, int]] = set()  # ordered
        self._valid = True

    def destroy(self):
        if self._valid:
            self.clear_all_selection()
            self._valid = False

    def __del__(self):
        self.destroy()

    def clear_all_selection(self):
        if len(self._selected_cvs) > 0:
            self._selected_cvs.clear()
            self._notify_selection_change()

    def clear_selection(self, basis_curves: UsdGeom.BasisCurves):
        if not self._enabled:
            self.clear_all_selection()
            return

        prev_len = len(self._selected_cvs)
        self._selected_cvs = {(curves, id) for (curves, id) in self._selected_cvs if curves != basis_curves}
        if prev_len != len(self._selected_cvs):
            self._notify_selection_change()

    def add_to_selection(self, basis_curves: UsdGeom.BasisCurves, id: int, clear_previous: bool):
        if not self._enabled:
            self.clear_all_selection()
            return

        if clear_previous:
            self._selected_cvs.clear()

        self._selected_cvs.add((basis_curves, id))
        self._notify_selection_change()

    def remove_from_selection(self, basis_curves: UsdGeom.BasisCurves, id: int):
        if not self._enabled:
            self.clear_all_selection()
            return 0

        self._selected_cvs.discard((basis_curves, id))
        self._notify_selection_change()

        return len(self._selected_cvs)

    def set_enabled(self, value: bool):
        self._enabled = value
        if not self._enabled:
            self.clear_all_selection()

    def set_selected_cvs(self, selected_cvs: Set[Tuple[UsdGeom.BasisCurves, int]]):
        if not self._enabled:
            self.clear_all_selection()
            return

        if self._selected_cvs != selected_cvs:
            self._selected_cvs = selected_cvs
            self._notify_selection_change()

    def get_selected_cvs(self) -> Set[Tuple[UsdGeom.BasisCurves, int]]:
        return self._selected_cvs

    def get_selected_ids(self, basis_curves: UsdGeom.BasisCurves) -> Set[int]:
        # compare path, not basis_curves itself, different object can point to same prim
        return set([entry[1] for entry in self._selected_cvs if entry[0].GetPath() == basis_curves.GetPath()])

    def subscribe_to_selection_changed(self, on_selection_changed_fn):
        id = self.add_selection_changed_fn(on_selection_changed_fn)
        return Subscription(
            lambda selection=weakref.ref(self), id=id: (
                selection().remove_selection_changed_fn(id) if selection() else None
            )
        )

    def add_selection_changed_fn(self, on_selection_changed_fn):
        self._selection_changed_fn_id += 1
        self._selection_changed_fn[self._selection_changed_fn_id] = on_selection_changed_fn
        return self._selection_changed_fn_id

    def remove_selection_changed_fn(self, id: int):
        self._selection_changed_fn.pop(id)

    @carb.profiler.profile
    def _notify_selection_change(self):
        for fn in self._selection_changed_fn.values():
            fn(self._selected_cvs)
