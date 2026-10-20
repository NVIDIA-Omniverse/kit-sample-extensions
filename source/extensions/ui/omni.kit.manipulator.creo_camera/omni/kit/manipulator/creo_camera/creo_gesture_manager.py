## Copyright (c) 2025, NVIDIA CORPORATION.  All rights reserved.
##
## NVIDIA CORPORATION and its licensors retain all intellectual property
## and proprietary rights in and to this software, related documentation
## and any modifications thereto.  Any use, reproduction, disclosure or
## distribution of this software and related documentation without an express
## license agreement from NVIDIA CORPORATION is strictly prohibited.
##

"""
Gesture manager for Creo camera manipulator.

Handles prevention logic for perspective vs orthographic gestures.
"""

__all__ = ["CreoGestureManager"]

from omni.ui import scene as sc

from .creo_ortho_pan_gesture import CreoOrthoPanGesture
from .creo_ortho_scroll_zoom_gesture import CreoOrthoScrollZoomGesture
from .creo_ortho_zoom_gesture import CreoOrthoZoomGesture
from .creo_pan_gesture import CreoPanGesture
from .creo_scroll_zoom_gesture import CreoScrollZoomGesture
from .creo_zoom_gesture import CreoZoomGesture


class CreoGestureManager(sc.GestureManager):
    """
    Gesture manager for Creo camera manipulator.

    Ensures mutual exclusion between perspective and orthographic gestures:
    - In perspective mode: CreoPanGesture works, CreoOrthoPanGesture is prevented
    - In orthographic mode: CreoOrthoPanGesture works, CreoPanGesture is prevented
    """

    def __init__(self, viewport_api):
        """
        Initialize gesture manager.

        Args:
            viewport_api: ViewportAPI instance to check projection
        """
        super().__init__()
        self.viewport_api = viewport_api

    def can_be_prevented(self, gesture):
        """
        Determines if a gesture can be prevented.

        Args:
            gesture: The gesture to evaluate

        Returns:
            bool: True if gesture can be prevented
        """
        # For scroll gestures, allow prevention even in ENDED state
        # (each scroll is a separate event)
        is_scroll = isinstance(gesture, (CreoScrollZoomGesture, CreoOrthoScrollZoomGesture))

        if is_scroll:
            # Scroll gestures can always be prevented (they're discrete events)
            return gesture.state != sc.GestureState.CHANGED
        else:
            # Don't prevent drag gestures in the middle of operation
            return (
                gesture.state != sc.GestureState.CHANGED
                and gesture.state != sc.GestureState.ENDED
                and gesture.state != sc.GestureState.CANCELED
            )

    def should_prevent(self, gesture, preventer):
        """
        Decides if a gesture should be prevented.

        For pan gestures with same bindings, only allow the one matching camera mode.

        Args:
            gesture: The gesture that may be prevented
            preventer: The gesture attempting to prevent

        Returns:
            bool: True if gesture should be prevented
        """
        # Check gesture types
        is_persp_pan = isinstance(gesture, CreoPanGesture)
        is_ortho_pan = isinstance(gesture, CreoOrthoPanGesture)
        is_persp_zoom = isinstance(gesture, (CreoZoomGesture, CreoScrollZoomGesture))
        is_ortho_zoom = isinstance(gesture, (CreoOrthoZoomGesture, CreoOrthoScrollZoomGesture))

        preventer_is_persp_pan = isinstance(preventer, CreoPanGesture)
        preventer_is_ortho_pan = isinstance(preventer, CreoOrthoPanGesture)
        preventer_is_persp_zoom = isinstance(preventer, (CreoZoomGesture, CreoScrollZoomGesture))
        preventer_is_ortho_zoom = isinstance(preventer, (CreoOrthoZoomGesture, CreoOrthoScrollZoomGesture))

        # Check if we have conflicting gesture pairs (same bindings, different modes)
        is_conflicting_pair = (
            (is_persp_pan or is_ortho_pan) and (preventer_is_persp_pan or preventer_is_ortho_pan)
        ) or ((is_persp_zoom or is_ortho_zoom) and (preventer_is_persp_zoom or preventer_is_ortho_zoom))

        if is_conflicting_pair:
            # Check camera mode from viewport_api
            if self.viewport_api and self.viewport_api.projection:
                projection = self.viewport_api.projection
                # projection[3][3] is 1 for ortho, 0 for perspective
                is_ortho = projection[3][3] == 1.0

                # In perspective mode: prevent ortho gestures, allow perspective gestures
                if not is_ortho:
                    if (is_ortho_pan or is_ortho_zoom) and (preventer_is_persp_pan or preventer_is_persp_zoom):
                        return True
                # In orthographic mode: prevent perspective gestures, allow ortho gestures
                else:
                    if (is_persp_pan or is_persp_zoom) and (preventer_is_ortho_pan or preventer_is_ortho_zoom):
                        return True

                return False

        # Default prevention logic
        return super().should_prevent(gesture, preventer)
