## Copyright (c) 2025, NVIDIA CORPORATION.  All rights reserved.
##
## NVIDIA CORPORATION and its licensors retain all intellectual property
## and proprietary rights in and to this software, related documentation
## and any modifications thereto.  Any use, reproduction, disclosure or
## distribution of this software and related documentation without an express
## license agreement from NVIDIA CORPORATION is strictly prohibited.
##

"""
Creo-style camera manipulator using proper Kit APIs.

This implementation extends ViewportCameraManipulator and customizes it
to use custom Creo gestures with middle mouse button.
"""

from typing import TYPE_CHECKING

import carb.input
import omni.ui as ui
from omni.kit.manipulator.camera import ViewportCameraManipulator
from omni.ui import scene as sc

from .creo_gesture_manager import CreoGestureManager
from .creo_ortho_pan_gesture import CreoOrthoPanGesture
from .creo_ortho_scroll_zoom_gesture import CreoOrthoScrollZoomGesture
from .creo_ortho_visualizer import CreoOrthoVisualizer
from .creo_ortho_zoom_gesture import CreoOrthoZoomGesture
from .creo_pan_gesture import CreoPanGesture
from .creo_pan_visualizer import CreoPanVisualizer
from .creo_rotate_gesture import CreoRotateGesture
from .creo_rotate_visualizer import CreoRotateVisualizer
from .creo_scroll_zoom_gesture import CreoScrollZoomGesture
from .creo_zoom_gesture import CreoZoomGesture
from .creo_zoom_visualizer import CreoZoomVisualizer

if TYPE_CHECKING:
    from omni.kit.widget.viewport.api import ViewportAPI


class CreoCameraManipulator(ViewportCameraManipulator):
    """
    Creo-style camera manipulator - extends ViewportCameraManipulator.

    Overrides on_build to create custom gestures with middle mouse.
    All USD integration, model updates, etc. are inherited.
    """

    def __init__(self, viewport_api: "ViewportAPI", **kwargs):
        """
        Initialize the Creo camera manipulator.

        Args:
            viewport_api: The viewport API instance
        """
        super().__init__(viewport_api, **kwargs)
        # Initialize transform so we don't need to check in destroy
        self.__transform = None
        self.viewport_api = viewport_api
        self._pan_visualizer = None
        self._rotate_visualizer = None
        self._zoom_visualizer = None
        self._ortho_pan_visualizer = None
        self._ortho_zoom_visualizer = None

    def on_build(self):
        """
        Build the manipulator with custom gestures.

        Creates own transform and screen with pan, rotate, and zoom gestures.
        """
        # Create gesture manager for proper perspective/ortho gesture handling
        gesture_manager = CreoGestureManager(self.viewport_api)

        # Create our own transform reference
        self.__transform = sc.Transform()

        with self.__transform:
            # Create visualizers for perspective gestures
            self._pan_visualizer = CreoPanVisualizer()
            self._rotate_visualizer = CreoRotateVisualizer()
            self._zoom_visualizer = CreoZoomVisualizer()

            # Create visualizers for orthographic gestures (simpler, NDC-only)
            self._ortho_pan_visualizer = CreoOrthoVisualizer()
            self._ortho_zoom_visualizer = CreoOrthoVisualizer()

            # Perspective pan (with raycast)
            pan_gesture = CreoPanGesture(
                self.model,
                self._on_began,
                mouse_button=2,
                modifiers=carb.input.KEYBOARD_MODIFIER_FLAG_SHIFT,
                manager=gesture_manager,
                viewport_api=self.viewport_api,
                visualizer=self._pan_visualizer,
            )
            # Orthographic pan (no raycast needed)
            ortho_pan_gesture = CreoOrthoPanGesture(
                self.model,
                self._on_began,
                mouse_button=2,
                modifiers=carb.input.KEYBOARD_MODIFIER_FLAG_SHIFT,
                manager=gesture_manager,
                visualizer=self._ortho_pan_visualizer,
            )
            rotate_gesture = CreoRotateGesture(
                self.model,
                self._on_began,
                mouse_button=2,
                modifiers=0,
                manager=gesture_manager,
                viewport_api=self.viewport_api,
                visualizer=self._rotate_visualizer,
            )
            # Perspective zoom (drag)
            zoom_gesture = CreoZoomGesture(
                self.model,
                self._on_began,
                mouse_button=2,
                modifiers=carb.input.KEYBOARD_MODIFIER_FLAG_CONTROL,
                manager=gesture_manager,
                viewport_api=self.viewport_api,
                visualizer=self._zoom_visualizer,
            )
            # Orthographic zoom (drag)
            ortho_zoom_gesture = CreoOrthoZoomGesture(
                self.model,
                self._on_began,
                mouse_button=2,
                modifiers=carb.input.KEYBOARD_MODIFIER_FLAG_CONTROL,
                manager=gesture_manager,
                visualizer=self._ortho_zoom_visualizer,
            )
            # Perspective scroll zoom
            scroll_zoom_gesture = CreoScrollZoomGesture(
                self.model,
                self.viewport_api,
                self,
                manager=gesture_manager,
            )
            # Orthographic scroll zoom
            ortho_scroll_zoom_gesture = CreoOrthoScrollZoomGesture(
                self.model,
                self.viewport_api,
                self,
                manager=gesture_manager,
            )
            # Screen captures all viewport input
            # Perspective and ortho gestures registered - manager handles prevention
            self._screen = sc.Screen(
                gestures=[
                    rotate_gesture,
                    pan_gesture,
                    ortho_pan_gesture,
                    zoom_gesture,
                    ortho_zoom_gesture,
                    scroll_zoom_gesture,
                    ortho_scroll_zoom_gesture,
                ]
            )

    def destroy(self):
        """Clean up, including our transform and visualizers."""
        if self._pan_visualizer:
            self._pan_visualizer.destroy()
            self._pan_visualizer = None
        if self._rotate_visualizer:
            self._rotate_visualizer.destroy()
            self._rotate_visualizer = None
        if self._zoom_visualizer:
            self._zoom_visualizer.destroy()
            self._zoom_visualizer = None
        if self._ortho_pan_visualizer:
            self._ortho_pan_visualizer.destroy()
            self._ortho_pan_visualizer = None
        if self._ortho_zoom_visualizer:
            self._ortho_zoom_visualizer.destroy()
            self._ortho_zoom_visualizer = None
        if self.__transform:
            self.__transform.clear()
            self.__transform = None
        super().destroy()


def CreoCameraFactory(desc: dict) -> "CreoCameraManipulator":
    """
    Factory function for creating CreoCameraManipulator.

    Args:
        desc: Dictionary containing 'viewport_api' and other factory args

    Returns:
        CreoCameraManipulator instance
    """
    return CreoCameraManipulator(desc.get("viewport_api"))
