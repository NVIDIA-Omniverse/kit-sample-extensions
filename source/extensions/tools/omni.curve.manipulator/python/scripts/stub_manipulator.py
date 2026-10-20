# Copyright (c) 2023, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

from typing import List, Union

from omni.kit.manipulator.selector import ManipulatorBase
from pxr import Sdf, Usd

from ..bindings import get_interface
from .bezier_curve_edits_context import BezierCurveEditsContextManager


class CvStubManipulator(ManipulatorBase):
    """
    This manipulator is used to override and hide other manipulators when in curve editing mode
    It self is an empty manipulator that does nothing.

    The real curve manipulator will be instantiated differently."""

    def __init__(self, usd_context_name: str = "", viewport_api=None):
        super().__init__(name="omni.curve.manipulator.stub", usd_context_name=usd_context_name)
        self._curve_manip = get_interface()
        self._curve_context = BezierCurveEditsContextManager.get_context(usd_context_name).curve_edits.curve_context
        self._enabled = False

    def on_selection_changed(self, stage: Usd.Stage, selection: Union[List[Sdf.Path], None], *args, **kwargs) -> bool:
        return self._curve_manip.is_in_curve_editing_mode(self._curve_context)

    @property
    def enabled(self) -> bool:
        return self._enabled

    @enabled.setter
    def enabled(self, value: bool):
        self._enabled = value
