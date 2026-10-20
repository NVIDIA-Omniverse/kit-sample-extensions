# Copyright (c) 2018-2020, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#
import carb
import omni.usd
import usdrt
from pxr import Usd

_is_legacy_stage_event_system = False
try:
    from carb.eventdispatcher import get_eventdispatcher
except ImportError:
    _is_legacy_stage_event_system = True


class CollectionWatch(object):
    """
    The object that update collection in TreeView when the scene collection is
    changed.
    """

    def __init__(self):
        super().__init__()
        self._usd_context = omni.usd.get_context()
        self._stage_sub = None
        self._current_collection = []
        self._reattach()
        self._subscribe_stage_events()

    def _reattach(self):
        self._current_collection = []
        try:
            # OMPE-72501: while initializing the extension, the stage (and its corresponding ID)
            # is not yet valid, retiveing the ID will make usdrt.Usd.Stage.Attach raise exception.
            # Here the validity of stage ID is checked before passing it to usdrt.Usd.Stage.Attach
            stage_id = omni.usd.get_context().get_stage_id()
            if not Usd.StageCache.Id.FromLongInt(stage_id).IsValid():
                return
            usdrt_stage = usdrt.Usd.Stage.Attach(stage_id)
            ovstage_backed = getattr(usdrt, "OVSTAGE_BACKED", False)
            if usdrt_stage and not ovstage_backed and hasattr(usdrt_stage, "GetPrimsWithAppliedAPIName"):
                self._current_collection = usdrt_stage.GetPrimsWithAppliedAPIName("CollectionAPI")
            else:
                # Kit 111's OVStage-backed USDRT (what production apps load; usdrt.OVSTAGE_BACKED) returns no stage
                # until Kit publishes it, and its GetPrimsWithAppliedAPIName finds no multi-apply schema by base name:
                # read the composed USD stage. CollectionAPI is multi-apply, so its applied schemas read
                # "CollectionAPI:<name>".
                stage = omni.usd.get_context().get_stage()
                if stage:
                    self._current_collection = [
                        prim.GetPath()
                        for prim in stage.Traverse()
                        if any(schema.split(":")[0] == "CollectionAPI" for schema in prim.GetAppliedSchemas())
                    ]
        except Exception as e:
            carb.log_warn(f"Get collection from usdrt stage failed: {e}")

    def _subscribe_stage_events(self):
        if self._usd_context:
            global _is_legacy_stage_event_system
            if not _is_legacy_stage_event_system:
                try:
                    # this is not working less than kit sdk 107.3
                    self._stage_sub = get_eventdispatcher().observe_event(
                        observer_name="omni.kit.collection.window:get_collection",
                        event_name=self._usd_context.stage_event_name(omni.usd.StageEventType.OPENED),
                        on_event=lambda _: self._on_stage_opened(),
                    )
                except AttributeError:
                    _is_legacy_stage_event_system = True
            if _is_legacy_stage_event_system:
                self._stage_sub = self._usd_context.get_stage_event_stream().create_subscription_to_pop(
                    self._on_stage_event, name="omni.kit.collection.window:get_collection"
                )

    def add_collection(self, path):
        for p in self._current_collection:
            if str(p) == str(path):
                return
        self._current_collection.append(path)

    def remove_collection(self, path):
        for p in self._current_collection:
            if str(p) == str(path):
                self._current_collection.remove(p)

    @property
    def current_collection(self):
        return self._current_collection

    def destroy(self):
        if _is_legacy_stage_event_system:
            self._stage_sub.unsubscribe()
        else:
            self._stage_sub.reset()

    def _on_stage_event(self, event):
        if event.type == int(omni.usd.StageEventType.OPENED):
            self._on_stage_opened()

    def _on_stage_opened(self):
        self._reattach()
