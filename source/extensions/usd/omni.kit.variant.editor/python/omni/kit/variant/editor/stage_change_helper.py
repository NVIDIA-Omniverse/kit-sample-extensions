# Copyright (c) 2023, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

import weakref
from typing import Dict, Set, Union

import omni.kit.app
import omni.usd
from carb.eventdispatcher import get_eventdispatcher
from pxr import Sdf, Tf, Usd


class StageChangeHelper:
    """Helper class to keep stage change logic self-contained."""

    changed_paths: Dict[Sdf.Path, Union[Set[str], None]] = {}
    """Collected changed paths of stage."""

    instances = []

    _stage_event_sub = None
    _stage_change_sub = None
    _send_changes_sub = None

    def __init__(self) -> None:
        __class__.instances.append(weakref.ref(self))

    def __del__(self):
        del_list = []
        for instance in __class__.instances:
            if instance() is None:
                del_list.append(instance)

        for instance in del_list:
            __class__.instances.remove(instance)

    @staticmethod
    def is_stage_obj_changed(path: Sdf.Path, info: str = None):
        for changed_path, infos in __class__.changed_paths.items():
            if not path.HasPrefix(changed_path):
                continue

            if infos is None:
                return True

            if changed_path != path:
                continue

            if info in infos:
                return True

        return False

    def on_stage_changed(self):
        pass

    def is_changed_path_needed(self, path: Sdf.Path):
        return True

    def enable():
        __class__._stage_event_subs = [
            get_eventdispatcher().observe_event(
                observer_name="omni.kit.prim.icon.scene_camera",
                event_name=omni.usd.get_context().stage_event_name(event),
                on_event=func,
            )
            for event, func in (
                (
                    omni.usd.StageEventType.OPENED,
                    lambda _: __class__._init_changes(),
                ),
                (
                    omni.usd.StageEventType.CLOSING,
                    lambda _: __class__._on_stage_closing(),
                ),
            )
        ]

        __class__._init_changes()

    def disable():
        __class__._send_changes_sub = None
        if hasattr(__class__, "_stage_event_subs") and __class__._stage_event_subs:
            __class__._stage_event_subs.clear()
            __class__._stage_event_subs = None
        __class__._stage_change_sub = None
        __class__.changed_paths.clear()

    def _send_changes_next_update():
        if not __class__.changed_paths:
            return

        if __class__._send_changes_sub is not None:
            return

        def on_update(event):
            for instance in __class__.instances:
                instance().on_stage_changed()

            __class__.changed_paths.clear()

            __class__._send_changes_sub = None

        __class__._send_changes_sub = get_eventdispatcher().observe_event(
            observer_name="variant.editor.sendStageChanges",
            event_name=omni.kit.app.GLOBAL_EVENT_UPDATE,
            on_event=on_update,
        )

    def _init_changes():
        __class__._stage_change_sub = Tf.Notice.Register(
            Usd.Notice.ObjectsChanged,
            __class__._on_objects_changed,
            omni.usd.get_context().get_stage(),
        )
        __class__.changed_paths.clear()
        __class__.changed_paths[Sdf.Path("/")] = None
        __class__._send_changes_next_update()

    def _on_stage_closing():
        __class__._send_changes_sub = None
        __class__.changed_paths.clear()

    def _on_objects_changed(notice: Usd.Notice.ObjectsChanged, sender: Usd.Stage):
        new_paths = {}

        def is_path_needed(path: Sdf.Path):
            for instance in __class__.instances:
                if instance().is_changed_path_needed(path):
                    return True

            return False

        for path in notice.GetResyncedPaths():
            if not is_path_needed(path):
                continue

            new_paths[path] = None

        for path in notice.GetChangedInfoOnlyPaths():
            if not is_path_needed(path):
                continue

            if path.IsPropertyPath():
                new_paths[path] = None
                continue

            infos = set()
            new_paths[path] = infos

            for field in notice.GetChangedFields(path):
                infos.add(field)

        for path, infos in new_paths.items():
            if __class__.is_stage_obj_changed(path):
                continue

            if infos is None:
                # Check if it includes any changed paths
                remove_changed = []
                for changed_path, changed_infos in __class__.changed_paths.items():
                    if changed_path.HasPrefix(path):
                        remove_changed.append(changed_path)

                for remove_path in remove_changed:
                    del __class__.changed_paths[remove_path]

                __class__.changed_paths[path] = None
            else:
                changed_infos = __class__.changed_paths.setdefault(path, set())
                changed_infos.update(infos)

        __class__._send_changes_next_update()
