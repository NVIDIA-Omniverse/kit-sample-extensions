## Copyright (c) 2025, NVIDIA CORPORATION.  All rights reserved.
##
## NVIDIA CORPORATION and its licensors retain all intellectual property
## and proprietary rights in and to this software, related documentation
## and any modifications thereto.  Any use, reproduction, disclosure or
## distribution of this software and related documentation without an express
## license agreement from NVIDIA CORPORATION is strictly prohibited.
##

"""
Creo-style orthographic scroll zoom gesture.

Handles mouse wheel zoom in orthographic mode.
"""

__all__ = ["CreoOrthoScrollZoomGesture"]

from typing import TYPE_CHECKING

from omni.ui import scene as sc
from pxr import Gf

if TYPE_CHECKING:
    from omni.kit.widget.viewport.api import ViewportAPI


class CreoOrthoScrollZoomGesture(sc.ScrollGesture):
    """
    Creo-style scroll zoom for orthographic cameras.

    Each scroll adjusts aperture and pans to zoom around cursor position.
    """

    def __init__(self, model, viewport_api: "ViewportAPI", manipulator, *args, **kwargs):
        """
        Initialize ortho scroll zoom gesture.

        Args:
            model: Camera manipulator model
            viewport_api: Viewport API
            manipulator: Parent CreoCameraManipulator (for _on_began access)
        """
        super().__init__(*args, **kwargs)
        self.model = model
        self.viewport_api = viewport_api
        self.manipulator = manipulator

    def on_ended(self):
        """Called for each scroll event."""
        # Refresh model from USD on EVERY scroll (apertures change with focus/external ops)
        mouse_ndc = self.sender.gesture_payload.mouse if self.sender and self.sender.gesture_payload else None
        if mouse_ndc and hasattr(self.manipulator, "_on_began"):
            self.manipulator._on_began(self.model, mouse_ndc)

        scroll_amount = self.scroll[0]

        if abs(scroll_amount) < 0.01:
            return

        if not mouse_ndc:
            return

        self._perform_zoom(scroll_amount, mouse_ndc)

    def _perform_zoom(self, scroll_amount, mouse_ndc):
        """
        Perform orthographic scroll zoom.

        Args:
            scroll_amount: Scroll amount
            mouse_ndc: Mouse position in NDC
        """
        # Always read initial_aperture (refreshed from USD by _on_began)
        apertures = self.model.get_as_floats("initial_aperture")

        if not apertures or len(apertures) < 2:
            return

        # Calculate zoom distance (inverted for ortho)
        zoom_distance = -scroll_amount * 500.0  # Negative to invert direction

        # Apply to apertures
        new_apertures = list(apertures)
        for i in range(2):
            new_apertures[i] -= zoom_distance * 2

        # Prevent too small
        if new_apertures[0] <= 1.0 or new_apertures[1] <= 1.0:
            return

        # Calculate scale from initial_aperture
        projection = self.model.get_as_floats("projection")
        if projection and len(projection) >= 16:
            scale_x = projection[0] * apertures[0] / 2.0
            scale_y = projection[5] * apertures[1] / 2.0
        else:
            scale_x = 10.0
            scale_y = 20.88

        # Calculate pan to keep mouse point at same position
        pan_cam_x = mouse_ndc[0] * (apertures[0] - new_apertures[0]) / scale_x / 2.0
        pan_cam_y = mouse_ndc[1] * (apertures[1] - new_apertures[1]) / scale_y / 2.0

        # Convert to world space
        from .utils import flatten_matrix

        camera_transform = Gf.Matrix4d(*self.model.get_as_floats("transform"))
        camera_rotation = camera_transform.ExtractRotationMatrix()
        current_pos = camera_transform.ExtractTranslation()

        cam_right = camera_rotation.GetRow(0)
        cam_up = camera_rotation.GetRow(1)
        world_pan = (cam_right * pan_cam_x) + (cam_up * pan_cam_y)

        final_pos = current_pos + world_pan

        new_transform = Gf.Matrix4d(1.0)
        new_transform.SetRotateOnly(camera_rotation)
        new_transform.SetTranslateOnly(final_pos)

        # Setup for undo
        xf = self.model.get_as_floats("transform")
        if xf:
            self.model.set_floats("initial_transform", xf)

        # Update transform and current_aperture
        self.model.set_floats("transform", flatten_matrix(new_transform))
        self.model.set_floats("current_aperture", new_apertures)

        # Trigger undo-able updates
        self.model.set_ints("interaction_ended", [1])
        self.model._item_changed("transform")
        self.model._item_changed("current_aperture")
        self.model.set_ints("interaction_ended", [0])
