# SPDX-FileCopyrightText: Copyright (c) 2018-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

import math

import carb
import carb.events
import carb.profiler
import carb.settings
import carb.tokens
import omni.kit.app
import omni.usd
import usdrt
from carb.eventdispatcher import get_eventdispatcher
from pxr import Gf, Sdf, Usd, UsdGeom, UsdShade
from usdrt import Gf as usdrt_Gf

ATTR_SECTION_TRANSFORM = "xformOp:transform"
TELEPORT_TOOL_PATH = "/TeleportTools"
TELEPORT_PRIM_PATH = "/Teleport_Tool_Object"
VIEW_LAYER_EXT = ".view.usd"
HIDE_IN_STAGE_WINDOW = "hide_in_stage_window"
NO_DELETE = "no_delete"
M_PI = 3.14159265358979323846
TELE_WIDGET_SCALE = "/exts/omni.kit.tool.teleport/widgetScale"
PERSISTENT_SETTINGS_PREFIX = "/persistent"
PERSISTENT_TELE_WIDGET_SCALE = PERSISTENT_SETTINGS_PREFIX + TELE_WIDGET_SCALE
GIZMO_VIS_CHANGED_EVT = "teleport.tool.gizmo_vis.CHANGED"
GIZMO_VIS_EVT_PAYLOAD_KEY = "visibility"
MAX_SLOPE_ANGLE_PATH = "/exts/omni.kit.tool.teleport/max_slope_angle"
MAX_SLOPE_ANGLE_DEF = 30.0


class WidgetAlignment:
    X = "X"
    Y = "Y"
    Z = "Z"


def setLocalTransformFromWorldTransformMatrix(
    prim, mtx, timeCode=Usd.TimeCode.Default(), skipEqualSetForTimeSample=False
):  # pragma: no cover -- currently unused
    if not prim:
        return
    cmd = omni.usd.commands.TransformPrimCommand(path=prim.GetPath(), new_transform_matrix=mtx)
    cmd.do()


def get_stage_up(stage):
    up_axis = UsdGeom.GetStageUpAxis(stage)
    if up_axis == "X":
        up = Gf.Vec3d.XAxis()
    elif up_axis == "Y":
        up = Gf.Vec3d.YAxis()
    else:
        up = Gf.Vec3d.ZAxis()
    return up


def get_widget_world_scale(widget_scale: float, units_scale: float) -> float:
    """World-scale multiplier applied to the referenced gizmo prims.

    The gizmo geometry is authored in centimeters, but a USD reference keeps the referenced
    coordinates as-is and renders them at the HOST stage's metersPerUnit. `units_scale`
    (= 0.01 / stage_metersPerUnit) converts that centimeter geometry back to a constant physical
    size, so the gizmo looks the same on a metersPerUnit=1.0 stage as on a centimeter one. It is
    combined with the user-facing `widgetScale` setting.
    """
    return widget_scale * units_scale


def get_raycast_offset(units_scale: float = 1.0) -> float:
    """Lift-off, in stage units, used to keep the gizmo from making the surface it overlays
    unpickable. Authored as 1cm, so it is converted to stage units like every other size constant.
    """
    return 1e-2 * units_scale


class TeleportWidget:
    _teleport_widget_instance = None

    def __init__(self, model=None):
        self._direction_angle = 0
        self._settings = carb.settings.get_settings()
        self._usd_context = omni.usd.get_context()
        # Shared source of the stage-units conversion. Read live (rather than cached) so the widget
        # picks up the model's metersPerUnit re-query; falls back to 1.0 (centimeter behaviour) when
        # no model is wired in.
        self._model = model
        self._tool_path = None
        self._widget_prim = None
        self._beam_prim = None
        self._widget_file = ""
        self._beam_file = ""
        self._ring_rotation = usdrt.Gf.Quatf(1.0)
        self._ring_original_orient = usdrt.Gf.Quatf(1.0)  # needed to correct usdrt worldOrient
        self._denyring_rotation = usdrt.Gf.Quatf(1.0)
        self._denyring_original_orient = usdrt.Gf.Quatf(1.0)  # needed to correct usdrt worldOrient
        self._pointer_rotation = usdrt.Gf.Quatf(1.0)
        self._visual_up = None
        self._slope_angle = 0
        self._pointer_transform_attr = None
        self._pointer_prim = None
        self._pointer_rt_prim = None
        self._ring_prim = None
        self._ring_rt_prim = None
        self._denyring_prim = None
        self._denyring_rt_prim = None
        self._mesh_transform_attr = None
        self._mesh_prim = None
        self._mesh_rt_prim = None
        self._position = None
        self._is_init = False

        self._max_slope_angle = self._settings.get(MAX_SLOPE_ANGLE_PATH)
        if self._max_slope_angle is None:
            self._max_slope_angle = MAX_SLOPE_ANGLE_DEF

        usd = omni.usd.get_context()
        self._stage_event_sub = [
            get_eventdispatcher().observe_event(
                observer_name="omni.kit.tool.teleport:TeleportWidget",
                event_name=usd.stage_event_name(event),
                on_event=func,
            )
            for event, func in (
                (omni.usd.StageEventType.OPENED, lambda _: self._on_stage_opened()),
                (omni.usd.StageEventType.CLOSED, lambda _: self._on_stage_close()),
            )
        ]

        self._gizmo_vis_sub = get_eventdispatcher().observe_event(
            event_name=GIZMO_VIS_CHANGED_EVT, on_event=self._on_gizmo_vis_changed_outside
        )
        # self.refresh()

        TeleportWidget._teleport_widget_instance = self

    def _get_max_slope_angle(self):
        self._max_slope_angle = self._settings.get(MAX_SLOPE_ANGLE_PATH)
        if self._max_slope_angle is None:
            self._max_slope_angle = MAX_SLOPE_ANGLE_DEF
        return self._max_slope_angle

    def is_init(self):
        return self._is_init

    @property
    def units_scale(self) -> float:
        """Factor converting a centimeter-authored constant into stage units (1.0 on a cm stage)."""
        return self._model.units_scale if self._model else 1.0

    def get_prim_path(self):  # pragma: no cover -- currently unused
        return self._widget_prim.GetPath()

    def get_prim(self):  # pragma: no cover -- currently unused
        return self._widget_prim

    # just used for test
    def unbind_material(self):
        self.unbind_prim_material(self._mesh_prim)
        self.unbind_prim_material(self._ring_prim)
        self.unbind_prim_material(self._denyring_prim)
        self.unbind_prim_material(self._pointer_prim)

    def unbind_prim_material(self, prim):
        if prim:
            binding_api = UsdShade.MaterialBindingAPI(prim)
            if binding_api:
                binding_api.UnbindAllBindings()

    def set_widget_usd_file(self, file_path=None):
        if file_path:
            self._widget_file = file_path
        if self._widget_prim and self._widget_file:
            stage = self._usd_context.get_stage()
            self._teleport_layer = stage.GetSessionLayer()
            with Usd.EditContext(stage, self._teleport_layer):
                self._widget_prim.GetReferences().AddReference(self._widget_file)
            self.parse_ring_and_pointer()

    def parse_ring_and_pointer(self):
        stage = self._usd_context.get_stage()
        self._teleport_layer = stage.GetSessionLayer()
        with Usd.EditContext(stage, self._teleport_layer):
            for childPrim in self._widget_prim.GetChildren():
                if childPrim.GetName() == "teleport_mesh":
                    self._mesh_transform_attr = childPrim.GetAttribute(ATTR_SECTION_TRANSFORM)
                    self._mesh_prim = childPrim
                    self._mesh_rt_prim = None
                    self._usd_context.set_pickable(self._mesh_prim.GetPrimPath().pathString, False)

                if childPrim.GetName() == "teleport_ring":
                    self._ring_prim = childPrim
                    self._ring_rt_prim = None
                    self._ring_original_orient = usdrt.Gf.Quatf(1.0)

                if childPrim.GetName() == "deny_ring":
                    self._denyring_prim = childPrim
                    self._denyring_rt_prim = None
                    self._denyring_original_orient = usdrt.Gf.Quatf(1.0)

                if childPrim.GetName() == "pointer":
                    self._pointer_transform_attr = childPrim.GetAttribute(ATTR_SECTION_TRANSFORM)
                    self._pointer_prim = childPrim
                    self._pointer_rt_prim = None
                    self._usd_context.set_pickable(self._pointer_prim.GetPrimPath().pathString, False)

    def set_beam_usd_file(self, file_path=None):
        if file_path:
            self._beam_file = file_path
        if self._beam_prim and self._beam_file:
            self._beam_prim.GetReferences().AddReference(self._beam_file)

    @carb.profiler.profile
    def set_direction_and_up(self, dir: Gf.Vec3d, visual_up: Gf.Vec3d, use_ring_manipulator: bool = False):
        stage = self._usd_context.get_stage()
        up = get_stage_up(stage)
        up_axis = UsdGeom.GetStageUpAxis(stage)

        self._slope_angle = Gf.RadiansToDegrees(math.acos(Gf.Dot(visual_up, up)))
        if not use_ring_manipulator:  # pragma: no cover -- currently unused
            visible = self._slope_angle <= self._get_max_slope_angle()
            if not visible:
                side = Gf.Cross(up, visual_up).GetNormalized()
                if Gf.IsClose(side, Gf.Vec3d(0), 1e-6):
                    side = Gf.Vec3d().XAxis() if up_axis == UsdGeom.Tokens.y else Gf.Vec3d().YAxis()
                self.show_deny(visible=True)
            else:
                side = Gf.Cross(visual_up, dir).GetNormalized()
                if Gf.IsClose(side, Gf.Vec3d(0), 1e-6):
                    side = Gf.Cross(up, dir).GetNormalized()
                if Gf.IsClose(side, Gf.Vec3d(0), 1e-6):
                    side = Gf.Vec3d().XAxis() if up_axis == UsdGeom.Tokens.y else Gf.Vec3d().YAxis()
                self.show_deny(visible=False)

            front = Gf.Cross(side, visual_up).GetNormalized()

            rotation_mtx = Gf.Matrix3d(1)
            rotation_mtx.SetRow(0, side)
            rotation_mtx.SetRow(1, visual_up)
            rotation_mtx.SetRow(2, front)

            rotation = self._pxr_quat_to_usdrt_quat(rotation_mtx.ExtractRotation().GetQuat())
            if self._denyring_rt_prim:
                self._denyring_rotation = rotation * self._denyring_original_orient
            if self._ring_rt_prim:
                self._ring_rotation = rotation * self._ring_original_orient
            if self._pointer_rt_prim:
                self._pointer_rotation = rotation * self._pxr_quat_to_usdrt_quat(Gf.Rotation(up, 90).GetQuat())
            self._visual_up = visual_up

    def can_teleport(self) -> bool:
        return self._slope_angle <= self._get_max_slope_angle()

    def update_pos(self):  # pragma: no cover -- currently unused
        if self._delay_init_rt_prims():
            return

        # Add a small offset for raycast
        # Otherwise if the ring/denyring is not pickable, it affects the surface it overlays and will make them
        # unpickable too and picking ray penetrates the surface.
        position = self._position + self._visual_up * get_raycast_offset(self.units_scale)
        position = usdrt.Gf.Vec3d(position[0], position[1], position[2])

        if self._ring_rt_prim:
            xformable = usdrt.Rt.Xformable(self._ring_rt_prim)
            xformable.GetWorldOrientationAttr().Set(self._ring_rotation)
            xformable.GetWorldPositionAttr().Set(position)

        if self._denyring_rt_prim:
            xformable = usdrt.Rt.Xformable(self._denyring_rt_prim)
            xformable.GetWorldOrientationAttr().Set(self._denyring_rotation)
            xformable.GetWorldPositionAttr().Set(position)

        if self._mesh_rt_prim:
            xformable = usdrt.Rt.Xformable(self._mesh_rt_prim)
            xformable.GetWorldPositionAttr().Set(position)

        if self._pointer_rt_prim:
            xformable = usdrt.Rt.Xformable(self._pointer_rt_prim)
            xformable.GetWorldOrientationAttr().Set(self._pointer_rotation)
            xformable.GetWorldPositionAttr().Set(position)

    def destroy(self):  # pragma: no cover -- currently unused
        self.remove_widget()
        self._stage_event_sub = None
        self._settings = None
        self._usd_context = None
        self._model = None
        TeleportWidget._teleport_widget_instance = None

    @staticmethod
    def get_instance():
        return TeleportWidget._teleport_widget_instance

    def clear(self):
        self._stage = None
        self._widget_prim = None

    def refresh(self):
        self.clear()
        stage = self._usd_context.get_stage()
        if stage:
            self._on_stage_open()

    def remove_widget(self):
        if not self._usd_context:
            return
        stage = self._usd_context.get_stage()
        if self._tool_path and stage:
            self._teleport_layer = stage.GetSessionLayer()
            with Usd.EditContext(stage, self._teleport_layer):
                if stage.GetPrimAtPath(self._tool_path):
                    stage.RemovePrim(self._tool_path)

    def set_widget_position(self, position):
        self._position = position

    def get_teleport_widget_prim(self, create_if_not_exist=False):
        if self._widget_prim:
            return self._widget_prim

        stage = self._usd_context.get_stage()
        defaultPath = ""

        teleport_tool_path = defaultPath + TELEPORT_TOOL_PATH
        teleport_prim_path = teleport_tool_path + TELEPORT_PRIM_PATH
        self._teleport_layer = stage.GetSessionLayer()
        with Usd.EditContext(stage, self._teleport_layer):
            self._widget_prim = stage.GetPrimAtPath(teleport_prim_path)
            if not self._widget_prim and create_if_not_exist:
                self._widget_prim = stage.DefinePrim(teleport_prim_path, "Xform")

            if not self._widget_prim:
                return None

            xformable = UsdGeom.Xformable(self._widget_prim)
            visibilityAttr = xformable.GetVisibilityAttr()
            visibilityAttr.Set(UsdGeom.Tokens.invisible)
            self._teleport_transform_attr = self._widget_prim.GetAttribute(ATTR_SECTION_TRANSFORM)
            if not self._teleport_transform_attr:
                # init section prim
                xformable.AddXformOp(UsdGeom.XformOp.TypeTransform)
                self._teleport_transform_attr = self._widget_prim.CreateAttribute(
                    ATTR_SECTION_TRANSFORM, Sdf.ValueTypeNames.Matrix4d
                )
                self._teleport_transform_attr.Set(Gf.Matrix4d())

            self._tool_path = teleport_tool_path
            tool_prim = stage.GetPrimAtPath(teleport_tool_path)
            if tool_prim:
                tool_prim.SetMetadata(HIDE_IN_STAGE_WINDOW, True)
                tool_prim.SetMetadata(NO_DELETE, True)
            self._widget_prim.SetMetadata(HIDE_IN_STAGE_WINDOW, True)
            self._widget_prim.SetMetadata(NO_DELETE, True)

            UsdGeom.PrimvarsAPI(self._widget_prim).CreatePrimvar("doNotCastShadows", Sdf.ValueTypeNames.Bool).Set(False)

        return self._widget_prim

    def hide_all(self):
        stage = self._usd_context.get_stage()
        if not stage:
            return
        self._teleport_layer = stage.GetSessionLayer()
        with Usd.EditContext(stage, self._teleport_layer):
            if not self._widget_prim:
                return
            imageable = UsdGeom.Imageable(self._widget_prim)
            if imageable:
                imageable.MakeInvisible()
            if self._denyring_prim:
                imageable = UsdGeom.Imageable(self._denyring_prim)
                if imageable:
                    imageable.MakeInvisible()

    def show(self, visible, init_transform=False):
        stage = self._usd_context.get_stage()
        if not stage:
            return
        self._teleport_layer = stage.GetSessionLayer()
        with Usd.EditContext(stage, self._teleport_layer):
            if not self._widget_prim:
                return
            imageable = UsdGeom.Imageable(self._widget_prim)
            if imageable:
                if visible:
                    imageable.MakeVisible()
                    self._usd_context.set_pickable(self._widget_prim.GetPrimPath().pathString, False)
                else:
                    imageable.MakeInvisible()
            if self._denyring_prim:
                imageable = UsdGeom.Imageable(self._denyring_prim)
                if imageable:
                    imageable.MakeInvisible()

    def show_deny(self, visible):  # pragma: no cover -- currently unused
        stage = self._usd_context.get_stage()
        if not stage:
            return
        self._teleport_layer = stage.GetSessionLayer()
        with Usd.EditContext(stage, self._teleport_layer):
            if not self._widget_prim:
                return
            imageable = UsdGeom.Imageable(self._ring_prim)
            if imageable:
                if visible:
                    imageable.MakeInvisible()
                else:
                    imageable.MakeVisible()
                    # set_pickable has to be called every time mesh visibility changes
                    self._usd_context.set_pickable(self._ring_prim.GetPrimPath().pathString, False)
            if self._denyring_prim:
                imageable = UsdGeom.Imageable(self._denyring_prim)
                if imageable:
                    if visible:
                        imageable.MakeVisible()
                        # set_pickable has to be called every time mesh visibility changes
                        self._usd_context.set_pickable(self._denyring_prim.GetPrimPath().pathString, False)
                    else:
                        imageable.MakeInvisible()

    def _on_gizmo_vis_changed_outside(self, *args) -> None:
        # OM-99523 - Hide teleport gizmo during "Google Maps" style mouse look.
        vis = args[0][GIZMO_VIS_EVT_PAYLOAD_KEY]
        self.show(vis)

    def _on_stage_opened(self):
        """Called when opening/closing stage"""
        pass
        # self._on_stage_open()

    def _on_stage_open(self):
        stage = self._usd_context.get_stage()

        self._teleport_layer = stage.GetSessionLayer()
        with Usd.EditContext(stage, self._teleport_layer):
            self.get_teleport_widget_prim(create_if_not_exist=True)
            self.set_widget_usd_file(self._widget_file)
            self.set_beam_usd_file()
            self._is_init = True

    def _on_stage_close(self):
        self.remove_widget()
        self._is_init = False

    # delayed initialization.
    # This is needed for FSD. If these steps are done in parse_ring_and_pointer, FSD won't hold correct
    # reference to ring and denyring
    def _delay_init_rt_prims(self) -> bool:  # pragma: no cover -- currently unused
        if (
            (self._ring_prim and self._ring_rt_prim is None)
            or (self._denyring_prim and self._denyring_rt_prim is None)
            or (self._mesh_prim and self._mesh_rt_prim is None)
            or (self._pointer_prim and self._pointer_rt_prim is None)
        ):
            rt_stage = usdrt.Usd.Stage.Attach(self._usd_context.get_stage_id())

            widget_scale = self._settings.get(PERSISTENT_TELE_WIDGET_SCALE)
            if widget_scale is None:
                widget_scale = self._settings.get(TELE_WIDGET_SCALE)
            # Fold the stage-units conversion into the user widgetScale so the centimeter-authored
            # gizmo renders at a constant physical size on non-centimeter stages.
            scale = get_widget_world_scale(widget_scale, self.units_scale)

            if self._ring_prim:
                self._ring_rt_prim = rt_stage.GetPrimAtPath(self._ring_prim.GetPrimPath().pathString + "/ring")
                xformable = usdrt.Rt.Xformable(self._ring_rt_prim)
                xformable.SetWorldXformFromUsd()
                self._ring_original_orient = xformable.GetWorldOrientationAttr().Get()
                scale_attr = xformable.GetWorldScaleAttr()
                scale_attr.Set(scale_attr.Get() * scale)

            if self._denyring_prim:
                if self._denyring_rt_prim is None:
                    rt_stage = usdrt.Usd.Stage.Attach(self._usd_context.get_stage_id())
                    self._denyring_rt_prim = rt_stage.GetPrimAtPath(
                        self._denyring_prim.GetPrimPath().pathString + "/ring"
                    )

                    xformable = usdrt.Rt.Xformable(self._denyring_rt_prim)
                    xformable.SetWorldXformFromUsd()
                    self._denyring_original_orient = xformable.GetWorldOrientationAttr().Get()
                    scale_attr = xformable.GetWorldScaleAttr()
                    scale_attr.Set(scale_attr.Get() * scale)

            if self._mesh_prim:
                if self._mesh_rt_prim is None:
                    self._mesh_rt_prim = rt_stage.GetPrimAtPath(self._mesh_prim.GetPrimPath().pathString)
                    xformable = usdrt.Rt.Xformable(self._mesh_rt_prim)
                    xformable.SetWorldXformFromUsd()
                    scale_attr = xformable.GetWorldScaleAttr()
                    scale_attr.Set(scale_attr.Get() * scale)

            if self._pointer_prim:
                if self._pointer_rt_prim is None:
                    self._pointer_rt_prim = rt_stage.GetPrimAtPath(self._pointer_prim.GetPrimPath().pathString)
                    xformable = usdrt.Rt.Xformable(self._pointer_rt_prim)
                    xformable.SetWorldXformFromUsd()
                    scale_attr = xformable.GetWorldScaleAttr()
                    scale_attr.Set(scale_attr.Get() * scale)
            return True

        return False

    def _pxr_quat_to_usdrt_quat(self, quat, usdrt_quat_type=usdrt_Gf.Quatf):  # pragma: no cover -- currently unused
        img = quat.GetImaginary()
        return usdrt_quat_type(quat.GetReal(), img[0], img[1], img[2])
