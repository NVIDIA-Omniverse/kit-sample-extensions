## Copyright (c) 2025, NVIDIA CORPORATION.  All rights reserved.
##
## NVIDIA CORPORATION and its licensors retain all intellectual property
## and proprietary rights in and to this software, related documentation
## and any modifications thereto.  Any use, reproduction, disclosure or
## distribution of this software and related documentation without an express
## license agreement from NVIDIA CORPORATION is strictly prohibited.
##

"""
Creo-style rotation gesture.

Implements camera rotation around a raycast-determined point.
Horizontal movement rotates around camera Y axis, vertical around camera X axis.
"""

__all__ = ["CreoRotateGesture"]

from typing import Sequence

from .creo_gesture_base import CreoGestureBase


class CreoRotateGesture(CreoGestureBase):
    """
    Creo-style rotation gesture.

    Rotates camera around the raycast hit point.
    - Horizontal mouse: rotates around camera Y axis
    - Vertical mouse: rotates around camera X axis
    """

    def __init__(self, *args, visualizer=None, **kwargs):
        """
        Initialize the rotate gesture.

        Args:
            visualizer: Optional CreoRotateVisualizer to show visual feedback
        """
        super().__init__(*args, **kwargs)
        self._visualizer = visualizer
        self._visualizer_initialized = False
        self._total_movement = [0.0, 0.0]
        self._last_has_moved_state = False

    def on_began(self, mouse: Sequence[float] = None):
        """Called when gesture begins."""
        # Reset state
        self._visualizer_initialized = False
        self._total_movement = [0.0, 0.0]
        self._last_has_moved_state = False

        # Don't show visualizer yet - wait for raycast to complete
        # Will show in first _perform_gesture when we have world position

        # Call parent to perform raycast
        super().on_began(mouse)

    def on_ended(self):
        """Called when gesture ends."""
        # Hide visualizer
        if self._visualizer:
            self._visualizer.hide()
            self._visualizer.model.set_has_moved(False)

        super().on_ended()

    def _perform_gesture(self, mouse_moved: Sequence[float], rotation_center):
        """
        Perform rotation around the raycast hit point.

        Args:
            mouse_moved: Accumulated mouse movement (dx, dy)
            rotation_center: World space point to rotate around
        """
        # Creo rotation works in both perspective and orthographic
        # Don't check disable_tumble (Kit disables it in ortho, but we want it enabled)

        from pxr import Gf

        from .utils import flatten_matrix

        # Accumulate total movement
        self._total_movement[0] += mouse_moved[0]
        self._total_movement[1] += mouse_moved[1]

        # On first frame, set world position and show visualizer
        if self._visualizer and not self._visualizer_initialized:
            self._visualizer_initialized = True
            self._visualizer.model.set_world_position(rotation_center)
            self._visualizer.model.set_has_moved(False)
            self._visualizer.show()

        # Update has_moved based on total displacement
        elif self._visualizer and self._visualizer.visible:
            movement_threshold = 0.001
            has_moved = (
                abs(self._total_movement[0]) > movement_threshold or abs(self._total_movement[1]) > movement_threshold
            )
            if has_moved != self._last_has_moved_state:
                self._last_has_moved_state = has_moved
                self._visualizer.model.set_has_moved(has_moved)

        # Get rotation speed
        speed = self.tumble_speed

        # Calculate rotation angles in degrees
        horizontal_degrees = mouse_moved[0] * speed[0] * -90
        vertical_degrees = mouse_moved[1] * speed[1] * 90

        # Get current camera transform
        camera_transform = Gf.Matrix4d(*self.model.get_as_floats("transform"))

        # Convert world rotation center to camera space
        camera_space_center = camera_transform.GetInverse().Transform(rotation_center)

        # Build rotation transformation in camera space
        translate_to_center = Gf.Matrix4d().SetTranslate(-camera_space_center)
        translate_back = Gf.Matrix4d().SetTranslate(camera_space_center)

        # Rotations in camera space:
        # - Vertical mouse -> rotate around camera X axis (1, 0, 0)
        # - Horizontal mouse -> rotate around camera Y axis (0, 1, 0)
        rotate_x = Gf.Matrix4d().SetRotate(Gf.Rotation(Gf.Vec3d(1, 0, 0), vertical_degrees))
        rotate_y = Gf.Matrix4d().SetRotate(Gf.Rotation(Gf.Vec3d(0, 1, 0), horizontal_degrees))

        # Compose: translate to center, rotate, translate back
        rotation_transform = translate_to_center * rotate_x * rotate_y * translate_back

        # Apply to current transform
        new_transform = rotation_transform * camera_transform

        # Update model
        self.model.set_floats("transform", flatten_matrix(new_transform))
        self.model._item_changed("transform")

        # Update visualizer world position (stays at rotation center)
        if self._visualizer and self._visualizer.visible:
            self._visualizer.model.set_world_position(rotation_center)
