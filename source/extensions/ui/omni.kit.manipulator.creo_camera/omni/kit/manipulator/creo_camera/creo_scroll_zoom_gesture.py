## Copyright (c) 2025, NVIDIA CORPORATION.  All rights reserved.
##
## NVIDIA CORPORATION and its licensors retain all intellectual property
## and proprietary rights in and to this software, related documentation
## and any modifications thereto.  Any use, reproduction, disclosure or
## distribution of this software and related documentation without an express
## license agreement from NVIDIA CORPORATION is strictly prohibited.
##

"""
Creo-style scroll zoom gesture.

Uses ScrollGesture to handle mouse wheel zoom with raycast at mouse position.
"""

__all__ = ["CreoScrollZoomGesture"]

from typing import TYPE_CHECKING

from omni.ui import scene as sc
from pxr import Gf

from .creo_zoom_math import (
    adjust_coi_for_zoom,
    apply_zoom_with_pan_compensation,
    calculate_percentage_zoom_distance,
    get_coi_distance_from_model,
)

if TYPE_CHECKING:
    from omni.kit.widget.viewport.api import ViewportAPI


# Configuration
SCROLL_ZOOM_PERCENT = 0.15  # Zoom 15% of reference distance per scroll unit


class CreoScrollZoomGesture(sc.ScrollGesture):
    """
    Creo-style scroll zoom using ScrollGesture.

    Each scroll event:
    - Accumulates scrolls while raycast is in progress
    - Performs raycast at current mouse position
    - Zooms toward target with pan compensation
    - Uses percentage-based zoom speed (15% of min(COI, target distance) per scroll unit)
    - Asymmetric formula ensures forward/backward scrolling returns to same position
    - Completely stateless between scroll sequences
    """

    def __init__(self, model, viewport_api: "ViewportAPI", manipulator, *args, **kwargs):
        """
        Initialize scroll zoom gesture.

        Args:
            model: Camera manipulator model
            viewport_api: Viewport API for raycasts
            manipulator: Parent CreoCameraManipulator (for _on_began access)
        """
        super().__init__(*args, **kwargs)
        self.model = model
        self.viewport_api = viewport_api
        self.manipulator = manipulator
        self._accumulated_scroll = 0.0
        self._raycast_in_progress = False
        self._model_initialized = False

    def on_ended(self):
        """
        Called for each scroll event.

        Accumulates scroll and starts raycast if not already running.
        """
        # Refresh model from USD on EVERY scroll (like ortho scroll)
        # This ensures transform is current after focus/external changes
        mouse_ndc = self.sender.gesture_payload.mouse if self.sender and self.sender.gesture_payload else None
        if mouse_ndc and hasattr(self.manipulator, "_on_began"):
            self.manipulator._on_began(self.model, mouse_ndc)

            # Initialize ndc_scale on first scroll
            if not self._model_initialized:
                coi = self.model.get_as_floats("center_of_interest")
                if coi and len(coi) >= 3:
                    self.model.calculate_pixel_to_world(Gf.Vec3d(coi[0], coi[1], coi[2]))
                self._model_initialized = True

        scroll_amount = self.scroll[0]  # X component
        self._accumulated_scroll += scroll_amount

        # Start raycast if not already in progress
        if not self._raycast_in_progress:
            self._start_raycast()

    def _start_raycast(self):
        """Start raycast at current mouse position."""
        mouse_ndc = self.sender.gesture_payload.mouse if self.sender and self.sender.gesture_payload else None
        if not mouse_ndc:
            return

        mouse_pixel, viewport_api = self.viewport_api.map_ndc_to_texture_pixel(mouse_ndc)
        if not mouse_pixel or not viewport_api:
            return

        self._raycast_in_progress = True

        def raycast_complete(prim_path: str, world_pos, *args):
            """Called when raycast completes."""
            self._raycast_in_progress = False

            if prim_path and world_pos:
                if hasattr(world_pos, "x"):
                    target = Gf.Vec3d(world_pos.x, world_pos.y, world_pos.z)
                else:
                    target = Gf.Vec3d(*world_pos)
            else:
                target = self._compute_world_position_at_distance(mouse_ndc)

            self._perform_zoom(self._accumulated_scroll, mouse_ndc, target)
            self._accumulated_scroll = 0.0

        query_name = "omni.kit.manipulator.creo_camera.ScrollZoom"
        viewport_api.request_query(mouse_pixel, raycast_complete, query_name=query_name)

    def _compute_world_position_at_distance(self, mouse_ndc):
        """Compute world position at center_of_interest distance along mouse ray."""
        camera_transform = Gf.Matrix4d(*self.model.get_as_floats("transform"))
        center_of_interest = Gf.Vec3d(*self.model.get_as_floats("center_of_interest"))
        coi_distance = center_of_interest.GetLength()

        ndc_near = Gf.Vec3d(mouse_ndc[0], mouse_ndc[1], -1)
        projection = Gf.Matrix4d(*self.model.get_as_floats("projection"))
        inv_projection = projection.GetInverse()

        camera_space_point = inv_projection.Transform(ndc_near)
        ray_dir = camera_space_point.GetNormalized()

        world_pos = camera_transform.Transform(ray_dir * coi_distance)
        return world_pos

    def _perform_zoom(self, scroll_amount, mouse_ndc, target_world_pos):
        """
        Perform zoom operation using shared zoom math.

        Args:
            scroll_amount: Accumulated scroll amount
            mouse_ndc: Mouse position in NDC
            target_world_pos: World position to zoom toward
        """
        from .utils import flatten_matrix

        if abs(scroll_amount) < 0.01:
            return

        # Get current camera state (model already initialized in on_ended)
        xf = self.model.get_as_floats("transform")
        if xf:
            self.model.set_floats("initial_transform", xf.copy())

        current_transform = Gf.Matrix4d(*xf if xf else self.model.get_as_floats("transform"))
        projection = Gf.Matrix4d(*self.model.get_as_floats("projection"))

        # Calculate zoom distance using shared percentage-based logic
        # Negative scroll_amount = zoom in (forward, positive distance)
        # Positive scroll_amount = zoom out (backward, negative distance)
        coi_distance = get_coi_distance_from_model(self.model)
        zoom_distance = calculate_percentage_zoom_distance(
            -scroll_amount,  # Invert: scroll up = zoom in = positive
            current_transform,
            target_world_pos,
            coi_distance,
            SCROLL_ZOOM_PERCENT,
        )

        # Apply zoom with pan compensation using shared math
        new_transform = apply_zoom_with_pan_compensation(
            current_transform, projection, zoom_distance, mouse_ndc, target_world_pos
        )

        # Update model transform
        self.model.set_floats("transform", flatten_matrix(new_transform))

        # Adjust COI using Kit's object-centric mechanism
        # This stores the world anchor point and recalculates COI distance automatically
        adjust_coi_for_zoom(self.model, target_world_pos)

        # Trigger undo-able update - this writes both transform and adjusted COI to USD
        self.model.set_ints("interaction_ended", [1])
        self.model._item_changed("transform")
        self.model.set_ints("interaction_ended", [0])

        # Clear object-centric flag after write
        self.model.set_ints("object_centric_movement", [0])
