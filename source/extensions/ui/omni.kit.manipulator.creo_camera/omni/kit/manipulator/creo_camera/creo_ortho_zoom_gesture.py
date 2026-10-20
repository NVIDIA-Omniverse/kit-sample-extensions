## Copyright (c) 2025, NVIDIA CORPORATION.  All rights reserved.
##
## NVIDIA CORPORATION and its licensors retain all intellectual property
## and proprietary rights in and to this software, related documentation
## and any modifications thereto.  Any use, reproduction, disclosure or
## distribution of this software and related documentation without an express
## license agreement from NVIDIA CORPORATION is strictly prohibited.
##

"""
Creo-style orthographic zoom gesture.

Zooms orthographic camera by adjusting aperture while keeping clicked point under cursor.
"""

__all__ = ["CreoOrthoZoomGesture"]

from typing import Sequence

from omni.kit.manipulator.camera import CameraGestureBase


class CreoOrthoZoomGesture(CameraGestureBase):
    """
    Creo-style zoom for orthographic cameras.

    Adjusts aperture and pans to keep clicked point under cursor during zoom.
    """

    def __init__(self, *args, visualizer=None, **kwargs):
        """
        Initialize the ortho zoom gesture.

        Args:
            visualizer: Optional CreoZoomVisualizer to show visual feedback
        """
        super().__init__(*args, **kwargs)
        self._initial_mouse_ndc = None
        self._initial_apertures = None
        self._initial_camera_position = None
        self._accumulated_distance = 0.0
        self._visualizer = visualizer
        self._accumulated_mouse_y = 0.0
        self._last_has_moved_state = False
        self._initial_transform = None

    def on_began(self, mouse: Sequence[float] = None):
        """Store initial state."""
        from pxr import Gf

        # Call parent first to initialize model
        super().on_began(mouse)

        # Store initial mouse position
        mouse_ndc = mouse if mouse else self.sender.gesture_payload.mouse
        self._initial_mouse_ndc = mouse_ndc

        # Store initial apertures and camera position
        apertures = self.model.get_as_floats("initial_aperture")
        if apertures and len(apertures) >= 2:
            self._initial_apertures = list(apertures)
            self._accumulated_distance = 0.0
            self._accumulated_mouse_y = 0.0
            self._last_has_moved_state = False

            # Store initial camera position and transform
            xf = self.model.get_as_floats("transform")
            if xf:
                self._initial_transform = Gf.Matrix4d(*xf)
                self._initial_camera_position = self._initial_transform.ExtractTranslation()

        # Show visualizer immediately
        # In ortho: both markers use NDC positioning
        if self._visualizer:
            # Fixed marker at initial click position (won't change)
            self._visualizer.model.set_fixed_ndc([mouse_ndc[0], mouse_ndc[1], 1.0])

            # Moving marker at initial position (will update each frame, Y only)
            self._visualizer.model.set_moving_ndc([mouse_ndc[0], mouse_ndc[1], 1.0])

            self._visualizer.model.set_has_moved(False)
            self._visualizer.show()

    def on_ended(self):
        """Called when gesture ends."""
        if self._visualizer:
            self._visualizer.hide()
            self._visualizer.model.set_has_moved(False)
        super().on_ended()

    def on_mouse_move(self, mouse_moved: Sequence[float]):
        """
        Zoom orthographic camera.

        Args:
            mouse_moved: Mouse movement (dx, dy) in NDC
        """
        if self.disable_zoom:
            return

        from pxr import Gf

        if not self._initial_apertures:
            return

        # Only use vertical movement for zoom
        vertical_delta = mouse_moved[1]

        # Accumulate Y movement
        self._accumulated_mouse_y += vertical_delta

        # Update visualizer
        if self._visualizer and self._visualizer.visible:
            # Update has_moved state
            movement_threshold = 0.001
            has_moved = abs(self._accumulated_mouse_y) > movement_threshold
            if has_moved != self._last_has_moved_state:
                self._last_has_moved_state = has_moved
                self._visualizer.model.set_has_moved(has_moved)

            # Update moving marker Y position (X stays at initial)
            current_ndc_y = self._initial_mouse_ndc[1] + self._accumulated_mouse_y
            self._visualizer.model.set_moving_ndc([self._initial_mouse_ndc[0], current_ndc_y, 1.0])

        # Get zoom speed
        move_speed = self.move_speed if hasattr(self, "move_speed") else (1.0, 1.0, 1.0)
        world_speed = self.world_speed if hasattr(self, "world_speed") else Gf.Vec3d(1.0, 1.0, 1.0)

        # Calculate zoom distance for this frame (inverted for ortho)
        zoom_speed_factor = move_speed[2] * world_speed.GetLength()
        frame_distance = -vertical_delta * zoom_speed_factor * 5.0  # Negative to invert direction

        # Accumulate total distance from start
        self._accumulated_distance += frame_distance

        # Apply ACCUMULATED zoom to INITIAL apertures
        from .utils import flatten_matrix

        new_apertures = self._initial_apertures.copy()
        for i in range(2):
            new_apertures[i] -= self._accumulated_distance * 2

        # Prevent apertures from going too small
        if new_apertures[0] <= 1.0 or new_apertures[1] <= 1.0:
            return

        # Calculate scale from initial apertures
        projection = self.model.get_as_floats("projection")
        if projection and len(projection) >= 16:
            scale_x = projection[0] * self._initial_apertures[0] / 2.0
            scale_y = projection[5] * self._initial_apertures[1] / 2.0
        else:
            scale_x = 1.0
            scale_y = 1.0

        # Calculate total pan from initial camera position
        pan_cam_x = self._initial_mouse_ndc[0] * (self._initial_apertures[0] - new_apertures[0]) / scale_x / 2.0
        pan_cam_y = self._initial_mouse_ndc[1] * (self._initial_apertures[1] - new_apertures[1]) / scale_y / 2.0

        # Convert to world space
        camera_transform = Gf.Matrix4d(*self.model.get_as_floats("transform"))
        camera_rotation = camera_transform.ExtractRotationMatrix()

        cam_right = camera_rotation.GetRow(0)
        cam_up = camera_rotation.GetRow(1)
        world_pan = (cam_right * pan_cam_x) + (cam_up * pan_cam_y)

        # Apply to initial camera position
        final_pos = self._initial_camera_position + world_pan

        new_transform = Gf.Matrix4d(1.0)
        new_transform.SetRotateOnly(camera_rotation)
        new_transform.SetTranslateOnly(final_pos)

        # Update transform and aperture
        self.model.set_floats("transform", flatten_matrix(new_transform))
        self.model.set_floats("current_aperture", new_apertures)

        # Trigger updates
        self.model._item_changed("transform")
        self.model._item_changed(self.model.get_item("current_aperture"))
