"""Prim command definitions for creating Material Graph stage primitives.

These commands author foundational USD prims (materials, shaders, nodegraphs)
from explicit types or SDR identifiers, then initialize required metadata so the
graph/editor layers can immediately model and render them.

Separating prim creation into command defs guarantees undo/redo safety and keeps
stage mutation logic out of UI controllers and delegates.

Typical consumers: node/material creation wrappers and controllers handling
catalog-driven or context-menu-driven prim instantiation.
"""

from .create import MaterialGraph_CreatePrimCommand
from .delete import MaterialGraph_DeletePrimsCommand
from .new_material import MaterialGraph_NewUsdShadeMaterialCommand
from .new_node import MaterialGraph_NewUsdShadeNodeCommand
from .new_node_from_sdr import MaterialGraph_NewUsdShadeNodeFromSdrCommand
from .new_nodegraph import MaterialGraph_NewUsdShadeNodeGraphCommand

__all__ = [
    "MaterialGraph_CreatePrimCommand",
    "MaterialGraph_DeletePrimsCommand",
    "MaterialGraph_NewUsdShadeMaterialCommand",
    "MaterialGraph_NewUsdShadeNodeCommand",
    "MaterialGraph_NewUsdShadeNodeFromSdrCommand",
    "MaterialGraph_NewUsdShadeNodeGraphCommand",
]
