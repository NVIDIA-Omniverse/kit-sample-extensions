# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
import asyncio
import math
from typing import Sequence

import carb.events
import carb.input
import omni.appwindow
import omni.kit.app
import omni.kit.commands
import omni.kit.viewport.utility as vp_util
import omni.usd
from omni import ui
from omni.kit.app import register_event_alias
from omni.kit.viewport.utility.camera_state import ViewportCameraState as VpCamera
from pxr import Gf, Sdf, Usd, UsdGeom

from .teleport_model import TeleportModel
from .teleport_widget import TeleportWidget
from .utils import get_data_path
from .widget_geometry import RingGeometry

MAX_RAYCAST_DIST = 10000000.0
TELE_EYE_HEIGHT = "/exts/omni.kit.tool.teleport/eyeHeight"
TELE_BEAM_VISIBLE = "/exts/omni.kit.tool.teleport/beamVisible"
TELE_USE_WORLD_UP = "/exts/omni.kit.tool.teleport/useWorldUp"
TELE_BASIC_GIZMO = "/exts/omni.kit.tool.teleport/basicGizmo"
TELE_SIMPLE_CAMERA = "/exts/omni.kit.tool.teleport/simple_camera"
TELEPORT_TOOL_PATH = "/TeleportTools"
CURRENT_TOOL_PATH = "/app/viewport/currentTool"
PERSISTENT_SETTINGS_PREFIX = "/persistent"
PERSISTENT_TELE_EYE_HEIGHT = PERSISTENT_SETTINGS_PREFIX + TELE_EYE_HEIGHT
RING_RADIUS = 95

TELE_ENABLED_GLOBAL_EVENT: str = "omni.kit.tool.teleport.TOOL_ENABLED"
TELE_ENABLED_EVENT: int = carb.events.type_from_string(TELE_ENABLED_GLOBAL_EVENT)
register_event_alias(TELE_ENABLED_EVENT, TELE_ENABLED_GLOBAL_EVENT)


class Teleport:
    """A class for interactive teleportation in the omni.kit.tool.teleport extension.

    This class enables users to relocate the camera in the viewport using a visual teleport widget. It processes mouse movements and clicks to determine a new destination, calculates the appropriate camera orientation and focus distance, and updates the camera position accordingly. The teleport functionality is integrated with scene settings and viewport configurations, providing a seamless method for navigating complex scenes.

    Args:
        test (bool): Optional flag to enable test mode for setting custom widget files. Defaults to False.
    """

    _teleport_display_instance = None

    def __init__(self, test=False):
        self._basic_gizmo_file_name = "teleport_gizmo_basic_v003.usda"
        self._settings = carb.settings.get_settings()
        self._settings.set_default(TELE_BEAM_VISIBLE, True)
        self._settings.set_default(TELE_USE_WORLD_UP, False)
        self._teleport_model = TeleportModel()
        self._widgetPos = Gf.Vec3d(0, 0, 0)
        self._dirPos = Gf.Vec3d(0, 0, 0)
        self._widgetUp = Gf.Vec3d.YAxis()
        self._mx = 0
        self._my = 0
        self._active = False
        self._start_draging = False
        self._draging = False
        self._current_angle = 0
        self._need_skip_teleport_frame = False
        # first click and first will trigger with click teleport button
        # that cause unexpect behavior, so we need skip them
        self._need_skip_first_click = True
        self._need_skip_first_drag = True
        self._widget = TeleportWidget(model=self._teleport_model)  # get_teleport_widget_interface()
        if test:
            self._widget.set_widget_usd_file(get_data_path("teleport_gizmo_nomaterial.usda"))
        elif not self._settings.get_as_bool(TELE_BASIC_GIZMO):
            self._widget.set_widget_usd_file(get_data_path("teleport_gizmo.usda"))
        else:
            self._widget.set_widget_usd_file(get_data_path(self._basic_gizmo_file_name))
        RingGeometry.get_instance().set_filename(get_data_path(self._basic_gizmo_file_name))
        self._widget.set_beam_usd_file(get_data_path("teleport_beam.usda"))
        self._stored_camera_focus_distance = 1000
        self._pre_click_pos = [-1000, -1000, -1000]

        self._window_visibility_changed = ui.Workspace.set_window_visibility_changed_callback(
            self._on_window_visibility_changed
        )

    # used for test
    def unbind_widget_material(self):
        """Unbinds the material from the teleport widget if available."""
        if self._widget:
            self._widget.unbind_material()

    def set_widget_usd_file(self, path):
        """Set the USD file path for the teleport widget.

        Args:
            path (str): File path for the USD file to apply to the widget.
        """
        self._widget.set_widget_usd_file(path)

    def get_model(self):
        """Return the teleport model instance used for managing teleport actions.

        Returns:
            TeleportModel: The teleport model instance.
        """
        return self._teleport_model

    @staticmethod
    def get_instance(test=False):
        """Return the singleton teleport display instance.

        Args:
            test (bool): If true, create instance with test settings.

        Returns:
            Teleport: The single instance of Teleport.
        """
        if Teleport._teleport_display_instance is None:
            Teleport._teleport_display_instance = Teleport(test)
        return Teleport._teleport_display_instance

    def destroy(self):  # pragma: no cover -- currently unused
        """Destroy the teleport instance and release associated resources."""
        self._stop()
        self._update_sub = None
        if self._widget:
            self._widget.destroy()
            self._widget = None
        if self._teleport_model:
            self._teleport_model.destroy()
            self._teleport_model = None
        Teleport._teleport_display_instance = None

    def set_enabled_picking(self, enabled: bool):
        """Enable or disable object picking in the viewport.

        Args:
            enabled (bool): Flag to enable or disable picking.
        """
        try:
            import omni.kit.viewport_legacy

            viewport_window = omni.kit.viewport_legacy.get_viewport_interface().get_viewport_window()
            if viewport_window:
                viewport_window.set_enabled_picking(enabled)
                return
        except ImportError:
            # TODO: add enable picking for vp2 here
            pass

    def _start(self, test=False):
        self._need_skip_first_click = True
        if not self._widget:
            self._widget = TeleportWidget(model=self._teleport_model)  # get_teleport_widget_interface()
            if test:
                self._widget.set_widget_usd_file(get_data_path("teleport_gizmo_nomaterial.usda"))
            elif not self._settings.get_as_bool(TELE_BASIC_GIZMO):
                self._widget.set_widget_usd_file(get_data_path("teleport_gizmo.usda"))
            else:
                self._widget.set_widget_usd_file(get_data_path(self._basic_gizmo_file_name))
            self._widget.set_beam_usd_file(get_data_path("teleport_beam.usda"))
        if not self._widget.is_init():
            self._widget.refresh()

        self.set_enabled_picking(False)
        if not self.is_using_ring_manipulator():
            self._widget.show(True, init_transform=True)
        self._store_camera_focus_distance()
        self._teleport_model.visible = True

    def _stop(self):
        self._need_skip_first_click = True
        self._need_skip_first_drag = True
        self.set_enabled_picking(True)
        self._start_draging = False
        self._draging = False
        if self._widget:
            self._widget.show(False, init_transform=False)
        self._teleport_model.visible = False

    def set_active(self, active, test=False):
        """Set the active state for the teleport tool. The widget is hidden if the Welcome window is open.

        Args:
            active (bool): True to activate the teleport tool.
            test (bool): Flag for test initialization.
        """
        # Do not show teleport widget if Welcome window is up
        current_tool = self._settings.get(CURRENT_TOOL_PATH)
        active = active and current_tool != "welcome"
        if self._active == active:
            return

        self._active = active

        if active:
            if str(current_tool).lower() == "none":
                self._settings.set(CURRENT_TOOL_PATH, "navigation")

            self._start(test)
            # Notify teleport_scene to start
            omni.kit.app.queue_event(TELE_ENABLED_GLOBAL_EVENT, {"enabled": True})
        else:
            self._stop()
            # Notify teleport_scene to stop
            omni.kit.app.queue_event(TELE_ENABLED_GLOBAL_EVENT, {"enabled": False})

    def get_active(self):
        """Return the active state of the teleport tool.

        Returns:
            bool: Active state flag.
        """
        return self._active

    def _get_distance(self):  # pragma: no cover -- currently unused
        camera_state = VpCamera()
        camera_pos = camera_state.position_world
        distance = (self._widgetPos - camera_pos).GetLength()
        return distance

    async def _await_next_event(self, n=4):
        while n > 0:
            await omni.kit.app.get_app().next_update_async()
            n = n - 1

    def _store_camera_focus_distance(self):
        cam_path = vp_util.get_viewport_window_camera_path()
        if not cam_path:
            return
        distance = self._get_camera_focus_distance(cam_path)
        if distance != 0:
            self._stored_camera_focus_distance = distance
            return
        cam_state = VpCamera()
        try:
            # Get the current position and forward
            cam_pos = cam_state.position_world
            # some times couldn't get the target world correct
            # is there a bug in camera state's target_world?
            target = cam_state.target_world
            # Now get distance from world-position to camera, and the direction camera is facing
            self._stored_camera_focus_distance = (target - cam_pos).GetLength()
        except:
            return

    def _change_camera_target(self, world_pos):  # pragma: no cover -- currently unused
        # No world position: nothing hit
        if not world_pos:
            return
        # No camera: nothing to do
        cam_path = vp_util.get_viewport_window_camera_path()
        if not cam_path:
            return
        cam_state = VpCamera()
        # Get the current position and forward
        cam_pos = cam_state.position_world
        # cam_target = cam_state.target_world
        cam_fwd = Gf.Vec3d(world_pos) - cam_pos
        # distance = Gf.Vec3d(cam_pos[0] - world_pos[0], cam_pos[1] - world_pos[1], cam_pos[2] - world_pos[2]).GetLength()
        # Set the target to pos + dir * d
        target = cam_pos + cam_fwd.GetNormalized() * self._stored_camera_focus_distance
        cam_state.set_target_world(target, True)
        self._set_camera_focus_distance(cam_path, self._stored_camera_focus_distance)
        asyncio.ensure_future(self._await_next_event(2))

    def _set_camera_focus_distance(self, camera_path, distance):
        stage = omni.usd.get_context().get_stage()
        with Usd.EditContext(stage):
            camera_prim = stage.GetPrimAtPath(camera_path)
            camera_prim.GetAttribute("focusDistance").Set(distance)

    def _get_camera_focus_distance(self, camera_path):
        stage = omni.usd.get_context().get_stage()
        if stage:
            camera_prim = stage.GetPrimAtPath(camera_path)
            attr = camera_prim.GetAttribute("focusDistance")
            if attr:
                return attr.Get()
        return 0

    def _teleport(self, keep_direction=False):
        eye_tele_height = self._settings.get(PERSISTENT_TELE_EYE_HEIGHT)
        if eye_tele_height is None:
            eye_tele_height = self._settings.get(TELE_EYE_HEIGHT)

        # The eyeHeight setting is expressed in centimeters (default 250 -> 2.5m).
        # Convert it to stage units, otherwise on stages not authored in
        # centimeters (e.g. metersPerUnit=1.0) the camera is raised 250 stage
        # units above the picked point and ends up outside the scene.
        eye_tele_height = eye_tele_height * self._teleport_model.units_scale

        camera_state = VpCamera()
        camera_pos = camera_state.position_world

        new_camera_pos = Gf.Vec3d(
            self._widgetPos[0],
            self._widgetPos[1] + self._widgetUp[1] * eye_tele_height,
            self._widgetPos[2] + self._widgetUp[2] * eye_tele_height,
        )

        camera_state.set_position_world(
            new_camera_pos,
            True,
        )
        if keep_direction:
            cam_path = vp_util.get_viewport_window_camera_path()
            camera_target = camera_state.target_world
            new_camera_target = camera_target + (new_camera_pos - camera_pos)

            # # in case if we need to change orientation around vertical axis:

            # dir_0 = (camera_target - camera_pos).GetNormalized()
            # dir_1 = (new_camera_pos - camera_pos).GetNormalized()
            # viewport_api = vp_util.get_active_viewport()
            # stage = viewport_api.stage
            # if UsdGeom.GetStageUpAxis(stage) == "Y":
            #     dir_0[1] = 0
            #     dir_1[1] = 0
            # else:
            #     dir_0[2] = 0
            #     dir_1[2] = 0
            # rot = Gf.Rotation(dir_0, dir_1)
            # dir = new_camera_target - new_camera_pos
            # dir = rot.TransformDir(dir)
            # new_camera_target = new_camera_pos + dir

            camera_state.set_target_world(new_camera_target, True)
            self._set_camera_focus_distance(cam_path, self._stored_camera_focus_distance)
        else:
            self._change_camera_target(
                [
                    self._dirPos[0],
                    self._dirPos[1] + self._widgetUp[1] * eye_tele_height,
                    self._dirPos[2] + self._widgetUp[2] * eye_tele_height,
                ]
            )
        # try to improve the beam line twinkling
        # 10cm nudge, converted to stage units so it stays a fixed physical offset on any stage.
        nudge = 10 * self._teleport_model.units_scale
        self._widgetPos = Gf.Vec3d(self._widgetPos[0] + nudge, self._widgetPos[1], self._widgetPos[2])
        self._teleport_model.visible = False
        self._need_skip_teleport_frame = True

    def _calculate_angle(self, sx, sy, dx, dy):
        derection_angle = 0
        if dy == sy:
            derection_angle = math.atan(9999999)
        else:
            derection_angle = math.atan((dx - sx) / (dy - sy))
        if (dy - sy) < 0:
            derection_angle = derection_angle + math.pi
        return derection_angle

    def _valid_coords(self, coords: Sequence[float]):
        return coords[0] > -1.0 and coords[0] < 1.0 and coords[1] > -1.0 and coords[1] < 1.0

    def _get_raycast_line(self, coords: Sequence[float]):
        # NDC space in VP2 is (-1, 1) (as in OpenGL spec)
        if not self._valid_coords(coords):
            return None, None, None
        viewport_api = vp_util.get_active_viewport()
        if not viewport_api:
            return None, None, None
        ndc_to_world = viewport_api.ndc_to_world
        near_pos = ndc_to_world.Transform(Gf.Vec3d(coords[0], coords[1], 0.1))
        far_pos = ndc_to_world.Transform(Gf.Vec3d(coords[0], coords[1], 1))
        ray_dir = (far_pos - near_pos).GetNormalized()

        xform_matrix = viewport_api.transform
        p = xform_matrix.Transform((0, 0, 0))

        view_matrix = viewport_api.view
        forward = view_matrix.GetColumn(2)
        w = forward[3] or 1
        # For camera facing brush, the "visual up" is perpendicular to near/far plane to remove visual distortion.
        # But actual "ray" up is still pointing from camera to target(forward).
        visual_up = -(Gf.Vec3d(forward[0], forward[1], forward[2]) / w).GetNormalized()
        return near_pos, ray_dir, visual_up

    def _get_surface_pos(self, coords: Sequence[float], hit_result):
        viewport_api = vp_util.get_active_viewport()
        stage = viewport_api.stage
        if not stage:
            return None, None
        world_up = Gf.Vec3d.YAxis() if UsdGeom.GetStageUpAxis(stage) == "Y" else Gf.Vec3d.ZAxis()
        if hit_result.valid:
            pos = hit_result.hit_position
            if self._settings.get_as_bool(TELE_USE_WORLD_UP):
                # Ignore the picked surface normal (e.g. random point-cloud sphere normals) and keep the
                # teleport level and always allowed by orienting to world up. OMPE-74317.
                normal_up = world_up
            else:
                normal = hit_result.normal
                # Pick hits carry no normal when the viewport cannot provide one: keep the teleport level.
                normal_up = world_up if normal is None else Gf.Vec3d(normal[0], normal[1], normal[2]).GetNormalized()
        else:
            near_pos, ray_dir, visual_up = self._get_raycast_line(coords)
            if not near_pos:
                return None, None

            a = near_pos
            b = ray_dir
            if (
                ray_dir[0] * world_up[0] > 0 or ray_dir[1] * world_up[1] > 0 or ray_dir[2] * world_up[2] > 0
            ) and not self._draging:
                return None, None
            if abs(b[1]) < 0.0001 or abs(b[2]) < 0.0001:
                b[0] = b[0] + 0.0001
                b[1] = b[1] + 0.0001
                b[2] = b[2] + 0.0001
            cross_xz = [a[0] - a[1] * b[0] / b[1], 0, a[2] - a[1] * b[2] / b[1]]
            cross_xy = [a[0] - a[2] * b[0] / b[2], a[1] - a[2] * b[1] / b[2], 0]
            pos = cross_xz if UsdGeom.GetStageUpAxis(stage) == "Y" else cross_xy
            normal_up = world_up
        self._widgetUp = normal_up
        return pos, world_up

    @carb.profiler.profile
    def on_moved(self, coords: Sequence[float], hit_result):
        """Update the teleport widget and model based on movement. Compute widget position and orientation from the ray query results.

        Args:
            coords (Sequence[float]): NDC coordinates from the viewport.
            hit_result: Viewport pick hit (valid, hit_position, normal) for the surface under the cursor.
        """
        if self._need_skip_teleport_frame:
            self._need_skip_teleport_frame = False
            return
        if self._draging:
            return

        pos, world_up = self._get_surface_pos(coords, hit_result)
        if not pos:
            self._teleport_model.visible = False
            return

        self._widgetPos = Gf.Vec3d(pos[0], pos[1], pos[2])
        cam_state = VpCamera()
        cam_pos = cam_state.position_world

        if UsdGeom.GetStageUpAxis(vp_util.get_active_viewport().stage) == "Y":
            self._current_angle = self._calculate_angle(self._widgetPos[0], self._widgetPos[2], cam_pos[0], cam_pos[2])
        else:
            self._current_angle = self._calculate_angle(self._widgetPos[0], self._widgetPos[1], cam_pos[0], cam_pos[1])
        self._current_angle += math.pi * 0.5

        use_ring_manipulator = self.is_using_ring_manipulator()

        self._widget.set_widget_position(self._widgetPos)
        self._widget.set_direction_and_up(
            (cam_pos - self._widgetPos).GetNormalized(), self._widgetUp, use_ring_manipulator
        )
        # Get the current position and forward

        dir_vec = cam_pos - self._widgetPos
        distance = dir_vec.GetLength()

        if use_ring_manipulator:
            self._widget.hide_all()
        else:  # pragma: no cover -- currently unused
            self._widget.update_pos()

        show_manipulator = True
        input = carb.input.acquire_input_interface()
        app_window = omni.appwindow.get_default_app_window()
        mouse = app_window.get_mouse()
        mb_left = input.get_mouse_value(mouse, carb.input.MouseInput.LEFT_BUTTON)
        mb_right = input.get_mouse_value(mouse, carb.input.MouseInput.RIGHT_BUTTON)
        mb_middle = input.get_mouse_value(mouse, carb.input.MouseInput.MIDDLE_BUTTON)
        if mb_right == 1.0 or mb_middle == 1.0 or mb_left == 1.0:
            self._widget.hide_all()
            show_manipulator = False

        self._teleport_model.distance = distance
        self._teleport_model.angle = self._current_angle
        self._teleport_model.world_up = world_up
        self._teleport_model.position = self._widgetPos
        self._teleport_model.visual_up = self._widgetUp
        self._teleport_model.visual_front = (cam_pos - self._widgetPos).GetNormalized()
        self._teleport_model.visible = show_manipulator

    def on_drag(self, hit_result):  # pragma: no cover -- currently unused
        """Update widget direction and teleport model orientation during dragging.

        Args:
            hit_result: Viewport pick hit containing the hit position.
        """
        self._draging = True
        self._need_skip_first_drag = False
        pos = hit_result.hit_position
        if not pos:
            return
        self._dirPos = Gf.Vec3d(pos[0], pos[1], pos[2])
        viewport_api = vp_util.get_active_viewport()
        stage = viewport_api.stage
        if UsdGeom.GetStageUpAxis(stage) == "Y":
            derection_angle = self._calculate_angle(
                self._widgetPos[0], self._widgetPos[2], self._dirPos[0], self._dirPos[2]
            )
            self._current_angle = derection_angle

        else:
            derection_angle = self._calculate_angle(
                self._widgetPos[0], self._widgetPos[1], self._dirPos[0], self._dirPos[1]
            )
            derection_angle = math.pi * 2.5 - derection_angle
            self._current_angle = derection_angle - math.pi * 1.5

        self._widget.set_direction_and_up((self._dirPos - self._widgetPos).GetNormalized(), self._widgetUp)
        self._widget.update_pos()
        self._teleport_model.angle = self._current_angle
        return

    def end_drag(self, hit_result):  # pragma: no cover -- currently unused
        """Ends the active drag session and teleports the user based on the hit position if available.

        Args:
            hit_result: Viewport pick hit containing the hit position and normal.
        """
        if not self._draging:
            return
        if self._need_skip_first_drag:
            self._need_skip_first_drag = False
            return
        self._draging = False
        pos = hit_result.hit_position
        if not pos:
            return
        self._teleport()

    def on_clicked(self, coords: Sequence[float], hit_result):
        """Processes a click event to initiate teleportation if the click position is significantly different from the previous one and teleportation is allowed.

        Args:
            coords (Sequence[float]): Click coordinates in normalized device coordinates.
            hit_result: Viewport pick hit for the click position.
        """
        if not self._widget.can_teleport():
            return
        if self._need_skip_first_click:
            self._need_skip_first_click = False
        self._draging = False
        self._start_draging = False
        pos, _ = self._get_surface_pos(coords, hit_result)
        if not pos:
            return
        if (
            abs(pos[0] - self._pre_click_pos[0])
            + abs(pos[1] - self._pre_click_pos[1])
            + abs(pos[2] - self._pre_click_pos[2])
            < 0.1
        ):
            return
        self._pre_click_pos = pos
        self._teleport(True)

    def show_arc(self, show: bool = True):
        """Sets the beam visibility setting to control the display of the teleport arc and makes the teleport model visible.

        Args:
            show (bool): Flag to show or hide the teleport beam arc.
        """
        carb.settings.get_settings().set("/exts/omni.kit.tool.teleport/beamVisible", show)
        self._teleport_model.visible = True

    def _on_window_visibility_changed(self, window_name: str, visible: bool):
        if window_name == "Welcome":
            self.set_active(not visible)

    def is_using_ring_manipulator(self):
        """Checks if the ring manipulator is enabled based on the current settings.

        Returns:
            bool: True if the ring manipulator is active, otherwise false.
        """
        return carb.settings.get_settings().get("/exts/omni.kit.tool.teleport/ringManipulatorVisible")
