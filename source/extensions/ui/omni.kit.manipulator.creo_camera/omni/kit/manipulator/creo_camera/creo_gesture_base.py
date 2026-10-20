## Copyright (c) 2025, NVIDIA CORPORATION.  All rights reserved.
##
## NVIDIA CORPORATION and its licensors retain all intellectual property
## and proprietary rights in and to this software, related documentation
## and any modifications thereto.  Any use, reproduction, disclosure or
## distribution of this software and related documentation without an express
## license agreement from NVIDIA CORPORATION is strictly prohibited.
##

"""
Base class for Creo camera gestures with raycast support.

Provides common raycast and mouse accumulation functionality for all Creo gestures.
"""

__all__ = ["CreoGestureBase"]

from typing import TYPE_CHECKING, Sequence

from omni.kit.manipulator.camera import CameraGestureBase

if TYPE_CHECKING:
    from omni.kit.widget.viewport.api import ViewportAPI


# Configuration
ORTHO_FALLBACK_TO_WORLD_ORIGIN_PLANE = True  # In ortho, if no raycast hit, use world XY plane at origin


def is_orthographic(model):
    """
    Check if camera is in orthographic mode.

    Checks projection matrix element [15] which is 1 for ortho, 0 for perspective.
    This is more reliable than the orthographic flag which may not be set yet.

    Args:
        model: Camera manipulator model

    Returns:
        bool: True if orthographic, False if perspective
    """
    projection = model.get_as_floats("projection")
    if projection and len(projection) >= 16:
        # projection[15] is 1 for orthographic, 0 for perspective
        return projection[15] == 1
    return False


class CreoGestureBase(CameraGestureBase):
    """
    Base class for Creo gestures with raycast support.

    Handles:
    - Async raycast to get world position under mouse
    - Mouse movement accumulation during raycast
    - Fallback to computed position if no hit
    """

    def __init__(self, *args, viewport_api=None, **kwargs):
        """
        Initialize the gesture.

        Args:
            viewport_api: The viewport API for performing raycasts
        """
        super().__init__(*args, **kwargs)
        self._viewport_api = viewport_api
        self._world_position = None  # World space position at click (set by raycast)
        self._accumulated_movement = [0.0, 0.0]  # Accumulated mouse movement before raycast completes

    def on_began(self, mouse: Sequence[float] = None):
        """
        Called when gesture begins.

        Performs raycast to get world position at mouse location.
        Subclasses can override _on_raycast_complete for custom handling.
        """
        # Reset state
        self._world_position = None
        self._accumulated_movement = [0.0, 0.0]

        # Call parent to set up state
        super().on_began(mouse)

        # Perform raycast to get world position
        self._perform_raycast(mouse)

    def _perform_raycast(self, mouse: Sequence[float] = None):
        """
        Perform raycast at mouse position.

        Args:
            mouse: Mouse position in NDC coordinates
        """
        if not self._viewport_api:
            return

        mouse_ndc = mouse if mouse else self.sender.gesture_payload.mouse

        # Convert NDC to pixel coordinates
        mouse_pixel, viewport_api = self._viewport_api.map_ndc_to_texture_pixel(mouse_ndc)

        if mouse_pixel and viewport_api:

            def raycast_complete(prim_path: str, world_pos, *args):
                """Called when raycast completes."""
                from pxr import Gf

                if prim_path and world_pos:
                    # Hit an object - use hit position
                    if hasattr(world_pos, "x"):
                        world_pos = Gf.Vec3d(world_pos.x, world_pos.y, world_pos.z)
                    else:
                        world_pos = Gf.Vec3d(*world_pos)
                else:
                    # No hit - use different fallback for ortho vs perspective
                    if ORTHO_FALLBACK_TO_WORLD_ORIGIN_PLANE and is_orthographic(self.model):
                        # In ortho: intersect ray with plane through world origin
                        world_pos = self._compute_ortho_world_plane_intersection(mouse_ndc)
                    else:
                        # In perspective: use center_of_interest distance
                        world_pos = self._compute_world_position_at_distance(mouse_ndc)

                # Store the world position
                self._world_position = world_pos

                # Notify subclass
                self._on_raycast_complete(world_pos)

            # Request the raycast query
            query_name = f"omni.kit.manipulator.creo_camera.{self.__class__.__name__}"
            viewport_api.request_query(mouse_pixel, raycast_complete, query_name=query_name)

    def _compute_ortho_world_plane_intersection(self, mouse_ndc: Sequence[float]):
        """
        Compute intersection of mouse ray with plane parallel to camera at world origin.

        In ortho, finds the point on a plane parallel to camera XY that passes through world origin.

        Args:
            mouse_ndc: Mouse position in NDC coordinates

        Returns:
            World space position on the plane
        """
        from pxr import Gf

        # Get camera transform
        camera_transform = Gf.Matrix4d(*self.model.get_as_floats("transform"))
        projection = Gf.Matrix4d(*self.model.get_as_floats("projection"))
        inv_projection = projection.GetInverse()

        camera_pos = camera_transform.ExtractTranslation()
        camera_rotation = camera_transform.ExtractRotationMatrix()

        # In ortho, unproject mouse to get camera space XY position
        ndc_point = Gf.Vec3d(mouse_ndc[0], mouse_ndc[1], 0)
        camera_space_xy = inv_projection.Transform(ndc_point)

        # Define plane: passes through world origin, perpendicular to camera forward
        camera_forward = -camera_rotation.GetRow(2)
        world_origin = Gf.Vec3d(0, 0, 0)

        # Construct ray in world space
        cam_right = camera_rotation.GetRow(0)
        cam_up = camera_rotation.GetRow(1)

        ray_origin = camera_pos + (cam_right * camera_space_xy[0]) + (cam_up * camera_space_xy[1])
        ray_direction = camera_forward

        # Intersect ray with plane through world origin
        numerator = -(ray_origin - world_origin).GetDot(camera_forward)
        denominator = ray_direction.GetDot(camera_forward)

        if abs(denominator) > 0.0001:
            t = numerator / denominator
            world_pos = ray_origin + ray_direction * t
        else:
            # Ray parallel to plane - use origin
            world_pos = world_origin

        return world_pos

    def _compute_world_position_at_distance(self, mouse_ndc: Sequence[float]):
        """
        Compute world position at center_of_interest distance along mouse ray.

        Args:
            mouse_ndc: Mouse position in NDC coordinates

        Returns:
            World space position along the ray
        """
        from pxr import Gf

        # Get camera transform and center of interest distance
        camera_transform = Gf.Matrix4d(*self.model.get_as_floats("transform"))
        center_of_interest = Gf.Vec3d(*self.model.get_as_floats("center_of_interest"))
        coi_distance = center_of_interest.GetLength()

        # Unproject mouse NDC to get ray direction
        ndc_near = Gf.Vec3d(mouse_ndc[0], mouse_ndc[1], -1)
        projection = Gf.Matrix4d(*self.model.get_as_floats("projection"))
        inv_projection = projection.GetInverse()

        # Get ray direction in camera space
        camera_space_point = inv_projection.Transform(ndc_near)
        ray_dir = camera_space_point.GetNormalized()

        # Compute world position at center_of_interest distance
        world_pos = camera_transform.Transform(ray_dir * coi_distance)

        return world_pos

    def _on_raycast_complete(self, world_pos):
        """
        Called when raycast completes.

        Subclasses can override this to perform custom actions.

        Args:
            world_pos: The world position determined by raycast
        """
        pass

    def on_mouse_move(self, mouse_moved: Sequence[float]):
        """
        Handle mouse movement - FINAL, do not override.

        Accumulates movement and calls _perform_gesture when raycast completes.

        Args:
            mouse_moved: Tuple of (dx, dy) in normalized device coordinates [-1, 1]
        """
        # Always accumulate current movement
        self._accumulated_movement[0] += mouse_moved[0]
        self._accumulated_movement[1] += mouse_moved[1]

        # Check if raycast has completed
        if self._world_position is None:
            # Raycast not complete yet - just accumulate
            pass
        else:
            # Raycast complete - perform gesture with ALL accumulated movement
            self._perform_gesture(self._accumulated_movement, self._world_position)
            # Reset for next move
            self._accumulated_movement = [0.0, 0.0]

    def _perform_gesture(self, mouse_moved: Sequence[float], world_position):
        """
        Perform the gesture action with accumulated movement.

        Subclasses MUST override this to implement gesture-specific behavior.

        Args:
            mouse_moved: Accumulated mouse movement (dx, dy)
            world_position: World space position from raycast
        """
        raise NotImplementedError("Subclasses must implement _perform_gesture")
