# Copyright (c) 2023, NVIDIA CORPORATION.  All rights reserved.
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
from collections import defaultdict

import carb
import omni.kit.app
from pxr import Tf, Trace, Usd


def handle_exception(func):
    """
    Decorator to print exception in async functions

    TODO: The alternative way would be better, but we want to use traceback.format_exc for better error message.
        result = await asyncio.gather(*[func(*args)], return_exceptions=True)
    """

    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except asyncio.CancelledError:
            # We always cancel the task. It's not a problem.
            pass
        except Exception as e:
            carb.log_error(f"Exception when async '{func}'")
            carb.log_error(f"{e}")
            carb.log_error(f"{traceback.format_exc()}")

    return wrapper


class StageChangeHelper:
    """Helper class to keep stage change logic self-contained."""

    def __init__(self, model):
        self._model = model
        self._dirty_prim_paths = defaultdict(set)
        self._prim_changed_task: asyncio.Future = None
        self._stage_listener_sub = None
        self._active = False

    @property
    def model(self):
        return self._model

    @property
    def dirty_prim_paths(self):
        return self._dirty_prim_paths

    def consume_dirty_paths(self):
        ret = self._dirty_prim_paths
        self._dirty_prim_paths = defaultdict(set)
        return ret

    def destroy(self):
        self.unregister_stage_listener()
        self._stage_listener_sub = None
        self._dirty_prim_paths = defaultdict(set)
        self._prim_changed_task = None

    def register_stage_listener(self, stage: Usd.Stage):
        self.unregister_stage_listener()
        self._dirty_prim_paths = defaultdict(set)
        self._prim_changed_task = None
        self._stage_listener_sub = Tf.Notice.Register(Usd.Notice.ObjectsChanged, self._on_objects_changed, stage)
        self._active = True

    def unregister_stage_listener(self):
        self._active = False
        if self._stage_listener_sub:
            self._stage_listener_sub.Revoke()
        if self._prim_changed_task:
            self._prim_changed_task.cancel()

    @Trace.TraceFunction
    def _on_objects_changed(self, notice: Tf.Notice, sender: Usd.Stage):
        """Observe ONLY variant selection changes via the 'variantSelection' field.

        USD emits ObjectsChanged notices for UsdVariantSet.SetVariantSelection() as
        resyncs (or info-only notices) on the *prim path*, with 'variantSelection'
        listed in notice.GetChangedFields(path). The prior filter matched on
        property paths named 'set()', which USD does not emit for variant selection
        changes in ObjectsChanged — the filter rejected every real notice, so the
        presenter never refreshed when variants changed externally.

        Performance: notice.GetChangedFields() is read directly off the notice and
        requires no Usd.Prim lookups or stage traversal, so this preserves the
        107.1.3 optimization goal of avoiding expensive HasVariantSets() /
        GetPrimAtPath() calls on complex stages.

        Trade-off: structural changes to variant sets (adding/removing/renaming
        variant sets) may not list 'variantSelection' in the changed fields and
        therefore won't trigger auto-refresh — users can click the refresh button
        for those rare operations, same as before.
        """
        variant_selection_changed = False

        for p in notice.GetResyncedPaths():
            if "variantSelection" in notice.GetChangedFields(p):
                prim_path = p.GetPrimPath() if p.IsPropertyPath() else p
                self._dirty_prim_paths[prim_path].add(p)
                variant_selection_changed = True

        for p in notice.GetChangedInfoOnlyPaths():
            if "variantSelection" in notice.GetChangedFields(p):
                prim_path = p.GetPrimPath() if p.IsPropertyPath() else p
                self._dirty_prim_paths[prim_path].add(p)
                variant_selection_changed = True

        if not variant_selection_changed:
            return

        # Update in the next frame to accumulate affected prims
        if self._prim_changed_task is None or self._prim_changed_task.done():
            self._prim_changed_task = asyncio.ensure_future(self.async_prim_changed())

    @handle_exception
    async def async_prim_changed(self):
        """Called to pump changes at the next frame after the changes received"""
        # Pump the changes to the model if we're still active.
        await omni.kit.app.get_app().next_update_async()
        if self._active:
            self._model.update_dirty()
            self._prim_changed_task = None
