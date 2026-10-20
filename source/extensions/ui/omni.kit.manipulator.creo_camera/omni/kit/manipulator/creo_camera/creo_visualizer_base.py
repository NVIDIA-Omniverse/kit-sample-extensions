## Copyright (c) 2025, NVIDIA CORPORATION.  All rights reserved.
##
## NVIDIA CORPORATION and its licensors retain all intellectual property
## and proprietary rights in and to this software, related documentation
## and any modifications thereto.  Any use, reproduction, disclosure or
## distribution of this software and related documentation without an express
## license agreement from NVIDIA CORPORATION is strictly prohibited.
##

"""
Base classes for Creo gesture visualizers.

Provides common functionality for nested square markers with color state.
"""

__all__ = ["CreoVisualizerModelBase", "CreoVisualizerBase"]

from typing import Sequence

import omni.ui as ui
from omni.ui import scene as sc


class CreoVisualizerModelBase(sc.AbstractManipulatorModel):
    """
    Base model for visualizers.

    Common items:
    - world_position: 3D world space position
    - has_moved: Boolean tracking if cursor has moved
    """

    class PositionItem(sc.AbstractManipulatorItem):
        """Item holding a 3D position."""

        def __init__(self, default_value=None):
            super().__init__()
            self.value = default_value if default_value else [0, 0, 0]

    class BoolItem(sc.AbstractManipulatorItem):
        """Item holding a boolean value."""

        def __init__(self, default_value=False):
            super().__init__()
            self.value = default_value

    def __init__(self):
        """Initialize the model."""
        super().__init__()
        self.world_position = CreoVisualizerModelBase.PositionItem()
        self.has_moved = CreoVisualizerModelBase.BoolItem(False)

    def get_item(self, identifier: str):
        """Get item by identifier."""
        if identifier == "world_position":
            return self.world_position
        elif identifier == "has_moved":
            return self.has_moved
        return None

    def get_as_floats(self, item):
        """Get item value as floats."""
        if item == self.world_position:
            return item.value
        return [0.0, 0.0, 0.0]

    def get_as_bool(self, item):
        """Get item value as bool."""
        if item == self.has_moved:
            return item.value
        return False

    def set_floats(self, item, value: Sequence[float]):
        """Set item value from floats."""
        if item == self.world_position:
            if value and len(value) >= 3:
                item.value = [value[0], value[1], value[2]]
                self._item_changed(item)

    def set_world_position(self, position: Sequence[float]):
        """Set world position and notify."""
        self.set_floats(self.world_position, position)

    def set_has_moved(self, moved: bool):
        """Set whether cursor has moved."""
        if self.has_moved.value != moved:
            self.has_moved.value = moved
            self._item_changed(self.has_moved)

    def destroy(self):
        """Clean up the model."""
        self.world_position = None
        self.has_moved = None


class CreoVisualizerBase(sc.Manipulator):
    """
    Base class for Creo gesture visualizers.

    Provides common nested squares rendering and color management.
    """

    # Visual configuration - 3 nested squares
    OUTER_SIZE = 40  # Black square
    MIDDLE_SIZE = 30  # White square
    INNER_SIZE = 20  # Green/Red square

    OUTER_COLOR = ui.color(0.0, 0.0, 0.0, 1.0)  # Black
    MIDDLE_COLOR = ui.color(1.0, 1.0, 1.0, 1.0)  # White
    INNER_COLOR_MOVED = ui.color(0.0, 1.0, 0.0, 1.0)  # Green when moved
    INNER_COLOR_NOT_MOVED = ui.color(1.0, 0.0, 0.0, 1.0)  # Red when not moved

    def __init__(self, **kwargs):
        """Initialize the visualizer."""
        super().__init__(**kwargs)
        self._root_transform = None

    def _build_nested_squares(self):
        """
        Build the 3 nested squares with Z-offset to prevent z-fighting.

        Returns:
            The inner rectangle reference for color updates
        """
        # Outer black square (z=0)
        with sc.Transform(transform=sc.Matrix44.get_translation_matrix(0, 0, 0)):
            sc.Rectangle(
                self.OUTER_SIZE,
                self.OUTER_SIZE,
                color=self.OUTER_COLOR,
                thickness=1,
            )
        # Middle white square (z=2)
        with sc.Transform(transform=sc.Matrix44.get_translation_matrix(0, 0, 2)):
            sc.Rectangle(
                self.MIDDLE_SIZE,
                self.MIDDLE_SIZE,
                color=self.MIDDLE_COLOR,
                thickness=1,
            )
        # Inner square (z=4, red/green based on movement)
        with sc.Transform(transform=sc.Matrix44.get_translation_matrix(0, 0, 4)):
            inner_rect = sc.Rectangle(
                self.INNER_SIZE,
                self.INNER_SIZE,
                color=self.INNER_COLOR_NOT_MOVED,
                thickness=1,
            )
        return inner_rect

    def show(self):
        """Make the visualizer visible."""
        if self._root_transform:
            self._root_transform.visible = True

    def hide(self):
        """Make the visualizer invisible."""
        if self._root_transform:
            self._root_transform.visible = False

    @property
    def visible(self) -> bool:
        """Get visibility state."""
        return self._root_transform.visible if self._root_transform else False

    @visible.setter
    def visible(self, value: bool):
        """Set visibility state."""
        if self._root_transform:
            self._root_transform.visible = bool(value)

    def _update_inner_square_color(self, *inner_rects):
        """
        Update inner square color(s) based on movement state.

        Args:
            *inner_rects: One or more inner rectangle references to update
        """
        has_moved = self.model.get_as_bool(self.model.has_moved)
        color = self.INNER_COLOR_MOVED if has_moved else self.INNER_COLOR_NOT_MOVED
        for rect in inner_rects:
            if rect:
                rect.color = color

    def destroy(self):
        """Clean up the visualizer."""
        if self._root_transform:
            self._root_transform.clear()
            self._root_transform = None
