## Copyright (c) 2025, NVIDIA CORPORATION.  All rights reserved.
##
## NVIDIA CORPORATION and its licensors retain all intellectual property
## and proprietary rights in and to this software, related documentation
## and any modifications thereto.  Any use, reproduction, disclosure or
## distribution of this software and related documentation without an express
## license agreement from NVIDIA CORPORATION is strictly prohibited.
##

"""
Creo-style orthographic pan gesture.

Implements camera panning for orthographic views.
"""

__all__ = ["CreoOrthoPanGesture"]

from typing import Sequence

from omni.kit.manipulator.camera import CameraGestureBase


class CreoOrthoPanGesture(CameraGestureBase):
    """
    Creo-style pan gesture for orthographic cameras.

    Pans camera in X/Y based on mouse movement and orthographic view size.
    """

    def __init__(self, *args, visualizer=None, **kwargs):
        """
        Initialize ortho pan gesture.

        Args:
            visualizer: Optional CreoPanVisualizer to show visual feedback
        """
        super().__init__(*args, **kwargs)
        self._initial_transform = None
        self._accumulated_mouse = [0.0, 0.0]
        self._initial_mouse_ndc = None
        self._visualizer = visualizer
        self._last_has_moved_state = False

    def on_began(self, mouse: Sequence[float] = None):
        """
        Called when gesture begins.

        WHY WE READ initial_transform INSTEAD OF transform:
        After pan-focus-pan sequence, model's 'transform' has stale value from previous pan,
        while 'initial_transform' was refreshed from USD by ViewportCameraManipulator._on_began.
        Using transform would cause camera to jump back to pre-focus position.
        """
        from pxr import Gf

        # Call parent to initialize model from USD
        super().on_began(mouse)

        # Store initial mouse position
        mouse_ndc = mouse if mouse else self.sender.gesture_payload.mouse
        self._initial_mouse_ndc = mouse_ndc

        # Read initial_transform (has correct USD value after focus)
        init_xf = self.model.get_as_floats("initial_transform")
        if init_xf:
            self._initial_transform = Gf.Matrix4d(*init_xf)

        # Reset accumulator
        self._accumulated_mouse = [0.0, 0.0]
        self._last_has_moved_state = False

        # Show visualizer immediately
        # In ortho: both markers use NDC positioning
        if self._visualizer:
            # Fixed marker at initial click position (won't change)
            self._visualizer.model.set_fixed_ndc([mouse_ndc[0], mouse_ndc[1], 1.0])

            # Moving marker at initial position (will update each frame)
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
        Pan camera in orthographic mode.

        Args:
            mouse_moved: Mouse movement (dx, dy) in NDC coordinates
        """
        if self.disable_pan:
            return

        if not self._initial_transform:
            return

        from pxr import Gf

        from .utils import flatten_matrix

        # Accumulate mouse movement from gesture start
        self._accumulated_mouse[0] += mouse_moved[0]
        self._accumulated_mouse[1] += mouse_moved[1]

        # Update visualizer
        if self._visualizer and self._visualizer.visible:
            # Update has_moved state
            movement_threshold = 0.001
            has_moved = (
                abs(self._accumulated_mouse[0]) > movement_threshold
                or abs(self._accumulated_mouse[1]) > movement_threshold
            )
            if has_moved != self._last_has_moved_state:
                self._last_has_moved_state = has_moved
                self._visualizer.model.set_has_moved(has_moved)

            # Update moving marker position (follows mouse in both X and Y)
            current_ndc_x = self._initial_mouse_ndc[0] + self._accumulated_mouse[0]
            current_ndc_y = self._initial_mouse_ndc[1] + self._accumulated_mouse[1]
            self._visualizer.model.set_moving_ndc([current_ndc_x, current_ndc_y, 1.0])

        # Get projection for view size calculation
        projection = Gf.Matrix4d(*self.model.get_as_floats("projection"))

        # Get orthographic view size
        ortho_width = 2.0 / projection[0][0] if projection[0][0] != 0 else 1.0
        ortho_height = 2.0 / projection[1][1] if projection[1][1] != 0 else 1.0

        # Calculate total pan from accumulated mouse movement
        camera_space_x = -self._accumulated_mouse[0] * ortho_width * 0.5
        camera_space_y = -self._accumulated_mouse[1] * ortho_height * 0.5

        camera_space_translation = Gf.Vec3d(camera_space_x, camera_space_y, 0.0)

        # Apply to initial transform (accumulated from start, like CreoZoomGesture)
        translation_matrix = Gf.Matrix4d().SetTranslate(camera_space_translation)
        new_transform = translation_matrix * self._initial_transform

        # Update both transform and initial_transform
        # Both must be updated because CameraGestureBase.on_began copies transform->initial_transform
        # If we only update transform, next gesture's on_began will copy stale transform to initial_transform
        self.model.set_floats("transform", flatten_matrix(new_transform))
        self.model.set_floats("initial_transform", flatten_matrix(new_transform))

        # Trigger updates (both must be notified for USD undo system)
        self.model._item_changed("transform")
        self.model._item_changed("initial_transform")
