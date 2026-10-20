"""High-level command wrappers used by UI/controllers and external callers.

Wrapper functions bridge human-scale operations (create node, connect ports,
group selection, remove property) to low-level Kit command execution.

Why this package exists:
- raw Kit command returns are inconsistent across commands/builds,
- wrapper-level validation can assert authored USD state after command success,
- callers receive normalized `CommandResult` structures and richer diagnostics.

In short, wrappers are the reliability layer above `impl`.

Typical consumers: UI controllers, graph models, and tests that need predictable
command outcomes without coupling to low-level command-class behavior.
"""

from .attributes import (
    LockAttribute,
    RemoveProperty,
    RenameProperty,
    SetDescription,
    SetDisplayName,
    SetPrimCustomData,
    UnlockAttribute,
)
from .isolation import DeleteInputOutputNodes
from .material import CreateMaterial, PauseMaterial
from .nodes import CreateNode, CreateShader
from .ports import (
    ConnectInputToSource,
    ConnectPortToSource,
    CreateInputPort,
    CreateOutputPort,
    DisconnectInputPort,
    DisconnectSourcePort,
    RemoveConnections,
)
from .prims import DeletePrims, GroupNodeGraph, MovePrims, RenamePrim, UngroupNodeGraph
from .selection import SelectPrims
from .tasks import cleanup_command_tasks, track_command_task
from .ui_nodes import (
    CreateBackdrop,
    CreateNodeGraph,
    RemovePosition,
    SetDisplayColor,
    SetPosition,
    SetSize,
)

__all__ = [
    "ConnectInputToSource",
    "ConnectPortToSource",
    "CreateBackdrop",
    "CreateMaterial",
    "CreateNode",
    "CreateNodeGraph",
    "CreateInputPort",
    "CreateOutputPort",
    "CreateShader",
    "DeleteInputOutputNodes",
    "DeletePrims",
    "DisconnectInputPort",
    "DisconnectSourcePort",
    "GroupNodeGraph",
    "LockAttribute",
    "MovePrims",
    "PauseMaterial",
    "RemoveConnections",
    "RemovePosition",
    "RemoveProperty",
    "RenamePrim",
    "RenameProperty",
    "SelectPrims",
    "SetDescription",
    "SetDisplayColor",
    "SetDisplayName",
    "SetPrimCustomData",
    "SetPosition",
    "SetSize",
    "UngroupNodeGraph",
    "UnlockAttribute",
    "cleanup_command_tasks",
    "track_command_task",
]
