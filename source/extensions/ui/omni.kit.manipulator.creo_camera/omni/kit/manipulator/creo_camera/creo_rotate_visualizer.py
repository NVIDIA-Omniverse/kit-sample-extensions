## Copyright (c) 2025, NVIDIA CORPORATION.  All rights reserved.
##
## NVIDIA CORPORATION and its licensors retain all intellectual property
## and proprietary rights in and to this software, related documentation
## and any modifications thereto.  Any use, reproduction, disclosure or
## distribution of this software and related documentation without an express
## license agreement from NVIDIA CORPORATION is strictly prohibited.
##

"""
Rotate visualization manipulator for Creo-style camera.

Shows a single world space rectangle at the rotation center point.
"""

__all__ = ["CreoRotateVisualizerModel", "CreoRotateVisualizer"]

import omni.ui as ui
from omni.ui import scene as sc

from .creo_visualizer_base import CreoVisualizerBase, CreoVisualizerModelBase


class CreoRotateVisualizerModel(CreoVisualizerModelBase):
    """Model for rotate visualization - uses base class."""

    pass


class CreoRotateVisualizer(CreoVisualizerBase):
    """
    Visualizer for rotate gesture.

    Shows a single world space marker at the rotation center.
    """

    def __init__(self, **kwargs):
        """Initialize the visualizer."""
        if "model" not in kwargs:
            kwargs["model"] = CreoRotateVisualizerModel()
        super().__init__(**kwargs)
        self._world_rect_transform = None
        self._world_inner_rect = None

    def on_build(self):
        """Build the visualization elements."""
        self._root_transform = sc.Transform(visible=False)

        with self._root_transform:
            # World space marker at rotation center
            self._world_rect_transform = sc.Transform()
            with self._world_rect_transform:
                with sc.Transform(look_at=sc.Transform.LookAt.CAMERA):
                    with sc.Transform(scale_to=sc.Space.SCREEN):
                        with sc.Transform(transform=sc.Matrix44.get_rotation_matrix(0, 0, 45, True)):
                            self._world_inner_rect = self._build_nested_squares()

    def on_model_updated(self, item):
        """Update visualization when model changes."""
        if not self._root_transform:
            return

        if item == self.model.world_position:
            world_pos = self.model.get_as_floats(self.model.world_position)
            if self._world_rect_transform:
                self._world_rect_transform.transform = sc.Matrix44.get_translation_matrix(*world_pos)

        elif item == self.model.has_moved:
            self._update_inner_square_color(self._world_inner_rect)

    def destroy(self):
        """Clean up the visualizer."""
        super().destroy()
        self._world_rect_transform = None
        self._world_inner_rect = None
