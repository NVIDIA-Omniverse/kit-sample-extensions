# Copyright (c) 2022, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

import weakref
from typing import Dict, List

import carb.events
import omni.kit.app
import omni.usd

from .bezier_curve_edits import BezierCurveEdits
from .cv_payload import CvPayloadManager
from .cv_selection import CvSelection


class BezierCurveEditsContext:
    def __init__(self, usd_context_name: str = ""):
        self._usd_context_name = usd_context_name
        self._context = omni.usd.get_context(usd_context_name)
        self._selection = CvSelection()
        self._edits = BezierCurveEdits(usd_context_name, self._selection)
        self._payload_manager = CvPayloadManager(self._selection, usd_context_name)
        self._stage_event_sub = self._context.get_stage_event_stream().create_subscription_to_pop(self._on_stage_event)

    def destroy(self):
        if self._edits:
            self._edits.destroy()
            self._edits = None

        if self._selection:
            self._selection.destroy()
            self._selection = None

        self._stage_event_sub = None

    def __del__(self):
        self.destroy()

    @property
    def usd_context(self) -> omni.usd.UsdContext:
        return self._context

    @property
    def usd_context_name(self) -> str:
        return self._usd_context_name

    @property
    def curve_edits(self) -> BezierCurveEdits:
        return weakref.proxy(self._edits)

    @property
    def selection(self) -> CvSelection:
        return weakref.proxy(self._selection)

    def set_default_prim_paths(self, paths: List[str]):
        self._payload_manager.set_default_prim_paths(paths)

    def _on_stage_event(self, event: carb.events.IEvent):
        if event.type == int(omni.usd.StageEventType.CLOSING):
            self._selection.clear_all_selection()


class BezierCurveEditsContextManager:
    _contexts: Dict[str, BezierCurveEditsContext] = {}

    @classmethod
    def clear(cls):
        for _, context in cls._contexts.items():
            context.destroy()
        cls._contexts.clear()

    @classmethod
    def get_context(cls, usd_context_name: str = "") -> BezierCurveEditsContext:
        if usd_context_name not in cls._contexts:
            cls._contexts[usd_context_name] = BezierCurveEditsContext(usd_context_name)

        return cls._contexts[usd_context_name]

    @classmethod
    def destroy_context(cls, usd_context_name: str = ""):
        cls._contexts.discard(usd_context_name)
