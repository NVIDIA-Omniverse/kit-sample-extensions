# Copyright (c) 2023, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

from typing import Any

import carb.events
import omni.timeline
import omni.usd as ou
from pxr import Sdf, Usd

from ...manager.state_machine import StateMachine


# Why AttributeValueCache?
# Since calling GetFaceVertexCountsAttr, GetFaceVertexIndicesAttr and GetPointsAttr takes considerable amount of time on
# very dense mesh, even only for read, we do not want to keep calling them every frame when trying to find a snap target.
# This AttributeValueCache caches the value returned by Get(), and handles invalidation upon USD changes or time changes.
class AttributeValueCache:
    def __singleton_init__(self):
        self.__usd_context = ou.get_context()
        self.__timeline = omni.timeline.get_timeline_interface()
        self.__stage: Usd.Stage = None
        self.__time_code = Usd.TimeCode.Default()
        self.__attribute_value_cache: dict[Sdf.Path, Any] = {}

        self.__opened_id: int = StateMachine().subscribe_to_stage_event(
            self.__on_stage_opened, ou.StageEventType.OPENED
        )

        self.__stage_sub = StateMachine().subscribe_to_stage_listener(self.__on_objects_changed)

        self.__timeline_sub = self.__timeline.get_timeline_event_stream().create_subscription_to_pop(
            self.__on_timeline_event
        )

        self.__on_stage_opened()

    def __new__(cls):
        if not hasattr(cls, "_instance"):
            cls._instance = super().__new__(cls)
            cls._instance.__singleton_init__()
        return cls._instance

    def __del__(self):
        if self.__stage_sub is not None:
            StateMachine().unsubscribe_to_stage_listener(self.__stage_sub)
            self.__stage_sub = None

        if self.__opened_id is not None:
            StateMachine().unsubscribe_to_stage_event(self.__opened_id, ou.StageEventType.OPENED)
            self.__opened_id = None

        self.__timeline_sub = None
        self.__attribute_value_cache.clear()

    def destroy(self):
        self.__del__()

    @classmethod
    def deinit(cls):
        cls._instance.destroy()
        del cls._instance

    def get_value(self, path: Sdf.Path) -> Any:
        if path not in self.__attribute_value_cache:
            attribute = self.__stage.GetAttributeAtPath(path)
            if attribute.IsValid():
                value = attribute.Get(self.__time_code)
                self.__attribute_value_cache[path] = value
                return value

        return self.__attribute_value_cache.get(path, None)

    def __on_stage_opened(self):
        self.__stage = self.__usd_context.get_stage()
        self.__attribute_value_cache.clear()

    def __on_timeline_event(self, e: carb.events):
        time_code = Usd.TimeCode(self.__timeline.get_current_time() * self.__timeline.get_time_codes_per_seconds())
        if time_code != self.__time_code:
            self.__time_code = time_code
            self.__attribute_value_cache.clear()

    def __on_objects_changed(self, notice) -> None:
        if not notice:
            return

        for path in notice.GetChangedInfoOnlyPaths():
            self.__attribute_value_cache.pop(path, None)

        for path in notice.GetResyncedPaths():
            self.__attribute_value_cache.pop(path, None)
