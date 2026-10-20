# Copyright (c) 2021, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#
import asyncio
import functools
import traceback
from typing import Callable, List, Optional

import carb
import carb.events
import omni.usd
from carb.eventdispatcher import get_eventdispatcher
from omni.usd.commands import UsdStageHelper
from pxr import Sdf, Tf, Trace, Usd

from .stage_duplicate_utils import copy_prim, copy_property

# The number of frames with no stage modification to update the relevant stage
DELAY_FRAMES = 1


def handle_exception(func):
    """
    Decorator to print exception in async functions
    """

    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            carb.log_error(f"Exception when async '{func}'")
            carb.log_error(f"{e}")
            carb.log_error(f"{traceback.format_exc()}")

    return wrapper


class RelevantStage:
    def __init__(self, target_context_name: str, source_context_name: str = ""):
        """
        Construct RelevantStage

        ### Arguments:

            `target_context_name : str`
                The target context name

            `source_context_name : str`
                The source context name
        """
        self._target_context_name = target_context_name
        self._source_context_name = source_context_name

        # Main context
        usd_context = omni.usd.get_context(self._source_context_name)

        context = omni.usd.get_context(self._target_context_name)
        if not context:
            context = omni.usd.create_context(self._target_context_name)
            context.new_stage()
            omni.usd.add_hydra_engine("rtx", context)
            # sync the render setting between the source stage and the target stage to avoid rendering difference
            context.load_render_settings_from_stage(usd_context.get_stage_id())
            self._created = True
        else:
            self._created = False

        self._stage_subscriptions = [
            get_eventdispatcher().observe_event(
                observer_name="omni.kit.widget.material_preview",
                event_name=usd_context.stage_event_name(event_name),
                on_event=func,
            )
            for event_name, func in (
                (omni.usd.StageEventType.OPENED, lambda _: self._on_stage_opened()),
                (omni.usd.StageEventType.CLOSING, lambda _: self._on_stage_closing()),
            )
        ]

        self.__dirty_paths: List[Sdf.Path] = []
        self.__prim_changed_task = None
        self.__delay_frames = DELAY_FRAMES
        self._root = None
        self._root_changed_fn: Optional[Callable[[List[Sdf.Path]], None]] = None

        self.__stage_notice = None
        self._on_stage_opened()

    def destroy(self):
        self.__stage_notice = None
        self._root_changed_fn = None
        self.__dirty_paths = []

        if self._stage_subscriptions:
            self._stage_subscriptions.clear()
            self._stage_subscriptions = None

        if self.__prim_changed_task is not None:
            self.__prim_changed_task.cancel()
            self.__prim_changed_task = None

        if self._created:
            context = omni.usd.get_context(self._target_context_name)
            omni.usd.release_all_hydra_engines(context)
            omni.usd.destroy_context(self._target_context_name)

    def set_root_changed_fn(self, fn: Callable[[List[Sdf.Path]], None]):
        self._root_changed_fn = fn

    def set_listen_root(self, root: Optional[Sdf.Path]):
        """
        Specify the path this object listens changes of and sends deltas to
        teh remote Kit
        """
        self._root = root

    def clear(self):
        context = omni.usd.get_context(self._target_context_name)
        stage = context.get_stage()
        # TODO: Find out why this crashes:
        # stage.GetRootLayer().Clear()
        # TODO: Find out why this crashes:
        # context.new_stage()
        for child in dict(stage.GetRootLayer().pseudoRoot.nameChildren):
            stage.RemovePrim(Sdf.Path(f"/{child}"))

    def submit_layer(self, delta_layer: Sdf.Layer):
        """Send the given layer to the own context"""
        stage_from = Usd.Stage.Open(delta_layer)
        stage_to = omni.usd.get_context(self._target_context_name).get_stage()
        copy_prim(stage_from.GetPseudoRoot(), stage_to, self._target_context_name)

    def submit_text(self, delta_text: str):
        """Send the given layer to the own context"""
        layer = Sdf.Layer.CreateAnonymous("swatch.usda")
        layer.ImportFromString(delta_text)
        self.submit_layer(layer)

    def update_dirty(self):
        """
        Create/remove dirty items that was collected from TfNotice. Can be
        called any time to pump changes.
        """
        dirty_paths = self.__dirty_paths
        self.__dirty_paths = []

        if self._root is None:
            return

        dirty_paths = [p for p in set(dirty_paths) if p.HasPrefix(self._root)]
        if not dirty_paths:
            return

        dirty_prim_paths = []
        dirty_material_prop_paths = []
        has_root = False

        for path in dirty_paths:
            if path == Sdf.Path.absoluteRootPath:
                has_root = True
                break
            elif path.IsPropertyPath():
                parent = path.GetParentPath()
                dirty_material_prop_paths.append(path)
                dirty_prim_paths.append(parent)
            else:
                dirty_prim_paths.append(path)

        # TODO: Those two are slow. We need to cache stages.
        stage_from = omni.usd.get_context(self._source_context_name).get_stage()
        stage_to = omni.usd.get_context(self._target_context_name).get_stage()

        # Copy
        if has_root:
            # Everything is changed
            copy_prim(stage_from.GetPseudoRoot(), stage_to, self._target_context_name)
        else:
            # Copy prims and properties
            for path in sorted(set(dirty_prim_paths)):
                copy_prim(stage_from.GetPrimAtPath(path), stage_to, self._target_context_name)

            if self._root_changed_fn and dirty_material_prop_paths:
                self._root_changed_fn(list(sorted(set(dirty_material_prop_paths))))

        self.__delay_frames = DELAY_FRAMES

    def _on_stage_opened(self):
        """Called when opening a new stage"""
        usd_context = omni.usd.get_context(self._source_context_name)
        stage = usd_context.get_stage()
        if not stage:
            return

        self.__stage_notice = Tf.Notice.Register(Usd.Notice.ObjectsChanged, self._on_objects_changed, stage)

    def _on_stage_closing(self):
        """Called when close the stage"""
        self.__stage_notice = None

    @Trace.TraceFunction
    def _on_objects_changed(self, notice, sender):
        """
        Called by Usd.Notice.ObjectsChanged. It's critically important to
        return ASAP.
        """
        dirty_prims_paths = []

        for p in notice.GetResyncedPaths():
            dirty_prims_paths.append(p)

        for p in notice.GetChangedInfoOnlyPaths():
            dirty_prims_paths.append(p)

        if not dirty_prims_paths:
            return

        self.__dirty_paths += dirty_prims_paths

        # Update in the next frame. We need it because we want to accumulate the affected prims
        if self.__prim_changed_task is None or self.__prim_changed_task.done():
            self.__prim_changed_task = asyncio.ensure_future(self.__delayed_prim_changed())

    @handle_exception
    @Trace.TraceFunction
    async def __delayed_prim_changed(self):
        """Called to update the dirty data in the next frame"""
        while self.__delay_frames > 0:
            await omni.kit.app.get_app().next_update_async()
            self.__delay_frames -= 1

        # Pump the changes to the model.
        self.update_dirty()

        self.__prim_changed_task = None
