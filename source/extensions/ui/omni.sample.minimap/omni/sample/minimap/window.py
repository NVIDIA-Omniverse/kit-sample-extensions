# SPDX-FileCopyrightText: Copyright (c) 2024 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

__all__ = ["WindowEventTypes", "SimpleModel", "ArcGesture", "PanGesture", "MinimapWindow"]

"""
This module implements a minimap window for the Omniverse Kit viewport.
It provides a top-down view of the scene with camera orientation and position tracking.
The minimap includes features like zooming, panning, rotation locking, and example scene loading.
"""

import asyncio

# Viewport camera monitoring using existing USD and viewport APIs
import logging
import math
import os
import weakref
from enum import IntEnum, auto
from functools import partial

import carb
import carb.eventdispatcher
import carb.events
import omni.client
import omni.kit.app
import omni.kit.commands
import omni.kit.undo
import omni.timeline
import omni.ui as ui
import omni.usd
from omni.kit.viewport.utility import get_active_viewport
from omni.kit.widget.settings import SettingType, create_setting_widget
from omni.ui import color as cl
from omni.ui import scene as sc
from pxr import Gf, Tf, Usd, UsdGeom

# Kit 107+ compatibility: ScrollGesture moved to omni.ui.scene
# Try new location first, fall back to old location for backward compatibility
try:
    from omni.ui.scene import ScrollGesture as SceneScrollGesture

    ScrollGestureBase = SceneScrollGesture
except (ImportError, AttributeError):
    # Kit 106 and earlier: use sc.ScrollGesture
    ScrollGestureBase = sc.ScrollGesture

from . import settings
from .generator import CAM_SIZE_KEY, CDATA_KEY
from .settings import S_PATH, IoHelper
from .style import style

logger = logging.getLogger(__name__)

# Custom event name for minimap UI updates (Events 2.0)
MINIMAP_UI_EVENT = "omni.kit.minimap.MINIMAP_UI_EVENT"
USE_OPENGL = False


def flatten(transform):
    """
    Convert a 4x4 matrix array to a flattened 16-element array.

    Args:
        transform (list): 4x4 matrix as nested lists

    Returns:
        list: Flattened 16-element array
    """
    m0, m1, m2, m3 = transform[0], transform[1], transform[2], transform[3]
    return [
        m0[0],
        m0[1],
        m0[2],
        m0[3],
        m1[0],
        m1[1],
        m1[2],
        m1[3],
        m2[0],
        m2[1],
        m2[2],
        m2[3],
        m3[0],
        m3[1],
        m3[2],
        m3[3],
    ]


def get_stage_axis_info(stage):
    """
    Get up axis information for a stage.

    Args:
        stage: USD stage

    Returns:
        tuple: (up_axis_token, up_index, horizontal_indices)
    """
    up_axis = UsdGeom.GetStageUpAxis(stage)
    up_index = 1 if up_axis == UsdGeom.Tokens.y else 2
    horizontal_indices = [i for i in range(3) if i != up_index]
    return up_axis, up_index, horizontal_indices


def execute_transform_command(camera_path, transform_matrix):
    """
    Execute a transform command on a camera with undo disabled.

    Args:
        camera_path: USD path to the camera prim
        transform_matrix: Gf.Matrix4d transformation matrix

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        with omni.kit.undo.disabled():
            omni.kit.commands.execute("TransformPrimCommand", path=camera_path, new_transform_matrix=transform_matrix)
        return True
    except Exception as e:
        carb.log_warn(f"Camera transform command failed: {e}")
        return False


def get_camera_relative_vectors(world_mtx, up_axis):
    """
    Extract orthogonal forward and right vectors from camera transform in horizontal plane.

    Args:
        world_mtx: Gf.Matrix4d camera world transform
        up_axis: UsdGeom up axis token (y or z)

    Returns:
        tuple: (forward, right) unit vectors in horizontal plane
    """
    world_mtx_no_translate = Gf.Matrix4d(world_mtx)
    world_mtx_no_translate.SetTranslateOnly(Gf.Vec3d(0, 0, 0))

    right_raw = world_mtx_no_translate.TransformDir(Gf.Vec3d(1, 0, 0))

    if up_axis == UsdGeom.Tokens.y:
        right = Gf.Vec3d(right_raw[0], 0, right_raw[2])
        up_vector = Gf.Vec3d(0, 1, 0)
    else:  # Z-up
        right = Gf.Vec3d(right_raw[0], right_raw[1], 0)
        up_vector = Gf.Vec3d(0, 0, 1)

    right_len = right.GetLength()
    right = right / right_len if right_len > 0.001 else Gf.Vec3d(1, 0, 0)
    forward = up_vector ^ right

    return forward, right


def get_leveled_camera_matrix(world_mtx, new_pos, up_axis, up_index):
    """
    Create camera transform matrix with horizontal look direction (no pitch).
    Preserves the camera's heading (yaw) by projecting forward direction to horizontal plane.

    Args:
        world_mtx: Current camera world transform matrix
        new_pos: New camera position (Vec3d)
        up_axis: Stage up axis token (y or z)
        up_index: Index of up axis (1 for Y, 2 for Z)

    Returns:
        Transform matrix with camera looking horizontally in preserved heading direction
    """
    # Extract current camera's forward direction and project to horizontal plane
    rotation_mtx = world_mtx.ExtractRotationMatrix()
    forward_dir = rotation_mtx.GetRow(2)
    forward_dir = -Gf.Vec3d(forward_dir[0], forward_dir[1], forward_dir[2])

    # Project to horizontal plane
    forward_horizontal = list(forward_dir)
    forward_horizontal[up_index] = 0.0
    forward_horizontal = Gf.Vec3d(*forward_horizontal)

    # Normalize or use default if too vertical
    length = forward_horizontal.GetLength()
    if length > 0.001:
        forward_horizontal = forward_horizontal / length
    else:
        # Camera was looking straight up/down, use default forward
        if up_axis == UsdGeom.Tokens.y:
            forward_horizontal = Gf.Vec3d(0, 0, -1)
        else:
            forward_horizontal = Gf.Vec3d(0, 1, 0)

    up_vector = Gf.Vec3d(0, 1, 0) if up_axis == UsdGeom.Tokens.y else Gf.Vec3d(0, 0, 1)
    camera_matrix = Gf.Matrix4d()
    camera_matrix.SetLookAt(new_pos, new_pos + forward_horizontal * 100.0, up_vector)
    return camera_matrix.GetInverse()


class WindowEventTypes(IntEnum):
    """Event types for minimap window state changes"""

    SHOW_SETTINGS = auto()  # Settings panel shown
    HIDE_SETTINGS = auto()  # Settings panel hidden


class SimpleModel(sc.AbstractManipulatorModel):
    """
    Model class that handles camera transformations and viewport updates for the minimap.
    Manages the stage events and updates the view/projection matrices.
    """

    def __init__(self, window: "MinimapWindow"):
        """
        Initialize the model with a reference to the minimap window.

        Args:
            window: Parent MinimapWindow instance
        """
        super().__init__()
        self._window = window
        self._stage = None
        self._usd_context = omni.usd.get_context()
        self.__view = (1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1)
        self.__projection = (1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1)
        self._current_time = None

        # Subscribe to stage events via Events 2.0
        self._stage_sub = [
            carb.eventdispatcher.get_eventdispatcher().observe_event(
                observer_name="omni.sample.minimap.SimpleModel",
                event_name=self._usd_context.stage_event_name(event),
                on_event=func,
            )
            for event, func in [
                (omni.usd.StageEventType.OPENED, lambda _: self._on_stage_opened()),
                (omni.usd.StageEventType.CLOSING, lambda _: self._on_stage_closing()),
            ]
        ]

        # Subscribe to timeline events
        self._timeline = omni.timeline.get_timeline_interface()
        self._timeline_sub = None
        if self._timeline:
            self._timeline_sub = self._timeline.get_timeline_event_stream().create_subscription_to_pop(
                self._on_timeline_event, name="Minimap Timeline Monitor"
            )

        # Track when position actually changes for throttled updates
        self._last_refresh_time = 0
        # Load polling throttle from settings (default to 0.1 seconds if not set)
        self._settings = carb.settings.get_settings()
        self._refresh_interval = self._settings.get(S_PATH.POLLING_THROTTLE) or 0.1

        if self._usd_context.get_stage_state() == omni.usd.StageState.OPENED:
            self._on_stage_opened()

    def destroy(self):
        """Clean up SimpleModel resources."""
        # Prevent multiple destroy calls
        if hasattr(self, "_destroyed") and self._destroyed:
            return
        self._destroyed = True

        self._on_stage_closing()
        self._stage_sub = None
        self._timeline_sub = None
        self._timeline = None
        self._window = None

    def get_as_floats(self, item):
        """
        Returns projection or view matrix as flattened float array.
        Called by SceneView to get transformation matrices.

        Args:
            item: Matrix identifier from get_item()

        Returns:
            tuple: Flattened 16-element matrix tuple
        """
        if item == self.get_item("projection"):
            return self.__projection
        if item == self.get_item("view"):
            return self.__view

    def _on_stage_opened(self):
        """
        Initializes model when a new stage is opened.
        Sets up stage reference and update subscription.
        """
        self._stage = self._usd_context.get_stage()
        self._update_sub = carb.eventdispatcher.get_eventdispatcher().observe_event(
            event_name=omni.kit.app.GLOBAL_EVENT_UPDATE,
            on_event=self._on_update,
            observer_name="omni.sample.minimap.SimpleModel.update",
        )

    def _on_stage_closing(self):
        """
        Cleanup when stage is closing.
        Clears stage reference and update subscription.
        """
        self._stage = None
        self._update_sub = None

    def _on_timeline_event(self, event):
        """
        Handle timeline events to detect time changes.
        Dispatches timeline change events when the current time changes.

        Args:
            event: Timeline event from omni.timeline
        """
        if not self._timeline or not self._window:
            return

        # Check if the current time has changed
        current_time = self._timeline.get_current_time()
        if self._current_time != current_time:
            self._current_time = current_time
            # Dispatch timeline changed event to refresh minimap
            self._window.dispatch_timeline_changed()

    # NOTE: _check_scene_camera_change is no longer used - camera updates now happen in _on_update()
    # Keeping the method stub in case we need to restore throttled updates later

    def _on_update(self, e):
        """
        Main update callback that runs on every frame.
        Updates camera matrices and minimap display based on viewport camera.

        Args:
            e: Update event
        """
        # Early return if window is being destroyed or doesn't exist
        if not self._window or not self._stage:
            return

        # Check if subscriptions have been cleared (window is shutting down)
        if not self._stage_sub or not hasattr(self, "_update_sub") or not self._update_sub:
            return

        viewport_api = get_active_viewport()
        if not viewport_api:
            return

        # Get camera path and validate it exists
        try:
            camera_path = viewport_api.get_active_camera()
            if not camera_path:
                return
        except Exception as e:
            logger.debug(f"Failed to get active camera: {e}")
            return

        up_axis = UsdGeom.GetStageUpAxis(self._stage)
        camera_prim = self._stage.GetPrimAtPath(camera_path)

        if not camera_prim or not camera_prim.IsValid():
            return

        # Additional validation: check if it's actually a camera
        try:
            usd_camera = UsdGeom.Camera(camera_prim)
            if not usd_camera or not usd_camera.GetCamera():
                return
        except Exception as e:
            logger.debug(f"Failed to validate camera prim: {e}")
            return

        # Track last valid (non-capture) camera continuously
        if camera_path and "__ommi_minimap_capture_cam" not in str(camera_path):
            self._window._last_valid_camera_path = str(camera_path)

        # Get camera transform
        rotate_actor = self._window.rotate_actor
        xform_cache = UsdGeom.XformCache(Usd.TimeCode.Default())
        world_mtx = xform_cache.GetLocalToWorldTransform(camera_prim)

        # Update actor position
        world_pos = world_mtx.ExtractTranslation()
        prev_pos = self._window._actor_world_pos
        self._window.set_actor_world_pos(world_pos)

        # Extract camera rotation quaternion for rotation tracking
        current_rotation = world_mtx.ExtractRotationQuat()
        prev_rotation = self._window._actor_rotation

        # Check if position or rotation changed with thresholds to avoid floating point noise
        position_changed = False
        if prev_pos is not None:
            # Only consider it changed if moved more than 0.001 units (1mm in meters)
            position_changed = (world_pos - prev_pos).GetLength() > 0.001

        rotation_changed = False
        if prev_rotation is not None:
            # Proper quaternion comparison: dot product of full quaternions (w, x, y, z)
            # For quaternions q1 and q2: dot = w1*w2 + x1*x2 + y1*y2 + z1*z2
            # Result: 1.0 = identical, -1.0 = opposite (both represent same rotation)
            imag1 = current_rotation.GetImaginary()
            imag2 = prev_rotation.GetImaginary()
            real1 = current_rotation.GetReal()
            real2 = prev_rotation.GetReal()
            quat_dot = abs(real1 * real2 + imag1[0] * imag2[0] + imag1[1] * imag2[1] + imag1[2] * imag2[2])
            # Threshold: only trigger on rotations > ~0.1 degrees
            # 0.9999997 corresponds to ~0.14 degrees of rotation
            rotation_changed = quat_dot < 0.9999997

        # Update stored rotation
        self._window._actor_rotation = current_rotation

        # Refresh UI if position or rotation changed (throttled)
        if position_changed or rotation_changed:
            import time

            current_time = time.time()
            # Throttle using polling interval from settings
            if (current_time - self._last_refresh_time) >= self._refresh_interval:
                self._last_refresh_time = current_time
                self._window._refresh_ui("viewport_nav")

        # Calculate orientation vectors
        t = world_mtx.ExtractTranslation()
        vp_camera_right = world_mtx.GetRow3(0)
        vp_camera_right.Normalize()

        actor_right = vp_camera_right
        up = Gf.Vec3d.YAxis() if up_axis == UsdGeom.Tokens.y else Gf.Vec3d.ZAxis()
        up_index = 1 if up_axis == UsdGeom.Tokens.y else 2
        back = Gf.Cross(actor_right, up)
        orient_actor = Gf.Matrix4d(*actor_right, 0, *up, 0, *back, 0, 0, 0, 0, 1)

        # Position the actor (camera indicator)
        translate = Gf.Matrix4d(1.0)
        t_fixed_height = t
        t_fixed_height[up_index] = 5000
        translate.SetTranslate(t_fixed_height)

        if not self._window.actor_transform:
            return

        self._window.actor_transform.transform = flatten(orient_actor * translate)

        # Initialize minimap view center to camera position if not set
        if self._window._minimap_view_center is None:
            self._window._minimap_view_center = Gf.Vec3d(t)
            self._window._minimap_view_center[up_index] = 5000

        # Set up camera orientation based on up axis
        if up_axis == UsdGeom.Tokens.y:
            back = [0, 1, 0]  # z
            up = [0, 0, -1]  # y
            right = [1, 0, 0]  # x
        else:
            back = [0, 0, 1]  # z
            up = [0, 1, 0]  # y
            right = [1, 0, 0]  # x

        orient_camera = Gf.Matrix4d(*right, 0, *up, 0, *back, 0, 0, 0, 0, 1)

        if not rotate_actor:
            # Unlocked: Map rotates with camera, camera stays centered
            orient_camera = orient_camera * orient_actor
            if up_axis == UsdGeom.Tokens.z:
                correct = Gf.Rotation(Gf.Vec3d.XAxis(), -90)
                correct_mtx = Gf.Matrix4d(1)
                correct_mtx.SetRotate(correct)
                orient_camera = correct_mtx * orient_camera

        # Apply view transform
        camera_offset_mtx = Gf.Matrix4d(1.0)
        camera_offset = Gf.Vec3d(self._window.camera_offset[0], -self._window.camera_offset[1], 0)
        camera_offset_mtx.SetTranslate(camera_offset)

        view_translate = Gf.Matrix4d(1.0)
        if rotate_actor:
            # Locked: Use minimap view center (allows panning independent of camera)
            # Fallback to camera position if view center not initialized
            if self._window._minimap_view_center is not None:
                view_translate.SetTranslate(self._window._minimap_view_center)
            else:
                view_translate.SetTranslate(t_fixed_height)
        else:
            # Unlocked: Always center on camera position (camera stays centered, map rotates)
            view_translate.SetTranslate(t_fixed_height)

        transform = camera_offset_mtx * orient_camera * view_translate
        view = transform.GetInverse()
        self.__view = flatten(view)

        # Update camera frustum and arc display
        try:
            usd_camera = UsdGeom.Camera(camera_prim)
            if not usd_camera:
                return
            camera = usd_camera.GetCamera()
            if not camera:
                return
            frustum = camera.frustum
            half_fov = frustum.GetFOV() * 0.5
            half_fov_radian = Gf.DegreesToRadians(half_fov)
            self._window.arc.begin = -half_fov_radian + math.pi
            self._window.arc.end = half_fov_radian + math.pi
        except Exception as e:
            # Silently handle camera access errors during initialization
            pass

        cam_zoom = self._window.cam_zoom

        # Calculate projection matrix
        right = cam_zoom
        left = -cam_zoom
        top = cam_zoom
        bottom = -cam_zoom
        near = 0
        far = 10000

        if not USE_OPENGL:
            projection = Gf.Matrix4d(
                2 / (right - left),
                0,
                0,
                0,
                0,
                2 / (top - bottom),
                0,
                0,
                0,
                0,
                1 / (far - near),
                0,
                -(right + left) / (right - left),
                -(top + bottom) / (top - bottom),
                far / (far - near),
                1,
            )
        else:
            projection = Gf.Matrix4d(
                2 / (right - left),
                0,
                0,
                0,
                0,
                2 / (top - bottom),
                0,
                0,
                0,
                0,
                -2 / (far - near),
                0,
                -(right + left) / (right - left),
                -(top + bottom) / (top - bottom),
                -(far + near) / (far - near),
                1,
            )

        self.__projection = flatten(projection)
        self._item_changed(None)

        # Note: _refresh_ui() is called from _on_update only when position changes
        # and is throttled to max 10 calls/second to avoid excessive invalidations


class ArcGesture(sc.DragGesture):
    """
    Gesture handler for rotating the camera view using an arc control.
    Allows dragging in an arc to rotate the camera orientation.
    """

    def __init__(self, window: "MinimapWindow"):
        """
        Initialize with reference to parent window.

        Args:
            window: Parent MinimapWindow instance
        """
        super().__init__(manager=PreventOthers())
        self._window = window

    def on_began(self):
        """Close markups when rotation begins to prevent viewport offset."""
        from .waypoints import close_markup_if_active

        close_markup_if_active()

    def on_changed(self):
        """Update camera rotation based on arc drag angle."""
        stage = omni.usd.get_context().get_stage()
        viewport_api = get_active_viewport()
        camera_prim = stage.GetPrimAtPath(viewport_api.get_active_camera())
        up_axis = UsdGeom.GetStageUpAxis(stage)

        xform_cache = UsdGeom.XformCache(Usd.TimeCode.Default())

        world_mtx = xform_cache.GetLocalToWorldTransform(camera_prim)
        world_translation = world_mtx.ExtractTranslation()
        world_mtx.SetTranslateOnly((0, 0, 0))

        angle_degree = Gf.RadiansToDegrees(self.sender.gesture_payload.moved_angle)
        rotate_actor = self._window.rotate_actor
        if not rotate_actor:
            angle_degree = -angle_degree

        rotate = Gf.Rotation(
            Gf.Vec3d.YAxis() if up_axis == UsdGeom.Tokens.y else Gf.Vec3d.ZAxis(), angle_degree
        ).GetQuat()
        rotate_mtx = Gf.Matrix4d(1)
        rotate_mtx.SetRotate(rotate)

        world_mtx = world_mtx * rotate_mtx
        world_mtx.SetTranslateOnly(world_translation)
        execute_transform_command(camera_prim.GetPath(), world_mtx)

    def on_ended(self):
        """Refresh waypoint icons after rotation completes."""
        from .waypoints import get_waypoints_layer

        waypoints = get_waypoints_layer()
        if waypoints:
            waypoints._update_icons()


class PreventOthers(sc.GestureManager):
    """
    Gesture manager that prevents certain gestures from overlapping.
    """

    def can_be_prevented(self, gesture: sc.AbstractGesture):
        return True

    def should_prevent(self, gesture: sc.AbstractGesture, preventer: sc.AbstractGesture) -> bool:
        # Prevent screen gesture when teleport or arc gesture is active
        if hasattr(gesture, "_window") and gesture._window and gesture._window._block_gestures:
            return True

        # Prevent teleport gesture when arc gesture is active
        if isinstance(gesture, TeleportGesture):
            if (isinstance(preventer, ArcGesture) or isinstance(preventer, PanGesture)) and (
                preventer.state == sc.GestureState.CHANGED
            ):
                return True

        if isinstance(gesture, PanGesture):
            if (isinstance(preventer, TeleportGesture) or isinstance(preventer, ArcGesture)) and (
                preventer.state == sc.GestureState.CHANGED
            ):
                return True

        # Allow zoom gestures to work alongside other gestures
        if isinstance(gesture, ZoomGesture):
            return False

        return False


class PanGesture(sc.DragGesture):
    """
    Gesture handler for panning the minimap view on left-drag.
    Updates the minimap view center based on mouse movement.
    """

    def __init__(self, window: "MinimapWindow"):
        """Initialize with reference to parent window."""
        self._window = window
        super().__init__(mouse_button=0, manager=PreventOthers())

    def _is_position_valid(self, pos: Gf.Vec3d) -> bool:
        """Check if a 3D position is within reasonable bounds based on map range."""
        # Get map bounds dynamically instead of using a fixed extent
        if not self._window._provider or not self._window._provider.range:
            # Fallback to large extent if no bounds available
            max_extent = 1000000.0  # 1000km
            return abs(pos[0]) < max_extent and abs(pos[1]) < max_extent and abs(pos[2]) < max_extent

        # Use map bounds with 2x margin for safety
        map_range = self._window._provider.range
        min_pt = map_range.GetMin()
        max_pt = map_range.GetMax()

        # Expand bounds by 2x on each side
        h_range = max(max_pt[0] - min_pt[0], max_pt[1] - min_pt[1]) * 2
        center_x = (min_pt[0] + max_pt[0]) * 0.5
        center_y = (min_pt[1] + max_pt[1]) * 0.5

        # Check if position is within expanded bounds
        return abs(pos[0] - center_x) < h_range and abs(pos[1] - center_y) < h_range

    def on_began(self):
        """Close markups when panning in unlocked mode."""
        if not self._window.rotate_actor:
            from .waypoints import close_markup_if_active

            close_markup_if_active()

    def on_changed(self):
        """
        Pan based on mouse movement in screen space.
        - Locked mode: Pan minimap view (camera indicator moves)
        - Unlocked mode: Move camera through stage (camera stays centered)
        """
        moved = self.sender.gesture_payload.mouse_moved
        stage = omni.usd.get_context().get_stage()
        if not stage:
            carb.log_warn("PanGesture: No stage")
            return

        up_axis = UsdGeom.GetStageUpAxis(stage)
        scale = self._window.cam_zoom

        if self._window.rotate_actor:
            delta_movement = Gf.Vec3d(
                -moved[0] * scale,
                0 if up_axis == UsdGeom.Tokens.y else -moved[1] * scale,
                -moved[1] * scale if up_axis == UsdGeom.Tokens.y else 0,
            )

            if self._window._minimap_view_center and self._is_position_valid(
                self._window._minimap_view_center + delta_movement
            ):
                self._window._minimap_view_center += delta_movement
        else:
            viewport_api = get_active_viewport()
            if not viewport_api:
                return

            camera_prim = stage.GetPrimAtPath(viewport_api.get_active_camera())
            if not camera_prim.IsValid():
                return

            xform_cache = UsdGeom.XformCache(Usd.TimeCode.Default())
            world_mtx = xform_cache.GetLocalToWorldTransform(camera_prim)
            cur_pos = world_mtx.ExtractTranslation()

            forward, right = get_camera_relative_vectors(world_mtx, up_axis)
            delta_movement = (right * -moved[0] * scale) + (forward * -moved[1] * scale)
            new_pos = cur_pos + delta_movement

            if not self._is_position_valid(new_pos):
                return

            new_mtx = Gf.Matrix4d(world_mtx)
            new_mtx.SetTranslateOnly(new_pos)
            execute_transform_command(camera_prim.GetPath(), new_mtx)

    def on_ended(self):
        """Save view center to settings when pan gesture ends (for hot reload persistence)."""
        if self._window.rotate_actor and self._window._minimap_view_center is not None:
            self._window._save_view_center_to_settings()


class TeleportGesture(sc.DoubleClickGesture):
    """Double-click to teleport (outside camera) or rotate camera (inside camera circle)."""

    def __init__(self, window: "MinimapWindow"):
        self._window = window
        super().__init__(mouse_button=0, manager=PreventOthers())

    def _get_floor_height(self):
        """Get floor height from provider, default to 0."""
        provider = self._window._provider if hasattr(self._window, "_provider") else None
        if provider:
            try:
                return provider.floor if hasattr(provider, "floor") and provider.floor is not None else 0.0
            except Exception as e:
                logger.debug(f"Failed to get floor height: {e}")
                return 0.0
        return 0.0

    def _recover_nan_camera(self, camera_prim, provider, up_index):
        """Recover camera from NaN position by placing at bounds center."""
        if not provider or not provider.range or provider.range.IsEmpty():
            carb.log_warn("Recovery failed: No valid provider range")
            return

        # Get stage units conversion
        stage = omni.usd.get_context().get_stage()
        if not stage:
            carb.log_warn("Recovery failed: No stage")
            return

        mpu = UsdGeom.GetStageMetersPerUnit(stage)
        up_axis = UsdGeom.GetStageUpAxis(stage)

        # Convert floor height from meters to stage units
        floor_height_meters = self._get_floor_height()
        floor_height_stage_units = floor_height_meters / mpu
        height_offset_stage_units = 2.0 / mpu  # 2 meters above floor

        center_3d = (provider.range.GetMin() + provider.range.GetMax()) * 0.5
        recovery_pos = list(center_3d)
        recovery_pos[up_index] = floor_height_stage_units + height_offset_stage_units
        new_pos = Gf.Vec3d(*recovery_pos)

        carb.log_warn(f"Recovering camera to: {new_pos}")

        # Get current camera transform to preserve heading
        xform_cache = UsdGeom.XformCache(Usd.TimeCode.Default())
        world_mtx = xform_cache.GetLocalToWorldTransform(camera_prim)

        # Level camera to look horizontally while preserving heading
        new_mtx = get_leveled_camera_matrix(world_mtx, new_pos, up_axis, up_index)

        success = execute_transform_command(camera_prim.GetPath(), new_mtx)
        if success:
            carb.log_warn("Camera recovered successfully")
        else:
            carb.log_warn("Camera recovery transform failed")

        self._window.camera_offset = Gf.Vec2d(0)
        self._window._minimap_view_center = Gf.Vec3d(new_pos)
        self._window._minimap_view_center[up_index] = 5000
        self._window._refresh_ui("button_click")

        # Auto-fit zoom to ensure camera is visible
        if hasattr(self._window, "auto_fit_zoom"):
            self._window.auto_fit_zoom()

    def _project_to_floor_plane(self, pos_3d, up_index, horizontal_indices):
        """Project 3D position to 2D floor plane."""
        floor_height = self._get_floor_height()
        pos_2d = [0.0, 0.0, 0.0]
        for idx in horizontal_indices:
            pos_2d[idx] = pos_3d[idx]
        pos_2d[up_index] = floor_height
        return Gf.Vec3d(*pos_2d)

    def _rotate_camera_to_look(self, camera_prim, cur_pos, look_direction_2d, up_axis, up_index):
        """Rotate camera around up axis to look in specified horizontal direction."""
        up_vector = Gf.Vec3d(0, 1, 0) if up_axis == UsdGeom.Tokens.y else Gf.Vec3d(0, 0, 1)

        horizontal_dir = Gf.Vec3d(*look_direction_2d)
        horizontal_dir[up_index] = 0.0
        horizontal_dir.Normalize()

        camera_matrix = Gf.Matrix4d()
        camera_matrix.SetLookAt(cur_pos, cur_pos + horizontal_dir * 100.0, up_vector)
        execute_transform_command(camera_prim.GetPath(), camera_matrix.GetInverse())

    def on_ended(self):
        """Teleport camera (outside circle) or rotate to look (inside circle)."""
        import math

        from .waypoints import close_markup_if_active

        close_markup_if_active()

        stage = omni.usd.get_context().get_stage()
        if not stage:
            return

        viewport_api = get_active_viewport()
        camera_prim = stage.GetPrimAtPath(viewport_api.get_active_camera())
        if not camera_prim.IsValid():
            return

        xform_cache = UsdGeom.XformCache(Usd.TimeCode.Default())
        world_mtx = xform_cache.GetLocalToWorldTransform(camera_prim)
        cur_pos = world_mtx.ExtractTranslation()

        up_axis, up_index, horizontal_indices = get_stage_axis_info(stage)
        provider = self._window._provider if hasattr(self._window, "_provider") else None

        # Handle NaN camera position
        if any(math.isnan(cur_pos[i]) for i in range(3)):
            self._recover_nan_camera(camera_prim, provider, up_index)
            return

        # Check if camera is currently outside bounds
        camera_outside_bounds = False
        if provider and provider.range and not provider.range.IsEmpty():
            minimap_range = provider.range
            min_pt, max_pt = minimap_range.GetMin(), minimap_range.GetMax()
            camera_outside_bounds = any(
                cur_pos[idx] < min_pt[idx] or cur_pos[idx] > max_pt[idx] for idx in horizontal_indices
            )

            # If camera is out of bounds AND no valid click position, recover to center
            click_pos_3d = self.gesture_payload.item_closest_point
            if camera_outside_bounds and not click_pos_3d:
                carb.log_warn("TeleportGesture: Camera out of bounds with no click target, recovering to center")
                self._recover_nan_camera(camera_prim, provider, up_index)
                return

        click_pos_3d = self.gesture_payload.item_closest_point
        if not click_pos_3d:
            carb.log_warn("TeleportGesture: No click position available")
            return

        if any(math.isnan(click_pos_3d[i]) for i in range(3)):
            carb.log_warn("TeleportGesture: Click position has NaN")
            return

        # All positions are in worldspace from here on
        # Project to 2D floor plane (worldspace coordinates)
        click_on_floor = self._project_to_floor_plane(click_pos_3d, up_index, horizontal_indices)
        camera_on_floor = self._project_to_floor_plane(cur_pos, up_index, horizontal_indices)
        offset_2d = click_on_floor - camera_on_floor

        # Force vertical component to zero
        if abs(offset_2d[up_index]) > 0.01:
            offset_list = list(offset_2d)
            offset_list[up_index] = 0.0
            offset_2d = Gf.Vec3d(*offset_list)

        # Calculate horizontal distance in worldspace
        horizontal_distance = math.sqrt(sum(offset_2d[idx] ** 2 for idx in horizontal_indices))

        camera_indicator_radius = getattr(getattr(self._window, "arc", None), "radius", 0.0)

        # Rotate camera if clicking within camera circle
        if camera_indicator_radius > 0 and horizontal_distance < camera_indicator_radius * 0.95:
            if horizontal_distance > 1.0:  # Only rotate if offset is significant
                # Rotate camera to look in the direction of the click
                normalized_offset = [offset_2d[idx] / horizontal_distance for idx in range(3)]
                look_direction_2d = Gf.Vec3d(*normalized_offset)
                self._rotate_camera_to_look(camera_prim, cur_pos, look_direction_2d, up_axis, up_index)
            return

        # Teleport: calculate absolute worldspace target position
        new_pos_worldspace = list(click_on_floor)
        new_pos_worldspace[up_index] = cur_pos[up_index]

        # Check if target position is outside horizontal bounds
        is_outside_horizontal_bounds = False
        if provider and provider.range and not provider.range.IsEmpty():
            minimap_range = provider.range
            min_pt, max_pt = minimap_range.GetMin(), minimap_range.GetMax()

            # Only validate click position if camera is currently within bounds
            if not camera_outside_bounds:
                # Camera is within bounds, check if clicked position is reasonable
                map_size_h = max(max_pt[idx] - min_pt[idx] for idx in horizontal_indices)
                max_distance_from_bounds = map_size_h * 2.0

                for idx in horizontal_indices:
                    if (
                        new_pos_worldspace[idx] < min_pt[idx] - max_distance_from_bounds
                        or new_pos_worldspace[idx] > max_pt[idx] + max_distance_from_bounds
                    ):
                        carb.log_warn(
                            f"TeleportGesture: Click position {new_pos_worldspace} is too far outside map bounds, ignoring"
                        )
                        return

                    if new_pos_worldspace[idx] < min_pt[idx] or new_pos_worldspace[idx] > max_pt[idx]:
                        is_outside_horizontal_bounds = True

        # Set camera height based on current position validity and teleport location
        mpu = UsdGeom.GetStageMetersPerUnit(stage)
        floor_height_meters = self._get_floor_height()
        floor_height_stage_units = floor_height_meters / mpu
        ceiling_height_meters = getattr(provider, "ceiling", None) or floor_height_meters + 10.0
        ceiling_height_stage_units = ceiling_height_meters / mpu

        # Check if current camera height is valid (between floor and ceiling)
        current_height_invalid = (
            cur_pos[up_index] < floor_height_stage_units or cur_pos[up_index] > ceiling_height_stage_units
        )

        if current_height_invalid or is_outside_horizontal_bounds or camera_outside_bounds:
            # Set to 2m above floor if: current height is invalid OR teleporting outside bounds
            height_offset_meters = 2.0
            height_offset_stage_units = height_offset_meters / mpu
            new_pos_worldspace[up_index] = floor_height_stage_units + height_offset_stage_units
        else:
            # Inside bounds and current height is valid: preserve current camera height
            new_pos_worldspace[up_index] = cur_pos[up_index]

        # Place camera's physical position at the clicked worldspace location
        new_pos_absolute = Gf.Vec3d(*new_pos_worldspace)

        # Determine camera orientation based on teleport location
        up_vector = Gf.Vec3d(0, 1, 0) if up_axis == UsdGeom.Tokens.y else Gf.Vec3d(0, 0, 1)

        if current_height_invalid:
            # Height was invalid: level camera to look horizontally but preserve heading (yaw)
            new_mtx = get_leveled_camera_matrix(world_mtx, new_pos_absolute, up_axis, up_index)
        elif is_outside_horizontal_bounds or camera_outside_bounds:
            # Teleporting outside bounds: look at center of bounds
            if provider and provider.range and not provider.range.IsEmpty():
                center_3d = (provider.range.GetMin() + provider.range.GetMax()) * 0.5
                # Set center height to same as camera for horizontal look
                center_target = list(center_3d)
                center_target[up_index] = new_pos_absolute[up_index]
                center_target = Gf.Vec3d(*center_target)

                camera_matrix = Gf.Matrix4d()
                camera_matrix.SetLookAt(new_pos_absolute, center_target, up_vector)
                new_mtx = camera_matrix.GetInverse()
            else:
                # No valid bounds, preserve orientation
                new_mtx = Gf.Matrix4d(world_mtx)
                new_mtx.SetTranslateOnly(new_pos_absolute)
        else:
            # Inside bounds with valid height: preserve camera's current orientation
            new_mtx = Gf.Matrix4d(world_mtx)
            new_mtx.SetTranslateOnly(new_pos_absolute)

        execute_transform_command(camera_prim.GetPath(), new_mtx)


class ZoomGesture(ScrollGestureBase):
    """Gesture handler for zooming the minimap view using mouse wheel (Kit 107+ compatible)."""

    def __init__(self, window: "MinimapWindow"):
        self._window = window
        super().__init__(manager=PreventOthers())

    def on_ended(self):
        """Process scroll events (supports both Kit 107.3 and Kit 109 APIs)."""
        try:
            scroll_value = None

            # Kit >= 109: Try raw_input.mouse_wheel first (newer API)
            if hasattr(self, "raw_input") and hasattr(self.raw_input, "mouse_wheel"):
                mouse_wheel = self.raw_input.mouse_wheel
                scroll_value = mouse_wheel.y if hasattr(mouse_wheel, "y") else mouse_wheel[1]

            # Kit < 109: Fall back to self.scroll if raw_input didn't work
            if scroll_value is None or abs(scroll_value) < 0.01:
                if hasattr(self, "scroll"):
                    scroll_list = self.scroll
                    if isinstance(scroll_list, (list, tuple)) and len(scroll_list) > 0:
                        scroll_value = scroll_list[1] if len(scroll_list) > 1 else scroll_list[0]
                    elif isinstance(scroll_list, (int, float)):
                        scroll_value = scroll_list

            # Apply zoom if we got a valid scroll value
            if scroll_value is not None and abs(scroll_value) > 0.01:
                # Use proportional zoom based on actual scroll magnitude for smoother response
                zoom_step = 0.15 * abs(scroll_value)
                zoom_factor = 1 - zoom_step if scroll_value > 0 else 1 + zoom_step
                new_zoom = max(50, min(self._window.cam_zoom * zoom_factor, 50000))
                self._window.cam_zoom = new_zoom
        except Exception as e:
            carb.log_error(f"ZoomGesture error: {e}")


# Global singleton instance of the window
g_singleton = None


class MinimapWindow(ui.Window):
    """
    Main window class for the minimap feature.
    Provides a top-down view of the scene with camera tracking and navigation controls.

    Features:
    - Camera position and orientation tracking
    - Zoom controls
    - Pan and rotate gestures
    - Rotation locking
    - Example scene loading
    - Settings panel
    """

    def __new__(cls, *args, **kwargs):
        """Ensure singleton instance"""
        if not hasattr(cls, "instance"):
            cls.instance = super().__new__(cls)
        return cls.instance

    def __init__(self, title="Minimap", width=500, height=500, *args, **kwargs):
        # Guard against multiple initialization of singleton
        if hasattr(self, "_initialized"):
            return
        self._initialized = True

        super().__init__(title=title, width=width, height=height, *args, **kwargs)
        global g_singleton
        g_singleton = self

        # CRITICAL: Force the window to always compute and not freeze when not hovered
        # This ensures camera updates are reflected even when mouse is not over minimap
        self.flags = ui.WINDOW_FLAGS_NO_SCROLLBAR
        self.auto_resize = False

        # Force the frame to always update
        self.frame.set_computed_content_size_changed_fn(lambda: None)

        # Initialize settings reference
        self._settings = carb.settings.get_settings()

        # Load cam_zoom (zoom level) from persistent settings, default to 700 if not set
        saved_cam_zoom = self._settings.get(S_PATH.CAM_ZOOM)
        self._cam_zoom = saved_cam_zoom if saved_cam_zoom is not None else 700

        # Load cam_size (FOV indicator multiplier 0-1) from runtime settings, default to 0.5 if not set
        # This persists through hot reloads but resets on app restart (30% of viewport at 0.5)
        # At 1.0, the camera indicator is half the viewport; at 0.0, it's 10% of viewport
        saved_cam_size = self._settings.get(S_PATH.CAM_SIZE)
        self._cam_size = saved_cam_size if saved_cam_size is not None else 0.5

        # Load lock/unlock mode from settings (hot reload persistence)
        saved_rotate_actor = self._settings.get(S_PATH.ROTATE_ACTOR)
        self.rotate_actor = saved_rotate_actor if saved_rotate_actor is not None else True
        self._lock_rot_btn = None
        self.camera_offset = Gf.Vec2d(0)
        # Load minimap view center from settings if available (hot reload persistence)
        saved_view_center_str = self._settings.get(S_PATH.VIEW_CENTER)
        if saved_view_center_str:
            try:
                coords = [float(x) for x in saved_view_center_str.split(",")]
                if len(coords) == 3:
                    self._minimap_view_center = Gf.Vec3d(coords[0], coords[1], coords[2])
                else:
                    self._minimap_view_center = None
            except:
                self._minimap_view_center = None
        else:
            self._minimap_view_center = None  # Separate view center that doesn't follow camera on teleport

        self._last_stage_url = None  # Track last opened stage to detect file changes
        self._actor_world_pos = Gf.Vec3d()
        self._actor_rotation = None  # Track camera rotation to detect changes
        self.actor_transform = self._show_settings = self._work_file = None
        self._work_dict = {}
        self._block_gestures = False
        self.arc = self._provider = self._menu_layer = None
        self._image_layer = self._waypoints = self._ui_frame = None
        self._camera_scene_view = None  # Scene view that displays the camera indicator
        self._simple_model = SimpleModel(self)
        self.__scene_views: list[sc.SceneView] = []

        # Subscribe to stage events to manage window state (dropdown, work_file)
        self._usd_context = omni.usd.get_context()
        self._stage = self._usd_context.get_stage()
        self._stage_sub = [
            carb.eventdispatcher.get_eventdispatcher().observe_event(
                observer_name="omni.sample.minimap.MinimapWindow",
                event_name=self._usd_context.stage_event_name(event),
                on_event=func,
            )
            for event, func in [
                (omni.usd.StageEventType.OPENED, self._on_stage_opened),
                (omni.usd.StageEventType.CLOSING, self._on_stage_closing),
            ]
        ]

        self._event_stream = carb.events.get_events_interface().create_event_stream()
        self._visiblity_changed_listener = None
        self._dispatcher = carb.eventdispatcher.get_eventdispatcher()
        # Track async tasks for proper cleanup
        self._async_tasks = []

        # Track the last valid (non-capture) camera so we can restore it
        self._last_valid_camera_path = None

        # Ensure DEV_MODE has a default value in carb settings (the _DevModeAccessor
        # in settings.py reads from carb settings on every access, so we never assign
        # to settings.DEV_MODE directly — that would overwrite the accessor object).
        if self._settings.get(S_PATH.DEV_MODE) is None:
            self._settings.set(S_PATH.DEV_MODE, False)

        self.frame.set_build_fn(self._build_ui)

    def _safe_destroy_component(self, attr_name: str):
        """Safely destroy a component and set it to None (helper to reduce boilerplate)."""
        if hasattr(self, attr_name) and (component := getattr(self, attr_name)):
            try:
                component.destroy()
            except Exception as e:
                if settings.DEV_MODE:
                    logger.warning(f"DEV: Error destroying {attr_name}: {e}")
            setattr(self, attr_name, None)

    def _build_ui(self):
        """
        Build the main UI components of the minimap window.
        Creates the base layout with minimap view and top menu.
        """
        # CRITICAL: Destroy old instances before creating new ones to prevent duplicate subscriptions
        self._safe_destroy_component("_menu_layer")
        self._safe_destroy_component("_image_layer")
        self._safe_destroy_component("_provider")

        with self.frame:
            with ui.ZStack():
                self.__build_minimap_ui()
                self._ui_frame = ui.Frame()
                self.__build_top_menu()

        from .generator import MinimapGenerator
        from .image_frame import ImageFrame
        from .menu import Menu

        self._provider = MinimapGenerator(window=self)
        self._image_layer = ImageFrame(self._provider, self)
        self._menu_layer = Menu(self._provider, self)

    def rebuild_ui(self):
        """
        Asynchronously rebuilds the entire UI.
        Clears the current frame and rebuilds all UI components on the next update cycle.
        """

        async def _rebuild_ui_async():
            # Wait for next update
            await omni.kit.app.get_app().next_update_async()
            self.frame.clear()
            self._build_ui()

        # Track the async task for proper cleanup
        task = asyncio.ensure_future(_rebuild_ui_async())
        self._async_tasks.append(task)

        # Clean up completed tasks to prevent memory leaks
        self._async_tasks = [t for t in self._async_tasks if not t.done()]

    def __build_minimap_ui(self):
        """
        Builds the core minimap UI components including:
        - Background frame and rectangle
        - Image layer for map display
        - Waypoints layer
        - Scene view with camera tracking
        - Arc controls for rotation
        """
        with ui.Frame(style={"background_color": 0xFF000000}):
            ui.Rectangle()

        # Create placeholder frames - will be replaced with actual ImageFrame and Waypoints in _build_ui
        # Use named frames so ImageFrame can find and replace them
        self._image_layer = ui.Frame(name="minimap_image_frame")
        self._waypoints = ui.Frame(name="point_icon_frame")

        with ui.Frame():
            if USE_OPENGL:
                from omni.kit.scene_view.opengl import OpenGLSceneView

                # Use the shared model instance for proper camera tracking!
                self._camera_scene_view = OpenGLSceneView(self._simple_model)
            else:
                self._camera_scene_view = sc.SceneView(self._simple_model)

            # Register the scene view so it receives model updates!
            self.add_scene_view(self._camera_scene_view)

            with self._camera_scene_view.scene:
                # Create a screen with all gestures
                screen = sc.Screen()
                screen.gestures = [
                    PanGesture(self),  # Left-drag to pan view
                    TeleportGesture(self),  # Double-click to teleport/rotate
                    ZoomGesture(self),  # Scroll to zoom
                ]

                self.actor_transform = sc.Transform()
                with self.actor_transform:
                    # FOV arc - maintains constant screen-space size based on current zoom
                    # Slider position controls percentage of screen: 0=10%, 0.5=21.5%, 1=33%
                    # Hidden by default until tiles are built
                    arc_radius = self._calculate_arc_radius()
                    self.arc = sc.Arc(
                        arc_radius,
                        axis=1,
                        tesselation=64,
                        color=[1, 1, 0, 0.5],
                        wireframe=False,
                        thickness=15,
                        intersection_thickness=5,
                        culling=sc.Culling.NONE,
                        visible=False,  # Hidden until tiles exist
                    )

                    with sc.Transform(look_at=sc.Transform.LookAt.CAMERA):
                        # Interaction arc - matches FOV arc size
                        self.interaction_arc = sc.Arc(
                            arc_radius,
                            axis=2,
                            tesselation=64,
                            color=[1, 1, 0, 0.1],
                            wireframe=False,
                            thickness=15,
                            intersection_thickness=25,
                            culling=sc.Culling.NONE,
                            gestures=[ArcGesture(self)],
                            visible=False,  # Hidden until tiles exist
                        )

                        # Center dot - 20% of arc radius
                        self.center_dot = sc.Arc(
                            arc_radius * 0.2, axis=2, tesselation=64, color=[0, 0, 1, 1], visible=False
                        )  # Hidden until tiles exist

        # Dispatch UI ready event via Events 2.0
        if self._dispatcher:
            self._dispatcher.dispatch_event(MINIMAP_UI_EVENT, payload={"ui_ready": True})

    @property
    def cam_zoom(self) -> float:
        """Get the camera zoom level."""
        return self._cam_zoom

    @cam_zoom.setter
    def cam_zoom(self, value: float):
        """Set the camera zoom level and persist to settings."""
        self._cam_zoom = value
        # Save to persistent settings
        carb.settings.get_settings().set(S_PATH.CAM_ZOOM, value)
        # Update arc sizes to maintain constant screen-space size
        self._update_arc_sizes()

    def auto_fit_zoom(self):
        """
        Automatically adjust zoom to fit the entire minimap in the window.
        This is called on first load or build to ensure the map is fully visible.
        """
        if not self._provider:
            carb.log_warn("Auto-fit: No provider available")
            return

        try:
            # Get the map bounds from the generator
            map_range = self._provider.range
            if not map_range or map_range.IsEmpty():
                carb.log_warn("Auto-fit: Map range is empty or invalid")
                return

            # Get the stage up axis to determine which axes to use
            stage = omni.usd.get_context().get_stage()
            if not stage:
                carb.log_warn("Auto-fit: No stage available")
                return

            up_axis = UsdGeom.GetStageUpAxis(stage)
            dimension = map_range.GetMax() - map_range.GetMin()

            # Determine horizontal and vertical indices based on up axis
            if up_axis == UsdGeom.Tokens.y:
                # Y-up: X is left/right, Z is forward/back
                h_idx, v_idx = 0, 2
            else:  # Z-up
                # Z-up: X is left/right, Y is forward/back
                h_idx, v_idx = 0, 1

            # Get the larger of the two horizontal dimensions IN STAGE UNITS (not meters!)
            # cam_zoom works in stage units, not meters!
            max_dimension_stage_units = max(dimension[h_idx], dimension[v_idx])

            # Also get in meters for logging
            mpu = UsdGeom.GetStageMetersPerUnit(stage)
            max_dimension_meters = max_dimension_stage_units * mpu

            # Get current window/viewport size in pixels
            window_width = self.width if hasattr(self, "width") and self.width > 0 else 500
            window_height = self.height if hasattr(self, "height") and self.height > 0 else 500
            min_window_dimension = min(window_width, window_height)

            # Calculate zoom to fit the map to fill the window
            # cam_zoom represents how many STAGE UNITS fit in the window viewport
            # Larger value = more zoomed out (can see more area)
            # Use 0.40x multiplier (0.35 * 1.15) - zoomed out 15% from previous value
            optimal_zoom = max_dimension_stage_units * 0.5

            # Clamp to reasonable bounds
            optimal_zoom = max(100, min(500000, optimal_zoom))

            # Set the zoom
            self.cam_zoom = optimal_zoom

            # Center the view on the map center (reset any panning)
            # Calculate the center point of the map bounds (horizontal only)
            min_pt, max_pt = map_range.GetMin(), map_range.GetMax()
            map_center = (min_pt + max_pt) * 0.5

            # Set minimap view center with fixed high vertical position for top-down view
            # Determine up axis index
            if up_axis == UsdGeom.Tokens.y:
                up_idx = 1
            else:  # Z-up
                up_idx = 2

            self._minimap_view_center = Gf.Vec3d(map_center)
            self._minimap_view_center[up_idx] = 5000  # Fixed high vertical position for overhead view
            self._save_view_center_to_settings()  # Persist for hot reload

        except Exception as e:
            import traceback

            carb.log_error(f"Failed to auto-fit zoom: {e}")
            carb.log_error(traceback.format_exc())

    def _calculate_arc_radius(self, cam_size: float = None) -> float:
        """
        Calculate arc radius based on cam_zoom and cam_size to maintain constant screen-space size.

        The arc occupies a percentage of screen space based on slider position:
        - slider 0.0 → 10% of screen (0.1)
        - slider 0.5 → 21.5% of screen (0.215)
        - slider 1.0 → 33% of screen (0.33)

        Uses linear formula: screen_fraction = 0.1 + cam_size * 0.23

        Args:
            cam_size: Camera size slider value (0-1). If None, uses self._cam_size

        Returns:
            Arc radius in world-space units
        """
        if cam_size is None:
            cam_size = self._cam_size

        # Linear formula for screen space percentage
        screen_fraction = 0.1 + cam_size * 0.23

        # Calculate radius based on current zoom level to maintain constant screen size
        return self._cam_zoom * screen_fraction

    def _update_arc_sizes(self, radius: float = None):
        """
        Update all arc sizes (camera FOV, interaction arc, and center dot).
        Called when cam_size slider changes or when zooming to maintain constant screen-space size.

        Args:
            radius: Arc radius to set. If None, calculates from current cam_zoom and cam_size
        """
        if radius is None:
            radius = self._calculate_arc_radius()

        # Update all arcs atomically
        if hasattr(self, "arc") and self.arc:
            self.arc.radius = radius
        if hasattr(self, "interaction_arc") and self.interaction_arc:
            self.interaction_arc.radius = radius
        if hasattr(self, "center_dot") and self.center_dot:
            self.center_dot.radius = radius * 0.2

        # Single model notification for synchronous update (scene views will update automatically)
        if self._simple_model:
            self._simple_model._item_changed(None)

    def _update_arc_visibility(self):
        """
        Update camera FOV arc visibility based on whether minimap tiles exist.
        Arcs are only visible when there are tiles to navigate.
        """
        # Check if tiles exist - explicitly convert to bool to avoid TypeError
        has_tiles = bool(
            self._provider and self._provider._map_tile_groups is not None and len(self._provider._map_tile_groups) > 0
        )

        # Update visibility for all arc components
        if hasattr(self, "arc") and self.arc:
            self.arc.visible = has_tiles
        if hasattr(self, "interaction_arc") and self.interaction_arc:
            self.interaction_arc.visible = has_tiles
        if hasattr(self, "center_dot") and self.center_dot:
            self.center_dot.visible = has_tiles

    @property
    def cam_size(self) -> float:
        """Get the camera FOV indicator size multiplier (0-1)."""
        return self._cam_size

    @cam_size.setter
    def cam_size(self, value: float):
        """Set the camera FOV indicator size multiplier (0-1) and update arcs."""
        # Clamp value between 0 and 1
        value = max(0.0, min(1.0, value))
        if self._cam_size != value:
            self._cam_size = value
            # Save to runtime settings (persists through hot reloads, resets on app restart)
            carb.settings.get_settings().set(S_PATH.CAM_SIZE, value)
            # Update arc sizes with new cam_size value
            self._update_arc_sizes(self._calculate_arc_radius(value))

    @property
    def stage(self) -> Usd.Stage:
        if self._stage is None:
            self._stage = omni.usd.get_context().get_stage()
        return self._stage

    @property
    def show_settings(self):
        if self._show_settings is None:
            # Default to True (show settings) if not set
            self._show_settings = self._settings.get(S_PATH.SHOW_SETTINGS)
            if self._show_settings is None:
                self._show_settings = True
        return self._show_settings

    @show_settings.setter
    def show_settings(self, value):
        # Only dispatch events and update UI if value actually changed
        if self._show_settings != value:
            self._show_settings = value
            carb.settings.get_settings().set(S_PATH.SHOW_SETTINGS, value)

            # Only dispatch events if the event stream is initialized
            if self._event_stream:
                if self._show_settings:
                    self._event_stream.dispatch(WindowEventTypes.SHOW_SETTINGS)
                else:
                    self._event_stream.dispatch(WindowEventTypes.HIDE_SETTINGS)

            self.__update_ui()

    def _on_stage_opened(self, e=None):
        """Handle stage opened event."""
        # Check if a capture camera became active and switch back to the last valid camera
        stage = self._usd_context.get_stage()
        if stage:
            viewport_api = get_active_viewport()
            if viewport_api:
                try:
                    camera_path = viewport_api.get_active_camera()
                    if camera_path:
                        is_capture_cam = "__ommi_minimap_capture_cam" in str(camera_path)

                        if is_capture_cam:
                            # Find a valid camera to restore to
                            if not self._last_valid_camera_path:
                                for prim in stage.Traverse():
                                    if prim.IsA(UsdGeom.Camera):
                                        prim_path_str = str(prim.GetPath())
                                        if "__ommi_minimap_capture_cam" not in prim_path_str:
                                            self._last_valid_camera_path = prim_path_str
                                            break

                            # Restore to valid camera
                            if self._last_valid_camera_path:
                                viewport_api.set_active_camera(self._last_valid_camera_path)
                        else:
                            # Track this valid camera for future restores
                            self._last_valid_camera_path = str(camera_path)
                except Exception:
                    pass

        async def init_view_center():
            await asyncio.sleep(0.3)

            # Check if this is a different stage file than the last one
            current_stage_url = self._usd_context.get_stage_url() if self._usd_context else None
            is_different_file = current_stage_url != self._last_stage_url

            # Reset view center if opening a different file
            if is_different_file and self._minimap_view_center is not None:
                self._minimap_view_center = None

            # For same file, check if camera position changed significantly (user moved & saved)
            if not is_different_file and self._minimap_view_center is not None and self._actor_world_pos:
                stage = self._usd_context.get_stage()
                if stage:
                    up_axis = UsdGeom.GetStageUpAxis(stage)
                    up_index = 1 if up_axis == UsdGeom.Tokens.y else 2
                    h_indices = [i for i in range(3) if i != up_index]
                    cam_h = Gf.Vec2d(self._actor_world_pos[h_indices[0]], self._actor_world_pos[h_indices[1]])
                    view_h = Gf.Vec2d(self._minimap_view_center[h_indices[0]], self._minimap_view_center[h_indices[1]])
                    horizontal_diff = (cam_h - view_h).GetLength()

                    # If camera moved >100 units from view center, re-center
                    if horizontal_diff > 100.0:
                        self._minimap_view_center = None

            # Initialize view center based on whether metadata exists
            if self._minimap_view_center is None:
                # Check if metadata (saved tiles) exists
                has_metadata = (
                    self._provider and self._provider._map_tile_groups and len(self._provider._map_tile_groups) > 0
                )

                if (
                    has_metadata
                    and self._actor_world_pos
                    and self._provider
                    and self._provider.range
                    and not self._provider.range.IsEmpty()
                ):
                    # Metadata exists: check if camera is within bounds
                    range_bbox = self._provider.range
                    stage = self._usd_context.get_stage()
                    if stage:
                        up_axis = UsdGeom.GetStageUpAxis(stage)
                        up_index = 1 if up_axis == UsdGeom.Tokens.y else 2
                        h_indices = [i for i in range(3) if i != up_index]
                        cam_h = [self._actor_world_pos[i] for i in h_indices]
                        range_min, range_max = range_bbox.GetMin(), range_bbox.GetMax()

                        is_within_bounds = (
                            range_min[h_indices[0]] <= cam_h[0] <= range_max[h_indices[0]]
                            and range_min[h_indices[1]] <= cam_h[1] <= range_max[h_indices[1]]
                        )

                        if is_within_bounds:
                            # Camera within bounds with metadata: center view on camera (locked mode behavior)
                            self._minimap_view_center = Gf.Vec3d(self._actor_world_pos)
                            self._minimap_view_center[up_index] = 5000
                            self._save_view_center_to_settings()  # Persist for hot reload
                        else:
                            # Camera outside bounds even with metadata: center on map
                            center_point = (range_bbox.GetMin() + range_bbox.GetMax()) * 0.5
                            self._minimap_view_center = Gf.Vec3d(center_point)
                            self._minimap_view_center[up_index] = 5000
                            self._save_view_center_to_settings()  # Persist for hot reload

                # No metadata or no valid camera position: always center on map bounds
                if (
                    self._minimap_view_center is None
                    and self._provider
                    and self._provider.range
                    and not self._provider.range.IsEmpty()
                ):
                    range_bbox = self._provider.range
                    center_point = (range_bbox.GetMin() + range_bbox.GetMax()) * 0.5
                    self._minimap_view_center = Gf.Vec3d(center_point)

                    stage = self._usd_context.get_stage()
                    if stage:
                        up_axis = UsdGeom.GetStageUpAxis(stage)
                        up_index = 1 if up_axis == UsdGeom.Tokens.y else 2
                        self._minimap_view_center[up_index] = 5000
                    self._save_view_center_to_settings()  # Persist for hot reload

        asyncio.ensure_future(init_view_center())

    def _on_stage_closing(self, e=None):
        """Handle stage closing event."""
        # Store the current stage URL for comparison when opening next stage
        self._last_stage_url = self._usd_context.get_stage_url() if self._usd_context else None

        self._work_file = None
        if hasattr(self, "_work_cb") and self._work_cb:
            self._work_cb.model.get_item_value_model(None).set_value(0)

    def _auto_frame_minimap(self):
        """
        Automatically center and zoom the minimap to fit the current minimap tiles.
        Called when a stage is opened to provide an optimal initial view.
        """

        async def frame_minimap_async():
            # Wait a bit for tiles to load
            await asyncio.sleep(0.2)

            # Get the minimap range from the provider
            if not self._provider or not self._provider.range:
                return

            range_bbox = self._provider.range
            if range_bbox.IsEmpty():
                return

            # Get the stage and up axis to determine which dimensions to use
            stage = self._usd_context.get_stage()
            if not stage:
                return

            up_axis = UsdGeom.GetStageUpAxis(stage)

            # Get the horizontal and vertical dimensions (excluding the up axis)
            min_point = range_bbox.GetMin()
            max_point = range_bbox.GetMax()
            dimensions = max_point - min_point

            # Determine which axes are horizontal and vertical based on up axis
            if up_axis == UsdGeom.Tokens.z:
                h_dim = dimensions[0]  # X
                v_dim = dimensions[1]  # Y
            else:  # Y up
                h_dim = dimensions[0]  # X
                v_dim = dimensions[2]  # Z

            # Calculate zoom to fit the larger dimension with minimal padding
            max_dim = max(h_dim, v_dim)
            if max_dim > 0:
                # Set zoom level based on max dimension
                # The zoom value represents the half-width of the view in stage units
                self.cam_zoom = max_dim * 0.5  # 0.5 provides balanced framing to fill window

            # Reset camera offset and center minimap view on the range center
            self.camera_offset = Gf.Vec2d(0, 0)

            # Center the minimap view on the center of the minimap range
            center_point = (min_point + max_point) * 0.5
            up_index = 1 if up_axis == UsdGeom.Tokens.y else 2
            self._minimap_view_center = Gf.Vec3d(center_point)
            self._minimap_view_center[up_index] = 5000  # Fixed height for minimap view
            self._save_view_center_to_settings()  # Persist for hot reload

        # Run the async task
        task = asyncio.ensure_future(frame_minimap_async())
        self._async_tasks.append(task)
        # Clean up completed tasks
        self._async_tasks = [t for t in self._async_tasks if not t.done()]

    def _populate_examples(self, init=False, *args, **kwargs):
        """
        Populates the example scene dropdown menu with available USD files.

        Args:
            init (bool): If True, tries to select the current stage if it matches an example
            *args, **kwargs: Additional arguments passed from UI callbacks
        """
        if not self._work_cb:
            return

        # Check if app is ready before trying to access extension paths
        app = omni.kit.app.get_app()
        if not app or not app.is_running():

            async def retry_later():
                await app.next_update_async()
                self._populate_examples(init)

            # Track the async task for proper cleanup
            task = asyncio.ensure_future(retry_later())
            self._async_tasks.append(task)

            # Clean up completed tasks to prevent memory leaks
            self._async_tasks = [t for t in self._async_tasks if not t.done()]
            return

        self._work_cb.tooltip = ""
        [self._work_cb.model.remove_item(item) for item in self._work_cb.model.get_item_children()]

        try:
            _work_dir = IoHelper().get_extension_path("data/example_scenes/")
            _dir_list = os.listdir(_work_dir)
            self._work_dict = {}
            for _file_name in _dir_list:
                _name, _ext = os.path.splitext(_file_name)
                if _ext in [".usd", ".usda", ".usdc"]:
                    _work_path = omni.client.combine_urls(_work_dir, _file_name)
                    self._work_dict[_name] = _work_path
        except (FileNotFoundError, OSError) as e:
            self._work_dict = {}

        self._work_cb.model.append_child_item(None, ui.SimpleStringModel("Load Example Scene:"))
        for _file_name in self._work_dict:
            self._work_cb.model.append_child_item(None, ui.SimpleStringModel(_file_name))

    def _on_example_changed(self, model, *args, **kwargs):
        """
        Handles selection changes in the example scene dropdown.
        Loads the selected example scene if valid.

        Args:
            model: ComboBox model containing selection
            *args, **kwargs: Additional callback arguments
        """
        item_names = [
            self._work_cb.model.get_item_value_model(item).as_string for item in self._work_cb.model.get_item_children()
        ]
        selection = self._work_dict.get(item_names[model.as_int], "")
        if selection:
            self.work_file = selection

    def __build_top_menu(self):
        """
        Builds the top menu bar UI with controls including:
        - Lock/unlock rotation button
        - Zoom in/out buttons
        - Recenter button
        - Settings toggle
        - Example scene selector
        """

        def clicked(widget=None, *args, **kwargs):
            """
            Click handler for menu buttons.

            Args:
                widget: Button identifier or widget instance
            """
            if not isinstance(widget, str):
                widget = widget.name

            if widget == "lock_rot":
                self.rotate_actor = not self.rotate_actor
                # Save lock/unlock mode to settings for hot reload persistence
                self._settings.set(S_PATH.ROTATE_ACTOR, self.rotate_actor)
                # Reset state when switching modes for consistent behavior
                if self.rotate_actor:
                    # Switching to locked mode: reinitialize view center to current camera position
                    stage = self._usd_context.get_stage()
                    if stage:
                        from omni.kit.viewport.utility import get_active_viewport

                        viewport_api = get_active_viewport()
                        if viewport_api:
                            try:
                                camera_path = viewport_api.get_active_camera()
                                if camera_path:
                                    camera_prim = stage.GetPrimAtPath(camera_path)
                                    if camera_prim.IsValid():
                                        xform_cache = UsdGeom.XformCache(Usd.TimeCode.Default())
                                        world_mtx = xform_cache.GetLocalToWorldTransform(camera_prim)
                                        cam_pos = world_mtx.ExtractTranslation()
                                        up_axis = UsdGeom.GetStageUpAxis(stage)
                                        up_index = 1 if up_axis == UsdGeom.Tokens.y else 2
                                        self._minimap_view_center = Gf.Vec3d(cam_pos)
                                        self._minimap_view_center[up_index] = 5000
                                        self._save_view_center_to_settings()  # Persist for hot reload
                            except Exception as e:
                                logger.debug(f"Failed to center on camera: {e}")
                self.__update_ui()
            elif widget == "settings":
                self.show_settings = not self.show_settings
            elif widget == "zoom_in":
                self.cam_zoom = max(50, min(self.cam_zoom * 10 / 12, 50000))
            elif widget == "zoom_out":
                self.cam_zoom = max(50, min(self.cam_zoom * 1.2, 50000))
            elif widget == "recenter":
                import math

                stage = self._usd_context.get_stage()
                if not stage or not self._provider:
                    return

                from omni.kit.viewport.utility import get_active_viewport

                viewport_api = get_active_viewport()
                if not viewport_api:
                    return

                camera_prim = stage.GetPrimAtPath(viewport_api.get_active_camera())
                if not camera_prim.IsValid():
                    return

                # Get bounds (minimap or stage fallback)
                minimap_range = (
                    self._provider.range if self._provider.range and not self._provider.range.IsEmpty() else None
                )
                if not minimap_range:
                    stage_bbox = UsdGeom.BBoxCache(
                        Usd.TimeCode.Default(), includedPurposes=[UsdGeom.Tokens.default_]
                    ).ComputeWorldBound(stage.GetPseudoRoot())
                    if stage_bbox.GetRange().IsEmpty():
                        return
                    minimap_range = stage_bbox.GetRange()

                up_axis = UsdGeom.GetStageUpAxis(stage)
                up_index = 1 if up_axis == UsdGeom.Tokens.y else 2
                horizontal_indices = [i for i in range(3) if i != up_index]

                xform_cache = UsdGeom.XformCache(Usd.TimeCode.Default())
                world_mtx = xform_cache.GetLocalToWorldTransform(camera_prim)
                cur_pos = world_mtx.ExtractTranslation()

                # Get floor height in meters and convert to stage units
                mpu = UsdGeom.GetStageMetersPerUnit(stage)
                floor_height_meters = self._get_floor_height()
                floor_height_stage_units = floor_height_meters / mpu
                height_offset_stage_units = 2.0 / mpu  # 2 meters above floor

                min_pt, max_pt = minimap_range.GetMin(), minimap_range.GetMax()
                center_3d = (min_pt + max_pt) * 0.5

                # Check for NaN or out of bounds
                is_nan = any(math.isnan(cur_pos[i]) for i in range(3))
                is_within_bounds = not is_nan and all(min_pt[i] <= cur_pos[i] <= max_pt[i] for i in range(3))

                if is_nan or not is_within_bounds:
                    # Camera is out of bounds or NaN: teleport to center at 2m above floor
                    new_pos = list(center_3d)
                    new_pos[up_index] = floor_height_stage_units + height_offset_stage_units
                    self._place_and_center_camera(camera_prim, Gf.Vec3d(*new_pos), world_mtx, up_index)
                else:
                    # Camera is within bounds: just center the minimap view without moving camera
                    self.camera_offset = Gf.Vec2d(0)
                    self._minimap_view_center = Gf.Vec3d(cur_pos)
                    self._minimap_view_center[up_index] = 5000
                    self._save_view_center_to_settings()  # Persist for hot reload
                    self._refresh_ui("recenter_button")

                # Auto-fit zoom to ensure entire minimap is visible
                self.auto_fit_zoom()

        with ui.Frame():
            with ui.VStack(width=0, height=0):
                ui.Spacer(height=5)
                with ui.HStack(height=0):
                    ui.Spacer(width=3)
                    with ui.ZStack(style=style):

                        def block_gestures(h):
                            self._block_gestures = h

                        ui.Rectangle(mouse_hovered_fn=lambda h: block_gestures(h))
                        h_stack = ui.HStack(spacing=5, width=0, style=style)
        with h_stack:
            self._lock_rot_btn = ui.Button("U", width=20, height=20, clicked_fn=partial(clicked, widget="lock_rot"))
            _tt = "Zoom Out (also mouse-wheel or pinch)."
            ui.Button("-", width=20, height=20, clicked_fn=partial(clicked, widget="zoom_out"), tooltip=_tt)
            _tt = "Zoom In (also mouse-wheel or pinch)."
            ui.Button("+", width=20, height=20, clicked_fn=partial(clicked, widget="zoom_in"), tooltip=_tt)
            _tt = "Recenter & Fit:\nIf camera is within 3D bounds, centers minimap view on camera.\nIf outside bounds, teleports camera to minimap center (2m above floor).\nAuto-fits zoom to fill window."
            ui.Button("C", width=20, height=20, clicked_fn=partial(clicked, widget="recenter"), tooltip=_tt)
            self._settings_btn = ui.Button("Show Settings", width=100, clicked_fn=partial(clicked, widget="settings"))
            _tt = "Use drop down to load an example scene."
            self._work_cb = ui.ComboBox(name="work_file", width=0, clicked_fn=self._populate_examples, tooltip=_tt)
            self._populate_examples(init=True)
            # set changed callback AFTER it is populated to avoid race condition
            self._work_cb.model.get_item_value_model(None).add_value_changed_fn(self._on_example_changed)

        self.__update_ui()

    def __update_ui(self):
        """
        Updates UI elements to reflect current state:
        - Lock/unlock button text and tooltip
        - Settings button text
        """
        self._lock_rot_btn.text = "U" if self.rotate_actor else "L"
        self._lock_rot_btn.tooltip = f"{'Unlock' if self.rotate_actor else 'Lock'} Orientation"
        self._settings_btn.text = "Hide Settings" if self._show_settings else "Show Settings"

    def _get_floor_height(self):
        """Get floor height from provider."""
        if self._provider:
            try:
                return (
                    self._provider.floor
                    if hasattr(self._provider, "floor") and self._provider.floor is not None
                    else 0.0
                )
            except Exception as e:
                logger.debug(f"Failed to get floor height from provider: {e}")
                return 0.0
        return 0.0

    def _save_view_center_to_settings(self):
        """Save current minimap view center to carb settings for persistence across hot reloads."""
        if self._minimap_view_center is not None:
            view_str = f"{self._minimap_view_center[0]},{self._minimap_view_center[1]},{self._minimap_view_center[2]}"
            self._settings.set(S_PATH.VIEW_CENTER, view_str)

    def _center_minimap_view_on_position(self, position: Gf.Vec3d, up_index: int, source: str = "center_view"):
        """Center the minimap view on a specific position.

        Args:
            position: 3D position to center on
            up_index: Index of the up axis (1 for Y, 2 for Z)
            source: String describing what triggered this action (for debugging)
        """
        self.camera_offset = Gf.Vec2d(0)
        self._minimap_view_center = Gf.Vec3d(position)
        self._minimap_view_center[up_index] = 5000
        self._save_view_center_to_settings()  # Persist for hot reload
        self._refresh_ui(source)

    def _place_and_center_camera(self, camera_prim, new_pos, world_mtx, up_index):
        """Place camera at position and center minimap view."""
        new_mtx = Gf.Matrix4d(world_mtx)
        new_mtx.SetTranslateOnly(new_pos)
        execute_transform_command(camera_prim.GetPath(), new_mtx)

        self._center_minimap_view_on_position(new_pos, up_index, "camera_teleport")

    def is_camera_within_bounds(self) -> bool:
        """Check if camera is within minimap bounds.

        Returns:
            True if camera is within bounds, False otherwise (or if unable to determine)
        """
        try:
            import math

            from omni.kit.viewport.utility import get_active_viewport

            viewport_api = get_active_viewport()
            if not viewport_api:
                return False

            stage = omni.usd.get_context().get_stage()
            if not stage or not self._provider or not self._provider.range:
                return False

            camera_prim = stage.GetPrimAtPath(viewport_api.get_active_camera())
            if not camera_prim.IsValid():
                return False

            minimap_range = self._provider.range
            if minimap_range.IsEmpty():
                return False

            xform_cache = UsdGeom.XformCache(Usd.TimeCode.Default())
            world_mtx = xform_cache.GetLocalToWorldTransform(camera_prim)
            camera_pos = world_mtx.ExtractTranslation()

            min_pt, max_pt = minimap_range.GetMin(), minimap_range.GetMax()

            # Check for NaN or out of bounds
            is_nan = any(math.isnan(camera_pos[i]) for i in range(3))
            is_within_bounds = not is_nan and all(min_pt[i] <= camera_pos[i] <= max_pt[i] for i in range(3))

            return is_within_bounds

        except Exception:
            # If we can't determine, assume out of bounds to be safe
            return False

    def is_camera_visible_in_viewport(self) -> bool:
        """Check if camera is visible in the current minimap viewport.

        Checks if the camera position is within the visible area defined by
        the current zoom level and view center.

        Returns:
            True if camera is visible in viewport, False otherwise
        """
        try:
            import math

            from omni.kit.viewport.utility import get_active_viewport

            viewport_api = get_active_viewport()
            if not viewport_api:
                return False

            stage = omni.usd.get_context().get_stage()
            if not stage or not self._minimap_view_center:
                return False

            camera_prim = stage.GetPrimAtPath(viewport_api.get_active_camera())
            if not camera_prim.IsValid():
                return False

            xform_cache = UsdGeom.XformCache(Usd.TimeCode.Default())
            world_mtx = xform_cache.GetLocalToWorldTransform(camera_prim)
            camera_pos = world_mtx.ExtractTranslation()

            # Get up axis to determine horizontal indices
            up_axis = UsdGeom.GetStageUpAxis(stage)
            up_index = 1 if up_axis == UsdGeom.Tokens.y else 2
            h_indices = [i for i in range(3) if i != up_index]

            # Check if camera position is NaN
            if any(math.isnan(camera_pos[i]) for i in range(3)):
                return False

            # Get horizontal positions
            cam_h = [camera_pos[i] for i in h_indices]
            view_h = [self._minimap_view_center[i] for i in h_indices]

            # cam_zoom defines the half-extent of the visible area
            # Viewport spans from (view_center - cam_zoom) to (view_center + cam_zoom)
            zoom_extent = self._cam_zoom

            # Check if camera is within the visible viewport (with small margin for safety)
            margin = zoom_extent * 0.1  # 10% margin
            is_visible = all(
                view_h[i] - zoom_extent - margin <= cam_h[i] <= view_h[i] + zoom_extent + margin for i in range(2)
            )

            return is_visible

        except Exception:
            # If we can't determine, assume not visible to trigger auto-fit
            return False

    def center_viewport_on_camera(self):
        """Center the minimap viewport on the camera without changing zoom (locked mode).

        Updates the minimap view center to the camera position, preserving current zoom level.
        """
        try:
            from omni.kit.viewport.utility import get_active_viewport

            viewport_api = get_active_viewport()
            if not viewport_api:
                return

            stage = omni.usd.get_context().get_stage()
            if not stage:
                return

            camera_prim = stage.GetPrimAtPath(viewport_api.get_active_camera())
            if not camera_prim.IsValid():
                return

            xform_cache = UsdGeom.XformCache(Usd.TimeCode.Default())
            world_mtx = xform_cache.GetLocalToWorldTransform(camera_prim)
            camera_pos = world_mtx.ExtractTranslation()

            # Get up axis
            up_axis = UsdGeom.GetStageUpAxis(stage)
            up_index = 1 if up_axis == UsdGeom.Tokens.y else 2

            # Center minimap view on camera position using shared helper
            self._center_minimap_view_on_position(camera_pos, up_index, "center_on_camera")

        except Exception as e:
            # Silently fail
            carb.log_warn(f"Failed to center viewport on camera: {e}")

    def check_and_center_camera(self):
        """Check if camera is outside minimap bounds and teleport to center if so (unlocked mode only)."""
        # Use helper method to check bounds
        if self.is_camera_within_bounds():
            return  # Camera is within bounds, no action needed

        # Camera is outside bounds, teleport to center
        try:
            from omni.kit.viewport.utility import get_active_viewport

            viewport_api = get_active_viewport()
            if not viewport_api:
                return

            stage = omni.usd.get_context().get_stage()
            if not stage or not self._provider or not self._provider.range:
                return

            camera_prim = stage.GetPrimAtPath(viewport_api.get_active_camera())
            if not camera_prim.IsValid():
                return

            minimap_range = self._provider.range
            if minimap_range.IsEmpty():
                return

            xform_cache = UsdGeom.XformCache(Usd.TimeCode.Default())
            world_mtx = xform_cache.GetLocalToWorldTransform(camera_prim)

            up_axis = UsdGeom.GetStageUpAxis(stage)
            up_index = 1 if up_axis == UsdGeom.Tokens.y else 2

            min_pt, max_pt = minimap_range.GetMin(), minimap_range.GetMax()

            # Calculate center and teleport
            mpu = UsdGeom.GetStageMetersPerUnit(stage)
            floor_height_meters = self._get_floor_height()
            floor_height_stage_units = floor_height_meters / mpu
            height_offset_stage_units = 2.0 / mpu  # 2 meters above floor

            center_3d = (min_pt + max_pt) * 0.5
            new_pos = list(center_3d)
            new_pos[up_index] = floor_height_stage_units + height_offset_stage_units

            self._place_and_center_camera(camera_prim, Gf.Vec3d(*new_pos), world_mtx, up_index)

        except Exception as e:
            # Silently fail - this is a convenience feature
            pass

    def destroy(self):
        """
        Clean up window resources and singleton state.
        Ensures proper cleanup of models, providers and UI layers.
        """
        # Prevent multiple destroy calls
        if hasattr(self, "_destroyed") and self._destroyed:
            return
        self._destroyed = True

        # Clear initialization flag to allow re-initialization
        if hasattr(self, "_initialized"):
            delattr(self, "_initialized")

        # 1. Cancel all async tasks first (children then self)
        for component in [self._provider, self._image_layer, self._menu_layer, self._waypoints]:
            if component and hasattr(component, "destroy"):
                component.destroy()

        # Cancel window's own async tasks
        if hasattr(self, "_async_tasks"):
            for task in self._async_tasks:
                if not task.done():
                    task.cancel()
            self._async_tasks.clear()

        # 2. Clean up subscriptions
        self._stage_sub = None
        self._dispatcher = None
        self._event_stream = None

        # 3. Clean up SimpleModel subscriptions
        if self._simple_model:
            if hasattr(self._simple_model, "_stage_sub"):
                self._simple_model._stage_sub = None
            if hasattr(self._simple_model, "_timeline_sub"):
                self._simple_model._timeline_sub = None
            if hasattr(self._simple_model, "_timeline"):
                self._simple_model._timeline = None

        # 4. Clear references
        self._camera_scene_view = None
        self._provider = None
        self._image_layer = None
        self._menu_layer = None
        self._waypoints = None

        # 5. Clean up singleton state and call parent destroy
        if hasattr(MinimapWindow, "instance"):
            delattr(MinimapWindow, "instance")

        super().destroy()
        global g_singleton
        g_singleton = None

    def set_actor_world_pos(self, world_pos: Gf.Vec3d):
        """
        Updates the camera position in world space with threshold checking.
        Only updates if position changed by more than 0.1 units (10cm).

        Args:
            world_pos (Gf.Vec3d): New world space position

        Note:
            _refresh_ui() is called by _on_update() after this method with proper
            throttling (max 10 calls/sec). This ensures tiles update efficiently.
        """
        # Use a reasonable tolerance to avoid excessive updates from micro-movements
        if self._actor_world_pos is not None:
            diff = (world_pos - self._actor_world_pos).GetLength()
            if diff < 0.1:  # Less than 10cm difference - only update for significant movements
                return

        self._actor_world_pos = world_pos

        # Directly refresh the minimap tiles when scene updates
        # This is immediate and not throttled - tiles have caching to prevent redundant rebuilds
        if self._image_layer and hasattr(self._image_layer, "_update_tiles"):
            self._image_layer._update_tiles()

    def _refresh_ui(self, source="unknown"):
        """
        Refresh UI by invalidating scene views to trigger re-render.
        This ensures the minimap updates even when the window is not hovered.
        Critical for Omniverse's deferred rendering system.

        The redundancy here is intentional - different views may need different invalidation paths.

        Args:
            source: String describing what triggered this refresh (for debugging)
        """
        # Throttle refresh to prevent excessive calls (max 10 FPS)
        import time

        current_time = time.time()
        if not hasattr(self, "_last_ui_refresh_time"):
            self._last_ui_refresh_time = 0.0

        time_since_last_refresh = current_time - self._last_ui_refresh_time
        if time_since_last_refresh < 0.1:  # ~10 FPS throttle
            return

        self._last_ui_refresh_time = current_time

        # Performance monitoring (only active when DEV_MODE = True) - tracks ACTUAL refreshes after throttling
        if settings.DEV_MODE:
            if not hasattr(self, "_refresh_count"):
                self._refresh_count = 0
                self._refresh_start_time = current_time
                self._last_logged_fps = 0.0
                self._dev_mode_log_counter = 0
                self._refresh_sources = {}

            self._refresh_count += 1
            self._refresh_sources[source] = self._refresh_sources.get(source, 0) + 1

            elapsed = current_time - self._refresh_start_time
            if elapsed >= 1.0:  # Log every second
                fps = self._refresh_count / elapsed
                self._dev_mode_log_counter += 1
                # Log if FPS changed significantly (> 2 FPS difference) OR every 5 seconds for heartbeat
                if abs(fps - self._last_logged_fps) > 2.0 or self._dev_mode_log_counter >= 5:
                    sources_str = ", ".join([f"{k}:{v}" for k, v in sorted(self._refresh_sources.items())])
                    logger.warning(f"DEV: UI Refresh Rate: {fps:.1f} / sec ({sources_str})")
                    self._last_logged_fps = fps
                    self._dev_mode_log_counter = 0
                self._refresh_count = 0
                self._refresh_start_time = current_time
                self._refresh_sources.clear()

        # Invalidate main window frame
        if hasattr(self, "frame") and self.frame and hasattr(self.frame, "invalidate_raster"):
            self.frame.invalidate_raster()

        # Invalidate the camera indicator scene view directly
        if (
            hasattr(self, "_camera_scene_view")
            and self._camera_scene_view
            and hasattr(self._camera_scene_view, "invalidate_raster")
        ):
            self._camera_scene_view.invalidate_raster()

        # Invalidate the image layer's scene view (tiles)
        if (
            hasattr(self, "_image_layer")
            and self._image_layer
            and hasattr(self._image_layer, "_scene_view")
            and self._image_layer._scene_view
            and hasattr(self._image_layer._scene_view, "invalidate_raster")
        ):
            self._image_layer._scene_view.invalidate_raster()

        # Invalidate all tracked scene views (catches views registered via add_scene_view)
        if hasattr(self, "_MinimapWindow__scene_views"):
            for scene_view_ref in self.__scene_views:
                scene_view = scene_view_ref()
                if scene_view and hasattr(scene_view, "invalidate_raster"):
                    scene_view.invalidate_raster()

    def dispatch_timeline_changed(self):
        """
        Triggers timeline change refresh for the minimap.
        Call this when the timeline/time slider changes.
        """
        # Directly refresh the minimap tiles when timeline changes
        if self._image_layer:
            self._image_layer._update_tiles()

    def get_frame(self, name: str = "") -> ui.Frame:
        """
        Returns a UI frame by name.

        Args:
            name (str): Frame identifier

        Returns:
            ui.Frame: Requested frame or None
        """
        if name == "minimap_image_frame":
            if hasattr(self, "_image_layer"):
                return self._image_layer
            return None
        elif name == "ui_frame":
            if hasattr(self, "_ui_frame"):
                return self._ui_frame
            return None
        elif name == "point_icon_frame":
            if hasattr(self, "_waypoints"):
                return self._waypoints
            return None
        return None

    def add_scene_view(self, scene_view: sc.SceneView):
        """
        Adds a scene view to track and updates its model.
        Uses weak references to allow proper cleanup.

        Args:
            scene_view (sc.SceneView): Scene view to add
        """
        self.__clean_weak_views()
        self.__scene_views.append(weakref.ref(scene_view, self.__clean_weak_views))
        scene_view.model = self._simple_model

    def __clean_weak_views(self, *args):
        """Removes any dead weak references from the scene view list."""
        self.__scene_views = [sv for sv in self.__scene_views if sv()]

    def get_actor_translate(self) -> Gf.Vec3d:
        """
        Returns the current camera position in world space.

        Returns:
            Gf.Vec3d: Current world space position
        """
        return self._actor_world_pos

    def get_minimap_view_center(self) -> Gf.Vec3d:
        """
        Returns the minimap view center position for tile visibility filtering.
        Falls back to camera position, then minimap range center if view center is not initialized.

        Returns:
            Gf.Vec3d: The view center position
        """
        if self._minimap_view_center is not None:
            return self._minimap_view_center

        # Fallback 1: Use camera position if it's been set (not at origin)
        if self._actor_world_pos and (
            self._actor_world_pos[0] != 0 or self._actor_world_pos[1] != 0 or self._actor_world_pos[2] != 0
        ):
            return self._actor_world_pos

        # Fallback 2: Use minimap range center if available
        if hasattr(self, "_provider") and self._provider and self._provider.range:
            minimap_range = self._provider.range
            if not minimap_range.IsEmpty():
                center = (minimap_range.GetMin() + minimap_range.GetMax()) * 0.5
                return center

        # Final fallback: origin (but this means no tiles will likely be shown)
        return Gf.Vec3d(0, 0, 0)

    def get_event_stream(self) -> carb.events.IEventStream:
        """
        Returns the window's event stream for subscribers.

        Returns:
            carb.events.IEventStream: Event stream instance
        """
        return self._event_stream

    @property
    def work_file(self):
        """
        Current stage file path.
        Returns None if stage is not set.
        """
        if self._work_file is None:
            root_layer = self._stage.GetRootLayer() if self._stage else None
            self._work_file = root_layer.identifier if root_layer and not root_layer.anonymous else None
        return self._work_file

    @work_file.setter
    def work_file(self, value):
        """
        Sets and loads a new stage file.

        Args:
            value (str): Path to USD stage file
        """
        if not value or not os.path.exists(value):
            return
        self._work_file = value
        open_loadset = omni.usd.UsdContextInitialLoadSet.LOAD_ALL
        omni.kit.window.file.open_stage(self._work_file, open_loadset=open_loadset)

    def set_visible(self, value):
        """
        Sets window visibility state.

        Args:
            value (bool): Desired visibility state
        """
        self.visible = value

    def get_visible(self):
        """
        Returns current visibility state.
        Used by menu items for checked status.

        Returns:
            bool: Current visibility state
        """
        return self.visible


def get_window_instance():
    """
    Returns the singleton instance of the MinimapWindow.

    Returns:
        MinimapWindow: Singleton instance of the MinimapWindow
    """
    return g_singleton
