"""Overlay controllers for drag/drop visual feedback.

These controllers render non-model visual affordances that communicate whether
the current drag target accepts a drop (for example catalog tinting and graph
background indication).

Keeping overlays in their own package avoids coupling transient visual feedback
to node-creation logic or core graph/canvas rendering code.

Typical consumers: drag/drop controllers and graph widget mixins that show
accept/reject feedback during hover and drop operations.
"""

from .catalog_drop_overlay import CatalogDropOverlayController
from .graph_background_drop_indicator import GraphBackgroundDropIndicatorController

__all__ = [
    "CatalogDropOverlayController",
    "GraphBackgroundDropIndicatorController",
]
