# Copyright (c) 2023, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

__all__ = ["MeasurePrim", "MeasureSubItem"]

from typing import List, Optional

import carb.profiler
import omni.kit.commands
import omni.kit.commands as cmds
import omni.kit.undo
import omni.usd as ou
from omni import ui
from omni.kit.viewport.utility import get_active_viewport
from pxr import Gf, Sdf, Usd, UsdGeom

from ..common import MeasureMode, Precision
from ._measure_compute import COMPUTE_MAP, MeasureCompute
from ._measure_payload import MeasurePayload


class MeasureSubItem(ui.AbstractItem):
    def __init__(self, name: str, value, uuid_ref: int, path_ref: str):
        super().__init__()
        self.name = name
        self.value = value
        self.uuid = uuid_ref
        self.path = path_ref
        self.visible = True  # Required


class MeasurePrim(ui.AbstractItem):
    def __init__(self, prim_path: str, payload: MeasurePayload):
        super().__init__()

        self.__ctx = ou.get_context()
        self.__stage = self.__ctx.get_stage()
        self.__layer = self.__stage.GetRootLayer()

        self.__payload: MeasurePayload = payload

        self._prim: "Usd.Prim" = self.__stage.GetPrimAtPath(prim_path)

        self._mode: MeasureMode = payload.tool_mode
        self._compute: MeasureCompute = self._set_compute(self._mode)
        self._children: List[MeasureSubItem] = []

        if not self._prim.IsValid():
            self.__create_prim(prim_path)

        self.__update_children()

    @property
    def children(self) -> List[MeasureSubItem]:
        return self._children

    @property
    def path(self):
        return self._prim.GetPrimPath()

    @property
    def uuid(self) -> int:
        return self.__payload.uuid

    @property
    def visible(self) -> bool:
        return self.__payload.visible

    @property
    def name(self) -> str:
        return self.__payload.name

    @name.setter
    def name(self, value: str) -> None:
        self.__payload.name = value
        self.set_attribute("measure:prop:name", value, Sdf.ValueTypeNames.String)

    @property
    def mode(self) -> MeasureMode:
        return self._mode

    @property
    def payload(self) -> MeasurePayload:
        return self.__payload

    @staticmethod
    def from_prim(prim_path: str) -> Optional["MeasurePrim"]:
        ctx = ou.get_context()
        prim = ctx.get_stage().GetPrimAtPath(prim_path)

        if prim and prim.HasAttribute("measure:uuid"):
            payload: Optional[MeasurePayload] = MeasurePayload.from_prim(prim)
            if payload is None:
                return None
            m_prim: "MeasurePrim" = MeasurePrim(prim_path, payload)
            return m_prim

        return None

    def __create_prim(self, prim_path: str) -> "Usd.Prim":
        with omni.kit.undo.group():
            cmds.execute("CreatePrimCommand", prim_type="", prim_path=prim_path)
            self._prim = self.__stage.GetPrimAtPath(prim_path)
            self.__payload.prim = self._prim
            MeasurePayload.write_prim_paths(self._prim, self.__payload.prim_paths)

            # Populate Name
            if self.__payload.name == "":
                self.__payload.name = self._prim.GetName()
            compute_data = self._compute.execute(self.__payload)
            self.__payload.update_from_compute(compute_data)
            self._load_payload(self.__payload)
            self.set_attribute("measure:prop:visible", self.__payload.visible, Sdf.ValueTypeNames.Bool)
            self.hide_measure_root()

    def hide_measure_root(self):
        parent_prim = self._prim.GetParent()
        parent_name = parent_prim.GetName()
        if parent_name == "Viewport_Measure":
            parent_prim.SetMetadata("hide_in_stage_window", True)

    @carb.profiler.profile
    def _load_payload(self, payload: MeasurePayload):
        # Core
        self.set_attribute("measure:uuid", payload.uuid, Sdf.ValueTypeNames.Int)
        # Metadata
        MeasurePayload.write_prim_paths(self._prim, payload.prim_paths)
        self.set_attribute("measure:meta:local_points", payload.points, Sdf.ValueTypeNames.Vector3dArray)
        self.set_attribute("measure:meta:tool_mode", payload.tool_mode.value, Sdf.ValueTypeNames.Int)
        self.set_attribute("measure:meta:tool_sub_mode", payload.tool_sub_mode, Sdf.ValueTypeNames.Int)
        # Compute Data
        self.set_attribute("measure:compute:points", payload.computed_points, Sdf.ValueTypeNames.Vector3dArray)
        self.set_attribute("measure:compute:primary", payload.primary_value, Sdf.ValueTypeNames.Double)
        self.set_attribute("measure:compute:secondary", payload.secondary_values, Sdf.ValueTypeNames.DoubleArray)
        # User Properties
        self.set_attribute("measure:prop:name", payload.name, Sdf.ValueTypeNames.String)
        self.set_attribute("measure:prop:axis_display", payload.axis_display, Sdf.ValueTypeNames.Token)
        self.set_attribute("measure:prop:unit", payload.unit_type, Sdf.ValueTypeNames.Token)
        self.set_attribute("measure:prop:precision", payload.precision, Sdf.ValueTypeNames.Token)
        self.set_attribute("measure:prop:label_size", payload.label_size, Sdf.ValueTypeNames.Token)
        self.set_attribute("measure:prop:label_color", payload.label_color, Sdf.ValueTypeNames.Color4f)

        self.__update_children()

    # TODO: This object creation can be simplified and have cleaner approach
    @carb.profiler.profile
    def __update_children(self):
        def name_mapping(tool_mode: MeasureMode):
            if tool_mode not in [MeasureMode.POINT_TO_POINT, MeasureMode.ANGLE]:
                return None
            return ["X", "Y", "Z"] if tool_mode == MeasureMode.POINT_TO_POINT else ["Secondary Angle"]

        self._children.clear()

        if self.__payload.tool_mode == MeasureMode.DIAMETER:
            return

        name_map = name_mapping(self.__payload.tool_mode)
        precision = list(Precision).index(self.__payload.precision.value)
        vals = self.payload.secondary_values
        val_type = "°" if self.__payload.tool_mode == MeasureMode.ANGLE else f"{self.__payload.unit_type.value}"

        for idx in range(len(vals)):
            title = str(idx) if name_map is None else name_map[idx]
            self._children.append(MeasureSubItem(title, f"{vals[idx]:.{precision}f} {val_type}", self.uuid, self.path))

    @carb.profiler.profile
    def refresh_payload(self):
        if not self._prim:
            return

        # Visibility is session-only view state kept in memory so toggling it never edits the stage;
        # carry it over rather than re-reading the value stored on the prim at creation.
        visible = self.__payload.visible
        self.__payload = MeasurePayload.from_prim(self._prim)
        self.__payload.visible = visible
        compute_data = self._compute.execute(self.__payload)
        self.__payload.update_from_compute(compute_data)
        self._load_payload(self.__payload)

    def get_attribute(self, attr_name: str, default=None):
        if not self._prim:
            return None

        if self._prim.HasAttribute(attr_name):
            attribute = self._prim.GetAttribute(attr_name)
            value = attribute.Get()

            return default if value is None else value

        return default

    def set_attribute(self, attr_name: str, value, type_name: Sdf.ValueTypeNames) -> None:
        if not self._prim:
            return

        if not (attr := self._prim.GetAttribute(attr_name)):
            # Create the attr and check if it is in need of token-setting
            attr = self._prim.CreateAttribute(attr_name, typeName=type_name)
            if type_name == Sdf.ValueTypeNames.Token:
                tokens = [item.name for item in type(value)]
                attr.SetMetadata("allowedTokens", tokens)

        if attr:
            value = value.name if type_name == Sdf.ValueTypeNames.Token else value
            if attr.Get() != value:
                cmds.create(
                    "ChangePropertyCommand",
                    prop_path=attr.GetPath(),
                    value=value,
                    prev=None,
                ).do()

    def set_mode(self, mode: MeasureMode) -> None:
        self._mode = mode
        self._compute = COMPUTE_MAP[mode]()

    def _set_compute(self, mode: MeasureMode) -> MeasureCompute:
        return COMPUTE_MAP[mode]()

    def frame(self) -> bool:
        viewport_api = get_active_viewport()
        if not viewport_api:
            return False

        points = self.get_attribute("measure:compute:points")
        if not points or len(points) <= 0:
            return False

        center = Gf.Vec3d(points[0])
        dx = 0.0
        dy = 0.0
        dz = 0.0
        if len(points) > 1:
            point_max = Gf.Vec3d(points[0])
            point_min = Gf.Vec3d(points[0])
            for i in range(len(points) - 1):
                point = points[i + 1]
                point_max[0] = max(point_max[0], point[0])
                point_max[1] = max(point_max[1], point[1])
                point_max[2] = max(point_max[2], point[2])
                point_min[0] = min(point_min[0], point[0])
                point_min[1] = min(point_min[1], point[1])
                point_min[2] = min(point_min[2], point[2])
            center[0] = (point_max[0] + point_min[0]) / 2.0
            center[1] = (point_max[1] + point_min[1]) / 2.0
            center[2] = (point_max[2] + point_min[2]) / 2.0
            dx = (point_max[0] - point_min[0]) / 2.0
            dy = (point_max[1] - point_min[1]) / 2.0
            dz = (point_max[2] - point_min[2]) / 2.0

        bounds = [
            Gf.Vec3d(center[0] - dx, center[1] - dy, center[2] - dz),
            Gf.Vec3d(center[0] + dx, center[1] + dy, center[2] + dz),
        ]

        stage = viewport_api.stage
        cam_path = viewport_api.camera_path
        if not stage or not cam_path:
            return False
        cam_prim = stage.GetPrimAtPath(cam_path)
        if not cam_prim:
            return False

        look_through = None
        # Loop over all targets (should really be only one) and see if we can get a valid UsdGeom.Imageable
        for target in cam_prim.GetRelationship("omni:kit:viewport:lookThrough:target").GetForwardedTargets():
            target_prim = stage.GetPrimAtPath(target)
            if not target_prim:
                continue
            if UsdGeom.Imageable(target_prim):
                look_through = target_prim
                break

        try:
            omni.kit.undo.begin_group()
            resolution = viewport_api.resolution
            omni.kit.commands.execute(
                "FramePointsCommand",
                prim_to_move=cam_path if not look_through else look_through.GetPath(),
                points=bounds,
                time_code=viewport_api.time,
                usd_context_name=viewport_api.usd_context_name,
                aspect_ratio=resolution[0] / resolution[1],
            )
        finally:
            omni.kit.undo.end_group()

        return True
