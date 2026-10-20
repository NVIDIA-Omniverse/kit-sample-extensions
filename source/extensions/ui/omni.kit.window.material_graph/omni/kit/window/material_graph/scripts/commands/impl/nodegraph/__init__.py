"""NodeGraph command definitions for grouping, ungrouping, and import flows.

These commands encapsulate complex graph-topology rewrites where multiple USD
connections must be preserved while nodes are grouped into, or extracted from,
UsdShade NodeGraph prims. They also include import helpers for bringing external
compound nodegraphs into the active stage.

The package exists because nodegraph transforms require coordinated edits across
prims, ports, and connection edges that must remain undoable and deterministic.

Typical consumers: grouping/ungrouping wrappers and controller flows that create
or import compound nodegraphs.
"""

from .group import MaterialGraph_GroupNodeGraphCommand
from .helpers import _normalize_connected_sources
from .import_ import MaterialGraph_ImportNodeGraphCommand
from .ungroup import MaterialGraph_UngroupNodeGraphCommand

__all__ = [
    "MaterialGraph_GroupNodeGraphCommand",
    "MaterialGraph_ImportNodeGraphCommand",
    "MaterialGraph_UngroupNodeGraphCommand",
    "_normalize_connected_sources",
]
