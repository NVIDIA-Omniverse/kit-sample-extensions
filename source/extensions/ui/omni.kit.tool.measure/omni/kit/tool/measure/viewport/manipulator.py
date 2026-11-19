# Copyright (c) 2022-2023, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

from typing import Dict, Optional

import carb.profiler
import omni.usd as ou
from carb import log_error
from carb.input import KeyboardInput
from omni.ui import scene as sc

from ..common import MeasureCreationState, MeasureMode, MeasureState
from ..manager import ReferenceManager, StateMachine
from ._model import ViewportMeasurementModel
from .manipulator_items import *
from .tools import (  # VolumeModel
    AngleModel,
    AreaModel,
    DiameterModel,
    MultiPointModel,
    PointToPointModel,
    ViewportModeModel,
)


class MeasureDrawManipulator(sc.Manipulator):

    def __init__(self, model: ViewportMeasurementModel):
        super().__init__()
        self.__root = sc.Transform()
        # Transient (in-memory) visibility of all completed measurement drawings.
        # This is independent of the persistent Display-menu visibility preference
        # and the per-measurement USD payloads; it gates the whole draw root at the
        # scene-graph level so nothing is mutated or serialized when toggled.
        self.__measurements_visible: bool = True
        self._model: ViewportMeasurementModel = model
        self._usd_context = ou.get_context()

        self._sub_item_changed = self._model.subscribe_item_changed_fn(self.__on_item_changed)

        self._stage_closed_sub: int = StateMachine().subscribe_to_stage_event(self.clear, ou.StageEventType.CLOSED)

        # Assign the draw manipulator to the Reference Manager
        ReferenceManager().measure_scene = self

    @carb.profiler.profile
    def __draw(self, item):
        with self.__root:
            item.draw()

    def __on_item_changed(self, model, item):
        self.__draw(item)

    def on_build(self):
        if not self._model:
            log_error("Model was not found for MeasureDrawManipulator")
            return

    @property
    def measurements_visible(self) -> bool:
        return self.__measurements_visible

    @measurements_visible.setter
    def measurements_visible(self, visible: bool) -> None:
        """Transiently show/hide every completed measurement drawing.

        Hides/shows non-destructively by toggling the draw root's visibility;
        the persistent visibility setting and per-item payloads are untouched.
        """
        self.__measurements_visible = visible
        self.__root.visible = visible

    def clear(self):
        """
        Removes the container items from the model's container of Measurements.
        """
        if not self._model:
            return
        self.__root.clear()
        self._model.clear()


class MeasureCreateManipulator(sc.Manipulator):
    """
    The ViewportManipulator handles all operations for creating and editing of a Measurement
    """

    def __init__(self, api):
        super().__init__()
        # self._model = model

        self._ctx = ou.get_context()

        # Create/Edit mode sub models for each mode to handle drawing/editing
        self._tools: Dict[MeasureMode, ViewportModeModel] = {
            MeasureMode.POINT_TO_POINT: PointToPointModel(api),
            MeasureMode.MULTI_POINT: MultiPointModel(api),
            MeasureMode.ANGLE: AngleModel(api),
            MeasureMode.AREA: AreaModel(api),
            MeasureMode.DIAMETER: DiameterModel(api),
            # MeasureMode.VOLUME: VolumeModel(api)
        }

        self._current_tool: Optional[ViewportModeModel] = None

        # Assign state machine callbacks
        self._state_changed_sub = StateMachine().add_tool_state_changed_fn(self._on_state_changed)
        self._create_mode_sub = StateMachine().add_on_create_mode_fn(self._on_create)
        self._edit_mode_sub = StateMachine().add_on_edit_mode_fn(self._on_edit)
        self._key_pressed_sub = StateMachine().subscribe_to_key_pressed_event(self._on_key_pressed)

    def __reset_tools(self) -> None:
        for tool in self._tools.values():
            tool.reset()

    def _get_tool(self, mode: MeasureMode) -> Optional[ViewportModeModel]:
        return self._tools.get(mode, None)

    def _on_state_changed(self, state: MeasureState, mode: MeasureMode) -> None:
        if state == MeasureState.NONE and mode == MeasureMode.NONE:
            self.__reset_tools()

    def _on_create(self, mode: MeasureMode):
        """
        Get the model and tell it to start its create mode. If the model is None, Return. Do nothing.
        If a model is actively in create/edit mode, reset its state before starting the new creation mode.
        """
        self._current_tool: Optional[ViewportModeModel] = self._get_tool(mode)
        if not self._current_tool:
            return

        # Reset tools that aren't the current tool
        for tool in self._tools.values():
            if tool.state != MeasureState.NONE and tool is not self._current_tool:
                tool.reset()

        # Set the current tool to its create mode IF its not currently in create already.
        if self._current_tool.state != MeasureState.CREATE:
            self._current_tool.state = MeasureState.CREATE

    def _on_edit(self, mode: MeasureMode):
        """
        Get the model and tell it to start its Edit mode. If the model is None, Return. Do Nothing.
        If a model is actively in create/edit mode, reset its state before starting the new Edit mode.
        """
        # TODO
        pass

    def _on_key_pressed(self, key: KeyboardInput) -> None:
        if self._current_tool is None or key != KeyboardInput.ESCAPE:
            return

        if self._current_tool.creation_state == MeasureCreationState.START_SELECTION:
            StateMachine().reset_state_to_default(is_current_tool=False)
        else:
            self._current_tool.reset()
