# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
import math
from typing import List

import carb
import omni.timeline
import omni.usd
from omni.kit.viewport.utility import get_active_viewport, get_active_viewport_camera_string
from omni.kit.viewport.utility.camera_state import ViewportCameraState
from pxr import Gf, Sdf, Tf, Usd

from ..common import IGNORE_PRIM_ATTR_NAME, create_data_only_prim
from .abstract_setting import AbstractWaypointSetting

WAYPOINT_ATTR_CAMERA_NAME = "camera_name"
WAYPOINT_ATTR_CAMERA_PATH = "camera:path"
WAYPOINT_ATTR_ICON_POSITION = "icon_position"
LOCK_CAMERA_ATTR = "omni:kit:cameraLock"
EXCLUDED_CAMERA_ATTR_NAMES = {IGNORE_PRIM_ATTR_NAME, "fStop"}
EXCLUDED_CAMERA_ATTR_PREFIXES = (
    "exposure:",
    "omni:rtx:",
)


def _should_skip_camera_attr(attr_name: str) -> bool:
    return attr_name in EXCLUDED_CAMERA_ATTR_NAMES or attr_name.startswith(EXCLUDED_CAMERA_ATTR_PREFIXES)


class CameraSetting(AbstractWaypointSetting):
    def __init__(self, edit_context, viewport_widget=None):
        super().__init__(edit_context)
        self.__edit_context = edit_context
        # Camera path where waypoint comes from
        self.camera_path: str = ""
        # Waypoint camera prim
        self.camera_prim: Usd.Prim = None
        # If viewport is a widget instead of a window, then use this to get values
        self.__viewport_widget = viewport_widget

    def get_name(self) -> str:
        return "Cameras"

    def is_dirty(self) -> bool:
        if not self.valid:
            return False
        if self.__viewport_widget:
            active_camera = self.__viewport_widget.camera_path.pathString
        else:
            active_camera = get_active_viewport_camera_string()
        stage = omni.usd.get_context().get_stage()
        if stage is None or omni.usd.get_context().get_stage_state() != omni.usd.StageState.OPENED:
            return True
        active_camera_prim = stage.GetPrimAtPath(active_camera)
        if not active_camera_prim or not self.camera_prim:
            return True

        timeline = omni.timeline.get_timeline_interface()
        time_code = timeline.get_current_time() * timeline.get_time_codes_per_seconds()

        # Move list to dictionaries of attr.name => attribute
        #
        active_camera_attributes = {
            a.GetName(): a for a in self._filter_attributes(active_camera_prim.GetAttributes(), time_code)
        }
        current_camera_attributes = {
            a.GetName(): a for a in self._filter_attributes(self.camera_prim.GetAttributes(), time_code)
        }

        # Organize dictionaries into attrs_a, attrs_b where attrs_a hold the large dictionary
        #
        if len(active_camera_attributes) >= len(current_camera_attributes):
            attrs_a, attrs_b = active_camera_attributes, current_camera_attributes
        else:
            attrs_a, attrs_b = current_camera_attributes, active_camera_attributes

        # Iterate all name, attributes in attrs_a and if it also exists in attrs_b;
        # compare the values (it is dirty if they do not match)
        #
        for name, attr_a in attrs_a.items():
            attr_b = attrs_b.get(name, None)
            if attr_b is not None:
                if not self.__equal(attr_a.Get(time_code), attr_b.Get(time_code), attr_a.GetTypeName()):
                    return True

        return False

    def update(self, prim: Usd.Prim) -> None:
        self.camera_prim = self._get_camera_prim(prim)

    def create(self, valid: bool = True) -> None:
        super().create(valid)
        if valid:
            if self.__viewport_widget:
                self.camera_path = self.__viewport_widget.camera_path.pathString
            else:
                self.camera_path = get_active_viewport_camera_string()

    def recall(self, prim: Usd.Prim) -> None:
        if not self.valid:
            return

        self.camera_prim = self._get_camera_prim(prim)
        PERSP_CAM_PATH = "/OmniverseKit_Persp"
        usd_context = omni.usd.get_context()
        stage = usd_context.get_stage()
        persp_cam_prim = stage.GetPrimAtPath(PERSP_CAM_PATH)

        if not persp_cam_prim:
            return

        edit_context = Usd.EditContext(stage, Usd.EditTarget(stage.GetSessionLayer()))
        with edit_context:
            for attr in self.camera_prim.GetAttributes():
                attr_name = attr.GetName()
                if _should_skip_camera_attr(attr_name):
                    continue
                if attr_name == LOCK_CAMERA_ATTR:
                    self._save_attribute(persp_cam_prim, attr_name, False, attr.GetTypeName())
                else:
                    self._save_attribute(persp_cam_prim, attr_name, attr.Get(), attr.GetTypeName())

        viewport_api = get_active_viewport()
        if viewport_api:
            viewport_api.camera_path = PERSP_CAM_PATH

    def save_to_usd(self, prim: Usd.Prim) -> None:
        self._save_attribute(prim, WAYPOINT_ATTR_CAMERA_PATH, self.camera_path, Sdf.ValueTypeNames.String)

        # Clone camera prim
        self.camera_prim = self._get_camera_prim(prim)
        if self.camera_prim is None:
            return
        stage = omni.usd.get_context().get_stage()
        if stage is None:
            return
        active_camera_prim = stage.GetPrimAtPath(self.camera_path)
        if active_camera_prim is None:
            carb.log_warn(f"Viewport waypoint: Failed to get the active camera {self.camera_path}.")
            return

        timeline = omni.timeline.get_timeline_interface()
        time_code = timeline.get_current_time() * timeline.get_time_codes_per_seconds()
        for attr in active_camera_prim.GetAttributes():
            attr_name = attr.GetName()
            if _should_skip_camera_attr(attr_name):
                continue
            if attr.Get(time_code) is not None:
                if attr_name == LOCK_CAMERA_ATTR:
                    self._save_attribute(self.camera_prim, attr_name, False, attr.GetTypeName())
                else:
                    self._save_attribute(self.camera_prim, attr_name, attr.Get(time_code), attr.GetTypeName())

        # Used to display waypoint prim icon for omni.kit.prim.icon
        if self.__viewport_widget:
            camera_state = ViewportCameraState(self.camera_path, viewport=self.__viewport_widget)
        else:
            camera_state = ViewportCameraState(self.camera_path)
        camera_position = camera_state.position_world
        self._save_attribute(prim, WAYPOINT_ATTR_ICON_POSITION, camera_position, Sdf.ValueTypeNames.Float3)

    def load_from_usd(self, prim: Usd.Prim) -> bool:
        camera_path_attr = prim.GetAttribute(WAYPOINT_ATTR_CAMERA_PATH)
        if camera_path_attr:
            self.camera_path = camera_path_attr.Get()
        else:
            camera_name_attr = prim.GetAttribute(WAYPOINT_ATTR_CAMERA_NAME)
            if camera_name_attr:
                self.camera_path = camera_name_attr.Get()
            else:
                self.camera_path = ""
                self.camera_prim = None
                self.valid = False
                return False

        self.camera_prim = self._get_camera_prim(prim)
        self.valid = True
        return True

    def _get_camera_prim(self, root_prim: Usd.Prim) -> Usd.Prim:
        root_prim_path = root_prim.GetPath().pathString
        if len(self.camera_path) > 0:
            camera_path = root_prim_path + "/" + self._get_camera_name()
        else:
            camera_path = root_prim_path + "/camera"

        return self._get_prim(camera_path)

    def _get_camera_name(self) -> str:
        return self.camera_path.split("/")[-1]

    # OM-53986: Remove defualt prim type of "Camera"
    def _get_prim(self, path: str, type_name=None) -> Usd.Prim:
        stage = omni.usd.get_context().get_stage()
        if stage is None:
            return None
        if path:
            prim = stage.GetPrimAtPath(path)
        else:
            prim = None
        if not prim:
            if type_name:
                prim = stage.DefinePrim(path, type_name)
            else:
                prim = create_data_only_prim(stage, path)
            if not prim:
                carb.log_error("Failed to create prim at '{path}'!")
                return None
        return prim

    def _filter_attributes(self, attributes: List[Usd.Attribute], time_code) -> List[Usd.Attribute]:
        """
        Filter attributes which:
        - Has valid value
        - Has valid xformOp
        """
        filtered: List[Usd.Attribute] = []
        xformop_order = []
        for attr in attributes:
            if not attr:
                continue
            # print(f"{self.__class__.__name__}._filter_attributes: {attr=} {time_code=}")
            if attr_name := attr.GetName():
                if _should_skip_camera_attr(attr_name):
                    continue

            attr_value = attr.Get(time_code)
            if attr_value is not None:
                filtered.append(attr)
                if attr_name == "xformOpOrder":
                    xformop_order = attr_value
        if xformop_order:
            filtered = [
                attr
                for attr in filtered
                if not attr.GetName().startswith("xformOp:") or attr.GetName() in xformop_order
            ]
        return filtered

    def __equal(self, active, current, type) -> bool:
        if type == Sdf.ValueTypeNames.Float3 or type == Sdf.ValueTypeNames.Double3:
            if isinstance(active, Gf.Vec3f):
                active = Gf.Vec3d(active)
            if isinstance(current, Gf.Vec3f):
                current = Gf.Vec3d(current)
            try:
                return Gf.IsClose(active, current, 1e-5)
            except:  # pragma: no cover
                return active == current
        else:
            return active == current
