"""Model layer root for Material Graph data adaptation.

This package defines the core adapter layer between raw USD/UsdShade stage data
and UI-facing graph/catalog item models used by Kit widgets.

It is split into:
- `catalog` models for discoverable assets (textures/compounds/shaders),
- `graph` models for live stage-backed prims, attributes, and isolation views.

The model layer exists to translate stage/schema concepts into stable, testable,
widget-friendly objects instead of driving UI directly from raw USD APIs.

Typical consumers: graph/canvas UI widgets and controllers that need a consistent
item-model interface independent of raw USD object shapes.
"""

from .catalog import *  # noqa: F403
from .graph import *  # noqa: F403
