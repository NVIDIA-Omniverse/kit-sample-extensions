"""Drop handlers for catalog, path, payload, and texture drag-and-drop.

This package provides handlers that respond to drag-and-drop events on the
graph canvas: creating nodes from catalog items, resolving file paths,
parsing JSON payloads, and creating texture nodes. Handlers are composed
into the graph widget's drop pipeline.

Architectural role: Drop handlers translate raw drop events into command
invocations and model updates. They sit between the graph widget and
node-creation/command layers.

Typical consumers: GraphWidget drop configuration, PayloadDropHandler
composition, and tests that verify drop behavior.
"""

from .catalog import CatalogCreationHandler
from .paths import PathDropHandler
from .payloads import PayloadDropHandler
from .textures import TextureDropHandler

__all__ = [
    "CatalogCreationHandler",
    "PathDropHandler",
    "PayloadDropHandler",
    "TextureDropHandler",
]
