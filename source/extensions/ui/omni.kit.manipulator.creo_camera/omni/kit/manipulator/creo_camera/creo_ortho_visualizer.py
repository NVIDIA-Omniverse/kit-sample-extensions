## Copyright (c) 2025, NVIDIA CORPORATION.  All rights reserved.
##
## NVIDIA CORPORATION and its licensors retain all intellectual property
## and proprietary rights in and to this software, related documentation
## and any modifications thereto.  Any use, reproduction, disclosure or
## distribution of this software and related documentation without an express
## license agreement from NVIDIA CORPORATION is strictly prohibited.
##

"""
Orthographic visualization manipulator for Creo-style camera.

Shows two screen-space rectangles:
1. Fixed at initial click position
2. Follows mouse cursor (or Y-only for zoom)
"""

__all__ = ["CreoOrthoVisualizerModel", "CreoOrthoVisualizer"]

from typing import Sequence

import omni.ui as ui
from omni.ui import scene as sc

from .creo_visualizer_base import CreoVisualizerBase, CreoVisualizerModelBase


class CreoOrthoVisualizerModel(CreoVisualizerModelBase):
    """
    Model for ortho visualization.

    Adds:
    - fixed_ndc: NDC position where gesture started (stays fixed)
    - moving_ndc: NDC position of current cursor (follows mouse)
    """

    def __init__(self):
        """Initialize the model."""
        super().__init__()
        self.fixed_ndc = CreoOrthoVisualizerModel.PositionItem()
        self.moving_ndc = CreoOrthoVisualizerModel.PositionItem()

    def get_item(self, identifier: str):
        """Get item by identifier."""
        if identifier == "fixed_ndc":
            return self.fixed_ndc
        elif identifier == "moving_ndc":
            return self.moving_ndc
        return super().get_item(identifier)

    def get_as_floats(self, item):
        """Get item value as floats."""
        if item in (self.fixed_ndc, self.moving_ndc):
            return item.value
        return super().get_as_floats(item)

    def set_floats(self, item, value: Sequence[float]):
        """Set item value from floats."""
        if item in (self.fixed_ndc, self.moving_ndc):
            if value and len(value) >= 3:
                item.value = [value[0], value[1], value[2]]
                self._item_changed(item)
        else:
            super().set_floats(item, value)

    def set_fixed_ndc(self, ndc: Sequence[float]):
        """Set fixed NDC position and notify."""
        self.set_floats(self.fixed_ndc, ndc)

    def set_moving_ndc(self, ndc: Sequence[float]):
        """Set moving NDC position and notify."""
        self.set_floats(self.moving_ndc, ndc)

    def destroy(self):
        """Clean up the model."""
        super().destroy()
        self.fixed_ndc = None
        self.moving_ndc = None


class CreoOrthoVisualizer(CreoVisualizerBase):
    """
    Visualizer for orthographic gestures.

    Shows two screen-space markers + connecting line.
    Both markers use NDC positioning (no world space).
    """

    def __init__(self, **kwargs):
        """Initialize the visualizer."""
        if "model" not in kwargs:
            kwargs["model"] = CreoOrthoVisualizerModel()
        super().__init__(**kwargs)
        self._fixed_transform = None
        self._fixed_rect_transform = None
        self._fixed_inner_rect = None
        self._moving_transform = None
        self._moving_rect_transform = None
        self._moving_inner_rect = None
        self._connecting_line = None

    def on_build(self):
        """Build the visualization elements."""
        self._root_transform = sc.Transform(visible=False)

        with self._root_transform:
            # Connecting line
            self._connecting_line = sc.Line([0, 0, 0], [0, 0, 0], color=ui.color(1.0, 0.0, 0.0, 1.0), thickness=1)

            # Fixed marker (at initial click position) - separate transform hierarchy
            self._fixed_rect_transform = sc.Transform()
            with self._fixed_rect_transform:
                self._fixed_transform = sc.Transform(look_at=sc.Transform.LookAt.CAMERA)
                with self._fixed_transform:
                    with sc.Transform(scale_to=sc.Space.SCREEN):
                        with sc.Transform(transform=sc.Matrix44.get_rotation_matrix(0, 0, 45, True)):
                            self._fixed_inner_rect = self._build_nested_squares()

            # Moving marker (follows cursor) - separate transform hierarchy
            self._moving_rect_transform = sc.Transform()
            with self._moving_rect_transform:
                self._moving_transform = sc.Transform(look_at=sc.Transform.LookAt.CAMERA)
                with self._moving_transform:
                    with sc.Transform(scale_to=sc.Space.SCREEN):
                        with sc.Transform(transform=sc.Matrix44.get_rotation_matrix(0, 0, 45, True)):
                            self._moving_inner_rect = self._build_nested_squares()

    def on_model_updated(self, item):
        """Update visualization when model changes."""
        if not self._root_transform or not self._fixed_transform or not self._moving_transform:
            return

        if item == self.model.fixed_ndc or item == self.model.moving_ndc:
            # Update BOTH positions together (camera may have moved)
            self._update_both_positions()

        elif item == self.model.has_moved:
            self._update_inner_square_color(self._fixed_inner_rect, self._moving_inner_rect)

    def _update_both_positions(self):
        """Update both marker positions and line together - all at once to prevent shaking."""
        if not self._fixed_rect_transform or not self._moving_rect_transform:
            return
        if not self._fixed_transform or not self._moving_transform or not self._connecting_line:
            return

        # Get both NDC positions once
        fixed_ndc = self.model.get_as_floats(self.model.fixed_ndc)
        moving_ndc = self.model.get_as_floats(self.model.moving_ndc)

        # Convert both to WORLD space once - use the same conversion for consistency
        fixed_world = self._fixed_transform.transform_space(
            sc.Space.NDC, sc.Space.WORLD, (fixed_ndc[0], fixed_ndc[1], 1.0)
        )
        moving_world = self._moving_transform.transform_space(
            sc.Space.NDC, sc.Space.WORLD, (moving_ndc[0], moving_ndc[1], 1.0)
        )

        # Set all three visual elements together using the same calculated positions
        self._fixed_rect_transform.transform = sc.Matrix44.get_translation_matrix(*fixed_world)
        self._moving_rect_transform.transform = sc.Matrix44.get_translation_matrix(*moving_world)
        self._connecting_line.start = fixed_world
        self._connecting_line.end = moving_world

    def show(self):
        """Make the visualizer visible and ensure positions are updated."""
        super().show()
        # Force position update to ensure both markers are positioned
        self._update_both_positions()

    def destroy(self):
        """Clean up the visualizer."""
        super().destroy()
        self._fixed_transform = None
        self._fixed_rect_transform = None
        self._fixed_inner_rect = None
        self._moving_transform = None
        self._moving_rect_transform = None
        self._moving_inner_rect = None
        self._connecting_line = None
