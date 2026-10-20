# Copyright (c) 2021, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

from __future__ import annotations

from typing import List, Set, Tuple
from weakref import ProxyType

import carb
import omni.kit.commands
import omni.kit.undo
import omni.usd
from pxr import Sdf, Usd, UsdGeom

from ..bindings import CurveEditingModeType, CurveManipulatorContext, get_interface
from .bezier_curve_edits_context import BezierCurveEditsContextManager
from .cv_selection import CvSelection


class EnableCurveEditing(omni.kit.commands.Command):
    def __init__(
        self,
        paths: List[str],
        mode: CurveEditingModeType,
        curve_context: CurveManipulatorContext,
        usd_context_name: str = "",
    ):
        self._curve_manip = get_interface()
        self._curve_context = curve_context
        self._mode = mode
        self._usd_context = omni.usd.get_context(usd_context_name)
        self._paths = paths.copy()

    def do(self):
        # these changes will be automatically included in undo.
        for path in self._paths:
            attr_path = Sdf.Path(path).AppendProperty("omni:scene:visualization:drawWireframe")
            omni.kit.commands.execute(
                "ChangeProperty",
                prop_path=attr_path,
                value=True,
                prev=None,
                usd_context_name=self._usd_context,
                type_to_create_if_not_exist=Sdf.ValueTypeNames.Bool,
            )

        self._old_selected_path = self._usd_context.get_selection().get_selected_prim_paths()

        self._curve_manip.enable_curve_editing_mode(self._curve_context, self._paths, self._mode)

    def undo(self):
        omni.kit.commands.execute(
            "SelectPrims",
            old_selected_paths=[],
            new_selected_paths=self._old_selected_path,
            expand_in_stage=False,
        )

        self._curve_manip.disable_curve_editing_mode(self._curve_context)


class DisableCurveEditing(omni.kit.commands.Command):
    def __init__(self, curve_context: CurveManipulatorContext, usd_context_name: str = ""):
        cv_selection = BezierCurveEditsContextManager.get_context(usd_context_name).selection
        self._curve_manip = get_interface()
        self._curve_context = curve_context
        self._usd_context = omni.usd.get_context(usd_context_name)
        self._usd_context_name = usd_context_name
        self._paths = self._curve_manip.get_editing_curve_paths(self._curve_context)
        self._mode = self._curve_manip.get_curve_editing_mode(self._curve_context)
        self._selected_cvs = self._copy_cvs(cv_selection.get_selected_cvs())

    def _copy_cvs(self, cvs):
        new_cvs = set()
        for basis_curves, index in cvs:
            new_cvs.add((basis_curves, index))
        return new_cvs

    def do(self):
        cv_selection = BezierCurveEditsContextManager.get_context(self._usd_context_name).selection
        cv_selection.clear_all_selection()
        self._curve_manip.disable_curve_editing_mode(self._curve_context)

    def undo(self):
        cv_selection = BezierCurveEditsContextManager.get_context(self._usd_context_name).selection
        selected_cvs = self._copy_cvs(self._selected_cvs)
        self._curve_manip.enable_curve_editing_mode(self._curve_context, self._paths, self._mode)
        cv_selection.set_selected_cvs(self._selected_cvs)
        self._selected_cvs = selected_cvs


class SetCurveEditingMode(omni.kit.commands.Command):
    def __init__(self, mode: CurveEditingModeType, curve_context: CurveManipulatorContext):
        self._curve_manip = get_interface()
        self._curve_context = curve_context
        self._mode = mode
        self._previous_mode = self._curve_manip.get_curve_editing_mode(self._curve_context)

    def do(self):
        self._curve_manip.set_curve_editing_mode(self._curve_context, self._mode)

    def undo(self):
        self._curve_manip.set_curve_editing_mode(self._curve_context, self._previous_mode)


class CvSelectionBase(omni.kit.commands.Command):
    def __init__(self, selection: ProxyType[CvSelection], basis_curves: UsdGeom.BasisCurves, id: int):
        self._selection = selection
        self._basis_curves = basis_curves
        self._id = id

    def do(self):
        if self._selection:
            self._prev_selection = self._selection.get_selected_cvs().copy()
            self._do_impl()

    def undo(self):
        if self._selection:
            self._selection.set_selected_cvs(self._prev_selection)

    def _do_impl(self): ...


class AddCvSelection(CvSelectionBase):
    def __init__(
        self, selection: ProxyType[CvSelection], basis_curves: UsdGeom.BasisCurves, id: int, clear_previous: bool
    ):
        super().__init__(selection, basis_curves, id)
        self._clear_previous = clear_previous

    def _do_impl(self):
        self._selection.add_to_selection(self._basis_curves, self._id, self._clear_previous)


class RemoveCvSelection(CvSelectionBase):
    def __init__(self, selection: ProxyType[CvSelection], basis_curves: UsdGeom.BasisCurves, id: int):
        super().__init__(selection, basis_curves, id)

    def _do_impl(self):
        self._selection.remove_from_selection(self._basis_curves, self._id)


class ClearCvSelection(CvSelectionBase):
    def __init__(self, selection: ProxyType[CvSelection], basis_curves: UsdGeom.BasisCurves = None):
        super().__init__(selection, basis_curves=basis_curves, id=None)

    def _do_impl(self):
        if self._basis_curves is not None:
            self._selection.clear_selection(self._basis_curves)
        else:
            self._selection.clear_all_selection()


class SetCvSelection(CvSelectionBase):
    def __init__(self, selection: CvSelection, selected_cvs: Set[Tuple[UsdGeom.BasisCurves, int]]):
        super().__init__(selection, basis_curves=None, id=None)
        self._selected_cvs = selected_cvs

    def _do_impl(self):
        self._selection.set_selected_cvs(self._selected_cvs)


class SetPrimvarInterpolationCommand(omni.kit.commands.Command):
    """Sets the primvar interpolation for a given primvar
    Args:
        primvar_path: The primvar path in the stage on which to set the interpolation
        interpolation: The interpolation to set
        usd_context_name: The name of the usd context for this command
    """

    def __init__(self, primvar_path: Sdf.Path, interpolation: Usd.Tokens, usd_context_name: str = ""):
        stage = omni.usd.get_context(usd_context_name).get_stage()
        self._interpolation = interpolation
        self._previous_interpolation = UsdGeom.Primvar(stage.GetAttributeAtPath(primvar_path)).GetInterpolation()
        self._primvar_path = primvar_path
        self._usd_context_name = usd_context_name

    def do(self):
        stage = omni.usd.get_context(self._usd_context_name).get_stage()
        UsdGeom.Primvar(stage.GetAttributeAtPath(self._primvar_path)).SetInterpolation(self._interpolation)

    def undo(self):
        stage = omni.usd.get_context(self._usd_context_name).get_stage()
        UsdGeom.Primvar(stage.GetAttributeAtPath(self._primvar_path)).SetInterpolation(self._previous_interpolation)


omni.kit.commands.register_all_commands_in_module(__name__)
