# Copyright (c) 2023, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

__all__ = ["MeasurementManager"]

import asyncio
from bisect import bisect_left
from functools import partial
from typing import List

import carb.profiler
import omni.kit.commands
import omni.kit.commands as cmds
import omni.kit.undo as undo
import omni.usd as ou
from carb.events import IEvent
from omni.kit.app import get_app
from omni.kit.async_engine import run_coroutine
from omni.kit.usd.layers import LayerEventType
from pxr import Sdf, UsdGeom

from ..common.notification import post_disreguard_future_notification
from ..system import MeasurementModel, MeasurePayload, MeasurePrim
from .reference_manager import ReferenceManager
from .state_machine import StateMachine

ATTR_LIST = [
    ".measure:meta:prim_paths",
    # ".measure:meta:prim_paths:relationship",
    ".measure:meta:points",
    ".measure:meta:local_points",
    # ".measure:meta:tool_mode",
    ".measure:meta:tool_sub_mode",
    ".measure:compute:primary",
    ".measure:compute:secondary",
    ".measure:prop:visible",
    ".measure:prop:axis_display",
    ".measure:prop:unit",
    ".measure:prop:precision",
    ".measure:prop:label_size",
    ".measure:prop:label_color",
]


class MeasurementManager:
    __root_prim_path: Sdf.Path = Sdf.Path("/Viewport_Measure")

    def __singleton_init__(self):
        self.__read_only_dismissed: bool = False
        self._model = MeasurementModel()

        self._closed_id: int = StateMachine().subscribe_to_stage_event(self._model.clear, ou.StageEventType.CLOSED)
        self._opened_id: int = StateMachine().subscribe_to_stage_event(self.__reset, ou.StageEventType.OPENED)

        self._in_live_session: bool = False
        self.__layers_sub = StateMachine().subscribe_to_layer_event(
            self.__on_prim_spec_event, LayerEventType.PRIM_SPECS_CHANGED
        )
        self.__edit_target_sub = StateMachine().subscribe_to_layer_event(
            self.__on_edit_target_changed, LayerEventType.EDIT_TARGET_CHANGED
        )

        self.__pending_changed_paths: set[Sdf.Path] = set()
        self.__objects_changed_task: asyncio.Task = None
        self.__ignore_usd_changes = False
        self._command_callback_ids = []

        self.__stage_sub = StateMachine().subscribe_to_stage_listener(self.__on_objects_changed)

        for command in ["DeletePrims"]:
            command_callback_id = omni.kit.commands.register_callback(
                command, omni.kit.commands.PRE_DO_CALLBACK, self.__on_pre_remove_prim_do
            )
            self._command_callback_ids.append(command_callback_id)

            command_callback_id = omni.kit.commands.register_callback(
                command, omni.kit.commands.POST_UNDO_CALLBACK, self.__on_post_remove_prim_undo
            )
            self._command_callback_ids.append(command_callback_id)

    def __del__(self):
        if self.__objects_changed_task and not self.__objects_changed_task.done():
            self.__objects_changed_task.cancel()
        self.__objects_changed_task = None

        for command_callback_id in self._command_callback_ids:
            omni.kit.commands.unregister_callback(command_callback_id)

        if self._closed_id is not None:
            StateMachine().unsubscribe_to_stage_event(self._closed_id, ou.StageEventType.CLOSED)
            self._closed_id = None

        if self._opened_id is not None:
            StateMachine().unsubscribe_to_stage_event(self._opened_id, ou.StageEventType.OPENED)
            self._opened_id = None

        if self.__layers_sub is not None:
            StateMachine().unsubscribe_to_layer_event(self.__layers_sub, LayerEventType.PRIM_SPECS_CHANGED)
            self.__layers_sub = None

        if self.__edit_target_sub is not None:
            StateMachine().unsubscribe_to_layer_event(self.__edit_target_sub, LayerEventType.EDIT_TARGET_CHANGED)
            self.__edit_target_sub = None

        if self.__stage_sub is not None:
            StateMachine().unsubscribe_to_stage_listener(self.__stage_sub)
            self.__stage_sub = None

    def destroy(self):
        self.__del__()

    @classmethod
    def deinit(cls):
        cls._instance.destroy()
        del cls._instance

    @property
    def selected(self) -> List[MeasurePrim]:
        return self._model.get_selected()

    def __new__(cls):
        if not hasattr(cls, "_instance"):
            cls._instance = super().__new__(cls)
            cls._instance.__singleton_init__()
        return cls._instance

    def __reset(self) -> None:
        # Clear the model for the new stage regardless
        if self.__objects_changed_task and not self.__objects_changed_task.done():
            self.__objects_changed_task.cancel()
        self.__objects_changed_task = None
        self.__pending_changed_paths.clear()
        self._model.clear()
        self.__read_only_dismissed = False
        ReferenceManager().measure_scene.clear()
        self._populate_model_from_stage()

        root_prim = ou.get_context().get_stage().GetPrimAtPath(self.__root_prim_path)
        if root_prim:
            root_prim.SetMetadata("no_delete", True)
            # Re lock all child prims (measurements). This unlocks when joining/leaving a live session
            for measure_prim in self._model.get_items():
                measure_prim._prim.SetMetadata("no_delete", True)

    def __on_read_only_notif(self):
        self.__read_only_dismissed = True

    def __on_edit_target_changed(self, payload, in_session: bool):
        if self._in_live_session == in_session:
            return
        self._in_live_session = in_session
        self.__reset()

    def __on_pre_remove_prim_do(self, params):
        paths = params.get("paths", None)  # List[Union[str, Sdf.Path]]

        # dedup the measure prims
        delete_measure_prims: set["MeasurPrim"] = set()
        prim_to_measure = self._model.prim_paths_to_measure_map

        for path in paths:
            if Sdf.Path(path) != self.__root_prim_path:
                for i in range(len(prim_to_measure)):
                    measure_prim_path, measure_prim = prim_to_measure[i]
                    if measure_prim_path == Sdf.Path(path):
                        delete_measure_prims.add(measure_prim)

        for measure in delete_measure_prims:
            measure_prim: MeasurePrim = self.read(measure.uuid)
            if self._model.remove(measure.uuid):
                ReferenceManager().measure_scene.delete(measure.uuid)
        if delete_measure_prims:
            omni.kit.commands.execute("_RestoreMeasurementOnUndo", measurements=list(delete_measure_prims))

    def __on_post_remove_prim_undo(self, params):
        paths = params.get("paths", None)  # List[Union[str, Sdf.Path]]

        if not paths:
            return

    def __on_prim_spec_event(self, payload, in_session: bool):
        if not payload:
            return
        dirty_specs = []
        for _, specs in payload.layer_spec_paths.items():
            for spec in specs:
                spec_path = Sdf.Path(spec)
                if spec_path.GetParentPath() == self.__root_prim_path:
                    prim = ou.get_context().get_stage().GetPrimAtPath(spec_path.GetPrimPath())
                    if not prim:
                        # Check to see if path is in any of the model items
                        for m_prim in self._model.get_item_children(None):
                            if spec_path == m_prim.path:
                                self.remove_measure_prim(m_prim.uuid)
                                break
                    else:
                        asyncio.ensure_future(self.add_measure_prim(spec_path))

            dirty_specs.extend([Sdf.Path(spec) for spec in specs if spec.startswith("/Viewport_Measure")])

    def __on_objects_changed(self, notice) -> None:
        if not notice:
            return

        if self.__ignore_usd_changes:
            return

        self.__pending_changed_paths.update(notice.GetChangedInfoOnlyPaths())

        # collect all changed paths in this frame and process them in batch
        if not self.__objects_changed_task or self.__objects_changed_task.done():
            self.__objects_changed_task = run_coroutine(self._process_pending_changed_path())

    # TODO: Clean up the logic here to try and simplify
    @carb.profiler.profile
    async def _process_pending_changed_path(self):
        await get_app().next_update_async()  # Allow for fabric to settle before updating measurements

        changed_paths = self.__pending_changed_paths.copy()
        self.__pending_changed_paths.clear()
        stage = ou.get_context().get_stage()

        # dedup the measure prims
        updated_measure_prims: set["MeasurePrim"] = set()
        prim_to_measure = self._model.prim_paths_to_measure_map

        for path in changed_paths:
            prim_path = path.GetPrimPath()
            if prim_path.GetParentPath() != self.__root_prim_path:
                # Check if the prim is a property with transformation attribute change
                if path.IsPropertyPath() and UsdGeom.Xformable.IsTransformationAffectedByAttrNamed(path.name):
                    # This is to emulate the std::set::lower_bound to find all measure_prims who's prim_paths or their
                    # ancestor paths has changed
                    index = bisect_left(prim_to_measure, prim_path, key=lambda r: r[0])
                    # If we've found a index, it means the prim_path or its descendants can affect a measure_prim.
                    # iterate through all of them until measure_prim_path is no longer a descendent of prim_path
                    for i in range(index, len(prim_to_measure)):
                        measure_prim_path, measure_prim = prim_to_measure[i]
                        if measure_prim_path.HasPrefix(prim_path):
                            updated_measure_prims.add(measure_prim)
                        else:
                            break
            else:
                prim = stage.GetPrimAtPath(prim_path)
                if not prim.IsValid():
                    continue

                measure_prim = self._model.get_item(prim.GetAttribute("measure:uuid").Get())
                if measure_prim is None:
                    continue  # Catches a new measurement before its stored in the model.

                elif path.IsPropertyPath():
                    # Update the measurement from the prim. This means:
                    # A) It exists in stage as a child of the root, B) It exists in the model
                    updated_measure_prims.add(measure_prim)

        # _model.update triggers USD changes since it writes to USD
        # don't double handle the changes we made just now
        was_ignoring_usd_changes = self.__ignore_usd_changes
        self.__ignore_usd_changes = True

        for measure_prim in updated_measure_prims:
            self._model.update(measure_prim)
        self.__ignore_usd_changes = was_ignoring_usd_changes

    def _populate_model_from_stage(self) -> None:
        # Check if parent prim exists, if not, early exit
        stage = ou.get_context().get_stage()

        if stage == None:
            return

        root_prim = stage.GetPrimAtPath(self.__root_prim_path)
        if not root_prim.IsValid():
            return

        # Iterate through parent prim and grab every child prim.
        for child in root_prim.GetChildrenNames():
            # Rebuild the MeasurePrim and add to the model
            measure_prim = MeasurePrim.from_prim(f"{self.__root_prim_path}/{child}")
            if measure_prim == None:
                continue
            self._model.add(measure_prim.uuid, measure_prim)
            # Tell the draw manipulator to create the measurement.
            ReferenceManager().measure_scene.create(measure_prim)

    def _create_internal(self, measure_payload: MeasurePayload):
        with ReferenceManager().edit_context:
            stage = ou.get_context().get_stage()
            root_prim = stage.GetPrimAtPath("/Viewport_Measure")
            if root_prim == None:
                cmds.execute("CreatePrimCommand", prim_type="", prim_path="/Viewport_Measure")
                root_prim = stage.GetPrimAtPath("/Viewport_Measure")
                root_prim.SetMetadata("no_delete", True)

            name = f"measurement_{measure_payload.tool_mode.name.lower()}"

            prim_path = ou.get_stage_next_free_path(stage, f"/Viewport_Measure/{name}", False)
            measure_prim: MeasurePrim = MeasurePrim(prim_path, measure_payload)
            self._model.add(measure_payload.uuid, measure_prim)
            ReferenceManager().measure_scene.create(measure_prim)

    def create(self, measure_payload: MeasurePayload):
        # ctx = ou.get_context()
        # if not ctx.is_writable():
        #     if not self.__read_only_dismissed:
        #         layer = ctx.get_stage().GetEditTarget().GetLayer()
        #         post_disreguard_future_notification(
        #             f"{layer.GetDisplayName()} is not writable. The measurement can not be saved.",
        #             self.__on_read_only_notif,
        #         )
        #     return
        cmds.execute("CreateMeasurementCommand", measure_payload=measure_payload)

    async def add_measure_prim(self, spec_path: str):
        await omni.kit.app.get_app().next_update_async()
        await omni.kit.app.get_app().next_update_async()
        measure_prim = MeasurePrim.from_prim(spec_path)
        measure_prim.name = Sdf.Path(spec_path).name
        self._model.add(measure_prim.uuid, measure_prim)
        ReferenceManager().measure_scene.create(measure_prim)

    def remove_measure_prim(self, uuid: int):
        ReferenceManager().measure_scene.delete(uuid)
        self._model.remove(uuid)

    def set_visibility_all(self, visible: bool):
        for measure_prim in self._model.get_items():
            self.set_visibility(measure_prim.uuid, visible)

    def set_visibility(self, uuid: int, visible: bool):
        measure_prim: MeasurePrim = self.read(uuid)
        measure_prim.payload.visible = visible
        ReferenceManager().measure_scene.update(measure_prim.payload)

    def redraw_all(self):
        for measure_prim in self._model.get_items():
            ReferenceManager().measure_scene.update(measure_prim.payload)

    def frame_measurement(self, uuid: int):
        measure_prim: MeasurePrim = self.read(uuid)
        measure_prim.frame()

    def read(self, uuid: int) -> MeasurePrim:
        return self._model.get_item(uuid)

    def rename(self, uuid: int, name: str) -> MeasurePrim:
        old_measure_prim: MeasurePrim = MeasurementManager().read(uuid)
        old_path = old_measure_prim.path
        new_path = Sdf.Path(old_path.ReplaceName(name))
        cmds.execute("MovePrim", path_from=old_path, path_to=new_path)

    def update(self, uuid: int):
        return NotImplementedError

    def delete(self, uuid: int) -> bool:
        measure_prim: MeasurePrim = self.read(uuid)
        if self._model.remove(uuid):
            ReferenceManager().measure_scene.delete(uuid)
            cmds.execute("RemoveMeasurementCommand", measure_prim=measure_prim)
            # Clear the viewport manipulator
            return True
        return False

    def delete_all(self):
        uuids = [measure_prim.uuid for measure_prim in self._model._measurements.values()]
        with undo.group():
            for uuid in uuids:
                self.delete(uuid)
