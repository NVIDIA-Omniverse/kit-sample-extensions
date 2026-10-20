"""Internal command registration for material graph command classes."""

from .backdrop import MaterialGraph_CreateUsdUIBackdropCommand
from .connections import (
    MaterialGraph_ConnectUsdShadeToSourceCommand,
    MaterialGraph_ConnectUsdShadeToSourcePolymorphicCommand,
    MaterialGraph_RemoveConnectionsCommand,
    MaterialGraph_UsdShadeDisconnectSourceCommand,
)
from .isolation import MaterialGraph_IsolationModelRemoveCommand
from .layer_transaction import MaterialGraph_CommitLayerTransactionCommand
from .metadata import MaterialGraph_SetPrimCustomDataCommand, MaterialGraph_SetPrimCustomDataKeyCommand
from .nodegraph import (
    MaterialGraph_GroupNodeGraphCommand,
    MaterialGraph_ImportNodeGraphCommand,
    MaterialGraph_UngroupNodeGraphCommand,
)
from .ports import (
    MaterialGraph_CreateInputPortCommand,
    MaterialGraph_CreateOutputPortCommand,
    MaterialGraph_RenamePropertyCommand,
)
from .prim import (
    MaterialGraph_CreatePrimCommand,
    MaterialGraph_DeletePrimsCommand,
    MaterialGraph_NewUsdShadeMaterialCommand,
    MaterialGraph_NewUsdShadeNodeCommand,
    MaterialGraph_NewUsdShadeNodeFromSdrCommand,
    MaterialGraph_NewUsdShadeNodeGraphCommand,
)
from .solo import MaterialGraph_SoloContextCommand

_REGISTERED_COMMANDS = (
    MaterialGraph_CreatePrimCommand,
    MaterialGraph_DeletePrimsCommand,
    MaterialGraph_CreateUsdUIBackdropCommand,
    MaterialGraph_ConnectUsdShadeToSourceCommand,
    MaterialGraph_ConnectUsdShadeToSourcePolymorphicCommand,
    MaterialGraph_CreateInputPortCommand,
    MaterialGraph_CreateOutputPortCommand,
    MaterialGraph_GroupNodeGraphCommand,
    MaterialGraph_UngroupNodeGraphCommand,
    MaterialGraph_ImportNodeGraphCommand,
    MaterialGraph_UsdShadeDisconnectSourceCommand,
    MaterialGraph_RemoveConnectionsCommand,
    MaterialGraph_RenamePropertyCommand,
    MaterialGraph_IsolationModelRemoveCommand,
    MaterialGraph_CommitLayerTransactionCommand,
    MaterialGraph_SetPrimCustomDataCommand,
    MaterialGraph_SetPrimCustomDataKeyCommand,
    MaterialGraph_SoloContextCommand,
    MaterialGraph_NewUsdShadeMaterialCommand,
    MaterialGraph_NewUsdShadeNodeCommand,
    MaterialGraph_NewUsdShadeNodeFromSdrCommand,
    MaterialGraph_NewUsdShadeNodeGraphCommand,
)
_commands_registered = False


def register_all_commands() -> None:
    """Register material graph command classes exactly once."""
    global _commands_registered
    if _commands_registered:
        return

    import omni.kit.commands

    add_command = omni.kit.commands.register
    for command_cls in _REGISTERED_COMMANDS:
        add_command(command_cls)

    _commands_registered = True


def unregister_all_commands() -> None:
    """Unregister material graph command classes when extension shuts down."""
    global _commands_registered
    if not _commands_registered:
        return

    import omni.kit.commands

    # Unregister in reverse registration order to mirror startup.
    remove_command = omni.kit.commands.unregister
    for command_cls in reversed(_REGISTERED_COMMANDS):
        remove_command(command_cls)

    _commands_registered = False


__all__ = [
    "register_all_commands",
    "unregister_all_commands",
]
