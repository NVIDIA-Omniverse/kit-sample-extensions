## Copyright (c) 2025, NVIDIA CORPORATION.  All rights reserved.
##
## NVIDIA CORPORATION and its licensors retain all intellectual property
## and proprietary rights in and to this software, related documentation
## and any modifications thereto.  Any use, reproduction, disclosure or
## distribution of this software and related documentation without an express
## license agreement from NVIDIA CORPORATION is strictly prohibited.
##

"""
Creo-style zoom gesture.

Zooms camera forward along camera Z axis, then pans to keep clicked point at same screen position.
Only uses vertical mouse movement.
Uses percentage-based zoom speed for context-aware behavior.
"""

__all__ = ["CreoZoomGesture"]

from typing import Sequence

from .creo_gesture_base import CreoGestureBase
from .creo_zoom_math import (
    adjust_coi_for_zoom,
    apply_zoom_with_pan_compensation,
    calculate_percentage_zoom_distance,
    get_coi_distance_from_model,
)

# Configuration
DRAG_ZOOM_PERCENT = 0.15  # Zoom 15% of reference distance per NDC unit of vertical drag
DRAG_ZOOM_SPEED_MULTIPLIER = 4.0  # Convert NDC delta to zoom amount (2x faster than scroll)


class CreoZoomGesture(CreoGestureBase):
    """
    Creo-style zoom gesture.

    Algorithm:
    1. Move camera forward along camera Z axis based on vertical mouse movement
    2. Pan to return clicked 3D point to its initial screen position (same as pan gesture)
    3. When target goes behind camera, maintain average direction from initial position
    4. Uses percentage-based zoom speed (15% of min(COI, target distance) per NDC unit)
    5. Asymmetric formula ensures dragging up then down returns to same position
    """

    def __init__(self, *args, visualizer=None, **kwargs):
        """
        Initialize the zoom gesture.

        Args:
            visualizer: Optional CreoZoomVisualizer to show visual feedback
        """
        super().__init__(*args, **kwargs)
        self._initial_mouse_ndc = None
        self._initial_camera_transform = None
        self._initial_camera_position = None
        self._accumulated_zoom = 0.0
        self._last_camera_position = None  # Store last final camera position
        self._visualizer = visualizer
        self._visualizer_initialized = False
        self._total_movement_y = 0.0  # Track Y movement only
        self._last_has_moved_state = False

    def on_began(self, mouse: Sequence[float] = None):
        """Store initial state and perform raycast."""
        from pxr import Gf

        # Call parent FIRST to let it initialize the model (via configure_model callback)
        super().on_began(mouse)

        # Store initial mouse position in NDC
        mouse_ndc = mouse if mouse else self.sender.gesture_payload.mouse
        self._initial_mouse_ndc = mouse_ndc

        # Store initial camera transform and position
        self._initial_camera_transform = Gf.Matrix4d(*self.model.get_as_floats("transform"))
        self._initial_camera_position = self._initial_camera_transform.ExtractTranslation()

        # Reset accumulated zoom and last position
        self._accumulated_zoom = 0.0
        self._last_camera_position = self._initial_camera_position

        # Reset visualizer state
        self._visualizer_initialized = False
        self._total_movement_y = 0.0
        self._last_has_moved_state = False

        # Show visualizer immediately with screen position
        if self._visualizer:
            # Set initial screen NDC position (X fixed, Y will change)
            self._visualizer.model.set_screen_ndc([mouse_ndc[0], mouse_ndc[1], 1.0])
            self._visualizer.model.set_has_moved(False)
            self._visualizer.show()

    def _perform_gesture(self, mouse_moved: Sequence[float], target_world_pos):
        """
        Perform zoom with pan compensation to keep target at initial screen position.

        Args:
            mouse_moved: Accumulated mouse movement (dx, dy) in NDC
            target_world_pos: World position to keep at initial screen position
        """
        if self.disable_zoom:
            return

        from pxr import Gf

        from .utils import flatten_matrix

        # Accumulate Y movement only
        self._total_movement_y += mouse_moved[1]

        # On first frame, set world position
        if self._visualizer and not self._visualizer_initialized:
            self._visualizer_initialized = True
            self._visualizer.model.set_world_position(target_world_pos)

        # Update has_moved based on Y displacement only
        if self._visualizer and self._visualizer.visible:
            movement_threshold = 0.001
            has_moved = abs(self._total_movement_y) > movement_threshold
            if has_moved != self._last_has_moved_state:
                self._last_has_moved_state = has_moved
                self._visualizer.model.set_has_moved(has_moved)

            # Update screen marker Y position (X stays fixed at initial)
            current_ndc_y = self._initial_mouse_ndc[1] + self._total_movement_y
            self._visualizer.model.set_screen_ndc([self._initial_mouse_ndc[0], current_ndc_y, 1.0])

        # Only use vertical movement for zoom
        vertical_delta = mouse_moved[1]

        # Calculate zoom distance using shared percentage-based logic
        # Vertical delta is in NDC space (-1 to 1 for full screen drag)
        # Negative vertical delta = drag down = zoom in (forward)
        # Positive vertical delta = drag up = zoom out (backward)

        # Convert vertical delta to zoom amount (4.0 makes it 2x faster than scroll)
        zoom_amount = -vertical_delta * DRAG_ZOOM_SPEED_MULTIPLIER

        # Get current transform for distance calculation
        current_transform = Gf.Matrix4d(*self.model.get_as_floats("transform"))
        coi_distance = get_coi_distance_from_model(self.model)

        # Calculate frame zoom distance using shared helper
        frame_zoom_distance = calculate_percentage_zoom_distance(
            zoom_amount, current_transform, target_world_pos, coi_distance, DRAG_ZOOM_PERCENT
        )

        # Update accumulated zoom from start
        self._accumulated_zoom += frame_zoom_distance

        # Get projection for unprojection calculations
        projection = Gf.Matrix4d(*self.model.get_as_floats("projection"))
        inv_projection = projection.GetInverse()

        # Step 1: Move camera forward/backward from INITIAL position
        # Use INITIAL camera transform, not current!
        initial_rotation = self._initial_camera_transform.ExtractRotationMatrix()
        camera_forward = -initial_rotation.GetRow(2)  # -Z is forward

        # Calculate new position from initial position using accumulated zoom
        new_camera_position = self._initial_camera_position + (camera_forward * self._accumulated_zoom)

        # Build camera transform after zoom (same rotation, new position)
        camera_after_zoom = Gf.Matrix4d(1.0)
        camera_after_zoom.SetRotateOnly(initial_rotation)
        camera_after_zoom.SetTranslateOnly(new_camera_position)

        # Step 2: Pan compensation (same logic as pan gesture)
        # Transform target to camera space after zoom
        camera_inv_after_zoom = camera_after_zoom.GetInverse()
        target_cam_space = camera_inv_after_zoom.Transform(target_world_pos)

        # Check if target is behind camera
        if target_cam_space[2] >= -0.01:  # Behind or too close
            # When behind camera, continue moving along average direction FROM last position
            # Average direction = last camera position minus initial camera position
            avg_direction = self._last_camera_position - self._initial_camera_position
            if avg_direction.GetLength() > 0.001:
                avg_direction = avg_direction.GetNormalized()

                # Continue from LAST position, move by frame zoom distance
                final_position = self._last_camera_position + (avg_direction * frame_zoom_distance)

                initial_rotation = self._initial_camera_transform.ExtractRotationMatrix()
                camera_after_zoom.SetRotateOnly(initial_rotation)
                camera_after_zoom.SetTranslateOnly(final_position)

                # Update last camera position for continuity
                self._last_camera_position = final_position
        else:
            # Target is in front - use shared zoom math for pan compensation
            # We already have camera_after_zoom positioned, just need pan adjustment
            temp_transform = Gf.Matrix4d(1.0)
            temp_transform.SetRotateOnly(initial_rotation)
            temp_transform.SetTranslateOnly(new_camera_position)

            # Apply pan compensation using shared function
            camera_after_zoom = apply_zoom_with_pan_compensation(
                temp_transform,
                projection,
                0.0,  # No additional zoom, just pan
                self._initial_mouse_ndc,
                target_world_pos,
            )

            # Store the final camera position for next frame
            self._last_camera_position = camera_after_zoom.ExtractTranslation()

        # Update the model with final transform
        self.model.set_floats("transform", flatten_matrix(camera_after_zoom))
        self.model._item_changed("transform")

        # Update visualizer world position
        if self._visualizer and self._visualizer.visible:
            self._visualizer.model.set_world_position(target_world_pos)

    def on_ended(self):
        """
        Called when gesture ends.

        Hides visualizer and adjusts center of interest.
        """
        # Hide visualizer
        if self._visualizer:
            self._visualizer.hide()
            self._visualizer.model.set_has_moved(False)
        # Adjust COI to track the world position we zoomed toward
        if self._world_position:
            adjust_coi_for_zoom(self.model, self._world_position)

        # Call parent to trigger undoable write
        super().on_ended()
