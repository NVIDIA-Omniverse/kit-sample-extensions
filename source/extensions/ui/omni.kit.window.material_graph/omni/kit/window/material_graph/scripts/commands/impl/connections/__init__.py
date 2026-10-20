"""Connection command definitions for USDShade port wiring.

These command classes implement low-level authoring for connect/disconnect and
multi-remove flows over USDShade inputs/outputs. They are the undoable stage
mutation layer used by wrapper functions when creating or removing graph edges.

Keeping connection mutations in dedicated command defs centralizes semantics for
undo/redo and avoids scattering fragile USD connection logic across UI code.

Typical consumers: `scripts.commands.wrappers.ports` and nodegraph group/ungroup
helpers that need deterministic connection authoring.
"""

from .connect import MaterialGraph_ConnectUsdShadeToSourceCommand
from .connect_polymorphic import MaterialGraph_ConnectUsdShadeToSourcePolymorphicCommand
from .disconnect import MaterialGraph_UsdShadeDisconnectSourceCommand
from .remove import MaterialGraph_RemoveConnectionsCommand

__all__ = [
    "MaterialGraph_ConnectUsdShadeToSourceCommand",
    "MaterialGraph_ConnectUsdShadeToSourcePolymorphicCommand",
    "MaterialGraph_UsdShadeDisconnectSourceCommand",
    "MaterialGraph_RemoveConnectionsCommand",
]
