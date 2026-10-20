## Copyright (c) 2025, NVIDIA CORPORATION.  All rights reserved.
##
## NVIDIA CORPORATION and its licensors retain all intellectual property
## and proprietary rights in and to this software, related documentation
## and any modifications thereto.  Any use, reproduction, disclosure or
## distribution of this software and related documentation without an express
## license agreement from NVIDIA CORPORATION is strictly prohibited.
##

"""
Pan visualization manipulator for Creo-style camera.

Shows two rectangles during pan:
1. World space rectangle at the raycast hit point (follows mouse)
2. Screen space rectangle at the initial mouse position (fixed)
"""

__all__ = ["CreoPanVisualizerModel", "CreoPanVisualizer"]

from typing import Sequence

import omni.ui as ui
from omni.ui import scene as sc

from .creo_visualizer_base import CreoVisualizerBase, CreoVisualizerModelBase


class CreoPanVisualizerModel(CreoVisualizerModelBase):
    """
    Model for pan visualization.

    Adds:
    - screen_ndc: 2D NDC position of initial mouse click
    """

    def __init__(self):
        """Initialize the model."""
        super().__init__()
        self.screen_ndc = CreoPanVisualizerModel.PositionItem()

    def get_item(self, identifier: str):
        """Get item by identifier."""
        if identifier == "screen_ndc":
            return self.screen_ndc
        return super().get_item(identifier)

    def get_as_floats(self, item):
        """Get item value as floats."""
        if item == self.screen_ndc:
            return item.value
        return super().get_as_floats(item)

    def set_floats(self, item, value: Sequence[float]):
        """Set item value from floats."""
        if item == self.screen_ndc:
            if value and len(value) >= 3:
                item.value = [value[0], value[1], value[2]]
                self._item_changed(item)
        else:
            super().set_floats(item, value)

    def set_screen_ndc(self, ndc: Sequence[float]):
        """Set screen NDC position and notify."""
        self.set_floats(self.screen_ndc, ndc)

    def destroy(self):
        """Clean up the model."""
        super().destroy()
        self.screen_ndc = None


class CreoPanVisualizer(CreoVisualizerBase):
    """
    Visualizer for pan gesture.

    Shows two markers + connecting line.
    """

    def __init__(self, **kwargs):
        """Initialize the visualizer."""
        if "model" not in kwargs:
            kwargs["model"] = CreoPanVisualizerModel()
        super().__init__(**kwargs)
        self._world_rect_transform = None
        self._world_inner_rect = None
        self._screen_transform = None
        self._screen_rect_transform = None
        self._screen_inner_rect = None
        self._connecting_line = None
        self._world_visible = False

    def on_build(self):
        """Build the visualization elements."""
        # Root transform controls overall visibility
        self._root_transform = sc.Transform(visible=False)

        with self._root_transform:
            # Connecting line between the two markers (hidden until world rect is visible)
            self._connecting_line = sc.Line(
                [0, 0, 0], [0, 0, 0], color=ui.color(1.0, 0.0, 0.0, 1.0), thickness=1, visible=False
            )

            # World space squares (follows mouse cursor to raycast point)
            # Initially hidden until we get world position from raycast
            self._world_rect_transform = sc.Transform(visible=False)
            with self._world_rect_transform:
                with sc.Transform(look_at=sc.Transform.LookAt.CAMERA):
                    with sc.Transform(scale_to=sc.Space.SCREEN):
                        with sc.Transform(transform=sc.Matrix44.get_rotation_matrix(0, 0, 45, True)):
                            self._world_inner_rect = self._build_nested_squares()

            # Screen space squares (stays at initial mouse position)
            # Uses camera-facing transform and NDC->WORLD conversion like SelectionManipulator
            self._screen_rect_transform = sc.Transform()
            with self._screen_rect_transform:
                self._screen_transform = sc.Transform(look_at=sc.Transform.LookAt.CAMERA)
                with self._screen_transform:
                    with sc.Transform(scale_to=sc.Space.SCREEN):
                        with sc.Transform(transform=sc.Matrix44.get_rotation_matrix(0, 0, 45, True)):
                            self._screen_inner_rect = self._build_nested_squares()

    def on_model_updated(self, item):
        """
        Update visualization when model changes.

        Args:
            item: The model item that changed
        """
        if not self._root_transform or not self._screen_transform:
            return

        # Update world rectangle position
        if item == self.model.world_position:
            world_pos = self.model.get_as_floats(self.model.world_position)
            if self._world_rect_transform:
                self._world_rect_transform.transform = sc.Matrix44.get_translation_matrix(*world_pos)
                # Show world rect now that we have a position
                if not self._world_visible:
                    self._world_rect_transform.visible = True
                    self._world_visible = True
                    # Also show the connecting line
                    if self._connecting_line:
                        self._connecting_line.visible = True
            # Update connecting line end point
            self._update_connecting_line()

        # Update screen rectangle position (convert NDC to WORLD space)
        elif item == self.model.screen_ndc:
            self._update_screen_rect_position()
            # Update connecting line start point
            self._update_connecting_line()

        # Update inner square colors based on movement
        elif item == self.model.has_moved:
            self._update_inner_square_color(self._world_inner_rect, self._screen_inner_rect)

    def _get_screen_world_position(self):
        """
        Get screen marker position in world space.

        Returns:
            Tuple of (x, y, z) in world space
        """
        ndc = self.model.get_as_floats(self.model.screen_ndc)
        return self._screen_transform.transform_space(sc.Space.NDC, sc.Space.WORLD, (ndc[0], ndc[1], 1.0))

    def _update_screen_rect_position(self):
        """Update screen rectangle position from NDC."""
        if not self._screen_rect_transform or not self._screen_transform:
            return

        obj_pos = self._get_screen_world_position()
        self._screen_rect_transform.transform = sc.Matrix44.get_translation_matrix(*obj_pos)

    def _update_connecting_line(self):
        """Update the connecting line between the two markers."""
        if not self._connecting_line or not self._screen_transform:
            return

        # Get both positions in world space
        screen_world_pos = self._get_screen_world_position()
        world_pos = self.model.get_as_floats(self.model.world_position)

        # Update line endpoints
        self._connecting_line.start = screen_world_pos
        self._connecting_line.end = world_pos

    def show(self, show_world_immediately=False):
        """
        Make the visualizer visible.

        Args:
            show_world_immediately: If True, show world marker immediately (for ortho)
        """
        super().show()

        # For ortho gestures, show world marker immediately
        if show_world_immediately and self._world_rect_transform:
            self._world_rect_transform.visible = True
            self._world_visible = True
            if self._connecting_line:
                self._connecting_line.visible = True

    def hide(self):
        """Make the visualizer invisible."""
        super().hide()
        # Reset world rect and line visibility for next time
        if self._world_rect_transform:
            self._world_rect_transform.visible = False
            self._world_visible = False
        if self._connecting_line:
            self._connecting_line.visible = False

    def destroy(self):
        """Clean up the visualizer."""
        super().destroy()
        self._world_rect_transform = None
        self._world_inner_rect = None
        self._screen_transform = None
        self._screen_rect_transform = None
        self._screen_inner_rect = None
        self._connecting_line = None
