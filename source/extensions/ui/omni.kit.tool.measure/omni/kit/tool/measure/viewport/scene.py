# Copyright (c) 2022, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

from typing import List, Optional

import omni.ui as ui
from omni.ui import Workspace as ui_workspace
from omni.ui import scene as sc

from ..common import EXTENSION_NAME, MeasureMode, MeasureState
from ..manager import ReferenceManager, StateMachine
from ..system import MeasurePrim
from ._measurement_items import _MeasurementItem
from ._model import ViewportMeasurementModel
from .manipulator import MeasureCreateManipulator, MeasureDrawManipulator
from .scene_overlay import MeasureSceneOverlay


class MeasureScene:
    """
    The window with the manipulators - Carb Input
    """

    def __init__(self, window, ext_id):
        self._viewport_window = window

        self.__measurement_model = ViewportMeasurementModel()

        self._manipulator: Optional[MeasureDrawManipulator] = None
        self._create_manipulator: Optional[MeasureCreateManipulator] = None
        self._scene_overlay: Optional[MeasureSceneOverlay] = None
        self.__build_scene(ext_id)

        # State Machine Callbacks
        self._state_sub = StateMachine().add_tool_state_changed_fn(self._on_state_changed)
        self._visibility_sub = ui_workspace.set_window_visibility_changed_callback(self._on_visibility_changed)

        # Assign to reference manager
        ReferenceManager().measure_scene = self

    def __build_scene(self, ext_id):
        """
        Called to build the SceneView wehere the MeasureManipulator lives
        """
        with self._viewport_window.get_frame(ext_id):
            with ui.ZStack():
                self._scene_view = sc.SceneView()
                with self._scene_view.scene:
                    self._manipulator = MeasureDrawManipulator(model=self.__measurement_model)
                    self._create_manipulator = MeasureCreateManipulator(self._viewport_window.viewport_api)
                self._scene_overlay = MeasureSceneOverlay()

            self._viewport_window.viewport_api.add_scene_view(self._scene_view)

    def _on_state_changed(self, state: MeasureState, mode: MeasureMode) -> None:
        ReferenceManager().selection_state.enabled = state == MeasureState.NONE

    def _on_visibility_changed(self, name: str, value: bool) -> None:
        if name == EXTENSION_NAME and not value:
            ReferenceManager().selection_state.enabled = True

    def destroy(self) -> None:
        if self._manipulator:
            self._manipulator.clear()
            self._manipulator = None

        if self._scene_overlay:
            self._scene_overlay.destroy()

    # CRUD Operations [Create, Read, Update, Delete]
    def create(self, measure_prim: MeasurePrim) -> bool:
        return self.__measurement_model.create(measure_prim)

    def read(self, uuid: int) -> Optional[_MeasurementItem]:
        return self.__measurement_model.read(uuid)

    def update(self, payload: "MeasurePayload") -> None:
        self.__measurement_model.update(payload)

    def delete(self, uuid: int) -> Optional["MeasurePayload"]:
        return self.__measurement_model.delete(uuid)

    # Selection
    @property
    def selected(self) -> List[int]:
        return self.__measurement_model.selected

    def select(self, uuid: int) -> None:
        self.__measurement_model.select(uuid)

    def deselect_all(self) -> None:
        self.__measurement_model.deselect_all()

    def clear_hovered(self):
        self.__measurement_model.clear_hovered()

    def set_hovered(self, uuid: int, hovered: bool):
        self.__measurement_model.set_hovered(uuid, hovered)

    # Manipulator Specific
    def clear(self) -> None:
        """
        Clears all drawings on the manipulator
        """
        if not self._manipulator:
            return
        self._manipulator.clear()

    @property
    def measurements_visible(self) -> bool:
        return self._manipulator.measurements_visible if self._manipulator else True

    def set_measurements_visible(self, visible: bool) -> None:
        """
        Transiently show/hide all completed measurement drawings without mutating
        the persistent visibility preference or the per-measurement USD payloads.
        """
        if self._manipulator:
            self._manipulator.measurements_visible = visible
