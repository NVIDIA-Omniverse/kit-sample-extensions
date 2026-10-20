# Copyright (c) 2018-2020, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#
__all__ = ["IconModel"]

import carb.eventdispatcher
import omni.kit.app
import omni.usd
from omni.ui import scene as sc
from pxr import Gf, Tf, Usd, UsdGeom

from .scene_camera import CameraModel

ICON_POSITION_ATTR = "icon_position"


class IconModel(CameraModel):
    """
    User part. The model tracks the icon object.
    """

    class IconItem(sc.AbstractManipulatorItem):
        """
        The Model Item represents the icon
        """

        def __init__(self, prim, icon_url, prim_path):
            super().__init__()
            self.prim = prim
            self.icon_url = icon_url
            self.prim_path = prim_path
            self.on_click = None
            self.removed = False
            self.visible = True

    def __init__(self):
        # this should re-create when open stage
        super().__init__()
        self._usd_context = omni.usd.get_context()
        stage = self._usd_context.get_stage()
        self._world_unit = 0.0
        if stage:
            self._world_unit = UsdGeom.GetStageMetersPerUnit(stage)
        if self._world_unit == 0.0:
            self._world_unit = 0.1
        self._usd_listener = Tf.Notice.Register(Usd.Notice.ObjectsChanged, self._on_usd_changed, stage)
        self._icons = {}
        self._stage_sub = carb.eventdispatcher.get_eventdispatcher().observe_event(
            observer_name="omni.kit.prim.icon.model",
            event_name=self._usd_context.stage_event_name(omni.usd.StageEventType.OPENED),
            on_event=lambda _: self._on_stage_opened(),
        )

    def _on_stage_opened(self):
        self._usd_listener = None
        stage = self._usd_context.get_stage()
        self._world_unit = UsdGeom.GetStageMetersPerUnit(stage)
        if self._world_unit == 0.0:
            self._world_unit = 0.1
        self._usd_listener = Tf.Notice.Register(Usd.Notice.ObjectsChanged, self._on_usd_changed, stage)
        self._item_changed(None)

    def get_world_unit(self):
        return max(self._world_unit, 0.1)

    def __del__(self):
        self._stage_sub = None
        self._usd_listener = None
        self.destroy()

    def destroy(self):
        self._icons = {}
        self._usd_listener = None

    def get_item(self, identifier):
        return self._icons

    def get_prim_paths(self):
        return self._icons.keys()

    def get_position(self, prim_path):
        if prim_path in self._icons.keys():
            prim = self._icons[prim_path].prim
            if prim.IsValid():
                attr = prim.GetAttribute(ICON_POSITION_ATTR)
                if attr:
                    return attr.Get()
        return None

    def get_on_click(self, prim_path):
        if prim_path in self._icons.keys():
            return self._icons[prim_path].on_click
        return None

    def get_icon_url(self, prim_path):
        if prim_path in self._icons.keys():
            return self._icons[prim_path].icon_url
        return ""

    def _on_usd_changed(self, notice, stage):
        for path in notice.GetChangedInfoOnlyPaths():
            if path in self._icons.keys():
                self._item_changed(self._icons[path])

    def clear(self):
        self._icons = {}
        self._item_changed(None)

    def add_prim_icon(self, prim_path, icon_url):
        stage = omni.usd.get_context().get_stage()
        prim = stage.GetPrimAtPath(prim_path)
        if not prim:
            return
        self._icons[prim_path] = IconModel.IconItem(prim, icon_url, prim_path)
        self._item_changed(self._icons[prim_path])

    def remove_prim_icon(self, prim_path):
        if prim_path in self._icons.keys():
            self._icons[prim_path].removed = True
            self._item_changed(self._icons[prim_path])
            self._icons.pop(prim_path)

    def set_icon_click_fn(self, prim_path, call_back):
        if prim_path in self._icons.keys():
            self._icons[prim_path].on_click = call_back

    def show_prim_icon(self, prim_path):
        if prim_path in self._icons.keys():
            self._icons[prim_path].visible = True
            self._item_changed(self._icons[prim_path])

    def hide_prim_icon(self, prim_path):
        if prim_path in self._icons.keys():
            self._icons[prim_path].visible = False
            self._item_changed(self._icons[prim_path])
