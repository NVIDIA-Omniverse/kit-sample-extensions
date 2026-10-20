## Copyright (c) 2025, NVIDIA CORPORATION.  All rights reserved.
##
## NVIDIA CORPORATION and its licensors retain all intellectual property
## and proprietary rights in and to this software, related documentation
## and any modifications thereto.  Any use, reproduction, disclosure or
## distribution of this software and related documentation without an express
## license agreement from NVIDIA CORPORATION is strictly prohibited.
##

"""
Creo-style pan gesture.

Implements camera panning that keeps the clicked 3D point under the mouse cursor.
"""

__all__ = ["CreoPanGesture"]

from typing import Sequence

from .creo_gesture_base import CreoGestureBase


class CreoPanGesture(CreoGestureBase):
    """
    Creo-style pan gesture.

    Keeps the clicked 3D point fixed under the mouse cursor during panning.
    """

    def __init__(self, *args, visualizer=None, **kwargs):
        """
        Initialize the pan gesture.

        Args:
            visualizer: Optional CreoPanVisualizer to show visual feedback
        """
        super().__init__(*args, **kwargs)
        self._initial_mouse_ndc = None  # Starting mouse position in NDC
        self._visualizer = visualizer
        self._visualizer_initialized = False
        self._total_movement = [0.0, 0.0]  # Total accumulated movement from start
        self._last_has_moved_state = False  # Cache last state to avoid unnecessary updates

    def on_began(self, mouse: Sequence[float] = None):
        """
        Called when gesture begins.

        Stores initial mouse position and shows visualizer with screen position.
        """
        # Store initial mouse position
        mouse_ndc = mouse if mouse else self.sender.gesture_payload.mouse
        self._initial_mouse_ndc = mouse_ndc
        self._visualizer_initialized = False
        self._total_movement = [0.0, 0.0]  # Reset total movement
        self._last_has_moved_state = False  # Reset state tracking

        # Show visualizer immediately with screen position
        # World position will be set later when raycast completes
        if self._visualizer:
            # Set screen NDC position (stays fixed on screen)
            self._visualizer.model.set_screen_ndc([mouse_ndc[0], mouse_ndc[1], 1.0])

            # Start with has_moved = False (red inner square)
            self._visualizer.model.set_has_moved(False)

            # Show the visualizer (world rect is hidden until we have world position)
            self._visualizer.show()

        # Call parent to perform raycast
        super().on_began(mouse)

    def on_ended(self):
        """
        Called when gesture ends.

        Hides the visualizer and resets state.
        """
        if self._visualizer:
            self._visualizer.hide()
            # Reset for next gesture
            self._visualizer.model.set_has_moved(False)
        super().on_ended()

    def _perform_gesture(self, mouse_moved: Sequence[float], target_world_pos):
        """
        Pan camera to keep target under cursor.

        Args:
            mouse_moved: Accumulated mouse movement (dx, dy) in NDC
            target_world_pos: World position that should stay under cursor
        """
        if self.disable_pan:
            return

        from pxr import Gf

        from .utils import flatten_matrix

        # Accumulate total movement from the start
        self._total_movement[0] += mouse_moved[0]
        self._total_movement[1] += mouse_moved[1]

        # On first frame, set world position (this will show the world rect)
        if self._visualizer and not self._visualizer_initialized:
            self._visualizer_initialized = True

            # Set world position (the raycast hit point)
            # This will make the world rect visible
            self._visualizer.model.set_world_position(target_world_pos)

        # Update has_moved based on total accumulated displacement from start
        if self._visualizer and self._visualizer.visible:
            # Check if total movement is significant
            # Use a small threshold to account for floating point precision and tiny movements
            movement_threshold = 0.001
            has_moved = (
                abs(self._total_movement[0]) > movement_threshold or abs(self._total_movement[1]) > movement_threshold
            )

            # Only update if state has changed to avoid unnecessary redraws
            if has_moved != self._last_has_moved_state:
                self._last_has_moved_state = has_moved
                self._visualizer.model.set_has_moved(has_moved)

        # Get current camera transform and projection
        camera_transform = Gf.Matrix4d(*self.model.get_as_floats("transform"))
        projection = Gf.Matrix4d(*self.model.get_as_floats("projection"))
        inv_projection = projection.GetInverse()

        # Current mouse position in NDC (initial + accumulated movement)
        current_mouse_ndc = [self._initial_mouse_ndc[0] + mouse_moved[0], self._initial_mouse_ndc[1] + mouse_moved[1]]

        # Unproject both positions to rays in camera space
        # Initial ray (where we clicked)
        initial_ndc = Gf.Vec3d(self._initial_mouse_ndc[0], self._initial_mouse_ndc[1], -1)
        initial_ray_dir = inv_projection.Transform(initial_ndc).GetNormalized()

        # Current ray (where cursor is now)
        current_ndc = Gf.Vec3d(current_mouse_ndc[0], current_mouse_ndc[1], -1)
        current_ray_dir = inv_projection.Transform(current_ndc).GetNormalized()

        # Convert target world position to camera space
        camera_space_target = camera_transform.GetInverse().Transform(target_world_pos)

        # Find where each ray intersects the plane at the target's depth
        target_depth = abs(camera_space_target[2])  # Z component is the depth

        # Scale rays to reach the target depth
        # ray_point.z = ray_dir.z * scale = -target_depth (negative Z is forward)
        initial_scale = -target_depth / initial_ray_dir[2] if initial_ray_dir[2] != 0 else 1
        current_scale = -target_depth / current_ray_dir[2] if current_ray_dir[2] != 0 else 1

        # Points where rays intersect the target's depth plane
        initial_point = initial_ray_dir * initial_scale
        current_point = current_ray_dir * current_scale

        # Translation needed to move current point to initial point
        translation = initial_point - current_point

        # Create translation matrix and apply to camera
        translation_matrix = Gf.Matrix4d().SetTranslate(translation)
        new_transform = translation_matrix * camera_transform

        # Update model
        self.model.set_floats("transform", flatten_matrix(new_transform))
        self.model._item_changed("transform")

        # Update visualizer world position (stays at original raycast point)
        if self._visualizer and self._visualizer.visible:
            self._visualizer.model.set_world_position(target_world_pos)
