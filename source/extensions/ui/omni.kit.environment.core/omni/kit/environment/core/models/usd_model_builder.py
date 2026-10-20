# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
import asyncio
from typing import Any, Callable, Dict, List, Optional, Union

import carb
import carb.profiler
import omni.kit.app
import omni.usd
from carb.eventdispatcher import get_eventdispatcher
from omni import ui
from pxr import Sdf, Tf, Trace, Usd

from ..singleton import Singleton
from .prim_value_model import PrimValueModel
from .property_value_model import PropertyValueModel


@Singleton
class UsdModelBuilder:
    """
    Represent builder for usd properties.
    It will trace prim and prim property changes and update value model.
    """

    def __init__(self):
        self._stage = None
        self._listener = None
        self._prim_paths = []
        self._property_models: Dict[str, PropertyValueModel] = {}
        self._prim_models: Dict[str, PrimValueModel] = {}
        self._prim_changed_fns: Dict[str, List[Callable[[Usd.Stage, str], None]]] = {}

        self._stop_event = asyncio.Event()
        self._work_queue = asyncio.Queue()

        asyncio.ensure_future(self._delayed_dirty_handler())

        self._context = omni.usd.get_context()
        self._stage_event_sub = get_eventdispatcher().observe_event(
            observer_name="omni.kit.environment.core.UsdModelBuilder",
            event_name=self._context.stage_event_name(omni.usd.StageEventType.OPENED),
            on_event=self._on_stage_opened,
        )

    def destroy(self):
        """Clean up and revoke USD model builder resources.

        Stops the work queue, revokes the listener, and destroys property and prim models along with registered callbacks.
        """
        self._stop_event.set()
        self._work_queue.put_nowait(None)
        self.stop()
        self._stage_event_sub = None
        for path in self._property_models:
            self._property_models[path].destroy()
        for path in self._prim_models:
            self._prim_models[path].destroy()
        for path in self._prim_changed_fns:
            self._prim_changed_fns[path].clear()

    def create_property_value_model(
        self,
        property_path: str,
        value_type: Sdf.ValueTypeName = Sdf.ValueTypeNames.String,
        default: Any = "",
        min: Union[int, float, None] = None,
        max: Union[int, float, None] = None,
        default_prim_type: Optional[str] = None,
    ) -> PropertyValueModel:
        """Create a value model for property.

        Args:
            property_path (str): Property path.
            value_type (Sdf.ValueTypeName): Property value type; used to create attributes if not exists. Default Sdf.ValueTypeNames.String.
            default (Any): Default property value. Default empty string.
            min (Union[int, float, None]): Minimum allowed value; default is None.
            max (Union[int, float, None]): Maximum allowed value; default is None.
            default_prim_type (Optional[str]): Prim type for creation if the prim does not exist; default is None to not create.

        Returns:
            PropertyValueModel: The created or existing property value model.
        """
        if property_path in self._property_models:
            return self._property_models[property_path]
        else:
            if self._stage is None:
                self._stage = omni.usd.get_context().get_stage()
            value_model = PropertyValueModel(
                property_path,
                self._stage,
                value_type=value_type,
                default=default,
                min=min,
                max=max,
                default_prim_type=default_prim_type,
            )
            self._property_models[property_path] = value_model

            # Auto start
            if self._listener is None and self._stage:
                self.start(self._stage)

            return value_model

    def create_prim_value_model(self, prim_path: str) -> PrimValueModel:
        """Create a value model for prim path.

        Args:
            prim_path (str): Prim path.

        Returns:
            PrimValueModel: The created or existing prim value model.
        """
        if prim_path in self._prim_models:
            return self._prim_models[prim_path]
        else:
            if self._stage is None:
                self._stage = omni.usd.get_context().get_stage()
            value_model = PrimValueModel(prim_path, self._stage)
            self._prim_models[prim_path] = value_model

            # Auto start
            if self._listener is None and self._stage:
                self.start(self._stage)

            return value_model

    def register_prim_callback(self, prim_path: str, on_prim_changed_fn: Callable[[Usd.Stage, str], None]) -> None:
        """
        Register callback if prim created/removed.
        Args:
            prim_path (str): Prim path. Could be start part of desired prim.
            on_prim_changed_fn (Callable[[Usd.Stage, str], None]): Callback when prim created/removed. Function signure:
                void on_prim_changed_fn(stage, path)
        """
        if prim_path not in self._prim_changed_fns:
            self._prim_changed_fns[prim_path] = []
        if on_prim_changed_fn not in self._prim_changed_fns[prim_path]:
            self._prim_changed_fns[prim_path].append(on_prim_changed_fn)

    def start(self, stage: Usd.Stage):
        """Start tracing in stage.

        Args:
            stage (Usd.Stage): The stage to trace for changes.
        """
        if self._listener is not None:
            if self._stage == stage:
                return
            else:
                self.stop()

        carb.log_info(f"[UsdModelBuilder] STARTED on {stage}")
        self._stage = stage
        self._listener = Tf.Notice.Register(Usd.Notice.ObjectsChanged, self._on_usd_changed, self._stage)

    def stop(self):
        """
        Stop tracing.
        """
        carb.log_info("[UsdModelBuilder] STOPPED!")
        if self._listener is not None:
            self._listener.Revoke()
        self._listener = None

    @Trace.TraceFunction
    def _on_usd_changed(self, notice, stage):
        carb.profiler.begin(1, "UsdModelBuilder._on_usd_changed")

        if stage != self._stage:
            return

        dirty_paths = set()

        for path in notice.GetResyncedPaths():
            # carb.log_info(f"[UsdModelBuilder] resync {path}")
            for callback_path in self._prim_changed_fns:
                if callback_path.startswith(path.pathString):
                    dirty_paths.add(Sdf.Path(callback_path))
                if path.pathString.startswith(callback_path):
                    dirty_paths.add(path)
            for property_path in self._property_models:
                if property_path.startswith(path.pathString):
                    dirty_paths.add(Sdf.Path(property_path))
            for prim_path in self._prim_models:
                if prim_path.startswith(path.pathString):
                    dirty_paths.add(Sdf.Path(prim_path))

        for path in notice.GetChangedInfoOnlyPaths():
            # carb.log_info(f"[UsdModelBuilder] changeInfoOnly {path}")
            dirty_paths.add(path)

        if hasattr(notice, "GetFastUpdates"):
            for fast_update in notice.GetFastUpdates():
                # carb.log_info(f"[UsdModelBuilder] fastUpdate {path}")
                dirty_paths.add(fast_update.path)

        if dirty_paths:
            self._work_queue.put_nowait(dirty_paths)

        carb.profiler.end(1)

    async def _delayed_dirty_handler(self):
        while not self._stop_event.is_set():
            sdf_paths = await self._work_queue.get()
            if sdf_paths is None:
                break
            carb.profiler.begin(1, "UsdModelBuilder._delayed_dirty_handler")
            for sdf_path in sdf_paths:
                path = sdf_path.pathString
                if path in self._property_models:
                    self._property_models[path].on_property_changed(self._stage)
                elif path in self._prim_models:
                    self._prim_models[path].on_prim_changed(self._stage)
                if "." not in path:
                    for callback_path in self._prim_changed_fns:
                        if path.startswith(callback_path) and len(path.split("/")) == len(callback_path.split("/")):
                            for callback in self._prim_changed_fns[callback_path]:
                                callback(self._stage, path)
            carb.profiler.end(1)

    def _on_stage_opened(self, _):
        self._stage = self._context.get_stage()
        property_paths = list(self._property_models.keys())
        for path in property_paths:
            if path in self._property_models:
                self._property_models[path].on_property_changed(self._stage)
        prim_paths = list(self._prim_models)
        for path in prim_paths:
            if path in self._prim_models:
                self._prim_models[path].on_prim_changed(self._stage)
        if self._listener is None:
            self.start(self._stage)
        else:
            self.stop()
            self.start(self._stage)
