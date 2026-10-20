"""Atomic edit-layer transaction command for composite Material Graph edits."""

import omni.kit.commands
from pxr import Sdf


class MaterialGraph_CommitLayerTransactionCommand(omni.kit.commands.Command):
    """Represent an already-applied composite layer edit as one undo item.

    Callers perform the composite mutation with Kit undo recording disabled,
    then submit this command with exact before/after layer snapshots.  The
    command manager invokes ``do`` once while the after state is already
    authored; subsequent undo/redo transfers the corresponding snapshot.
    """

    def __init__(
        self,
        target_layer: Sdf.Layer,
        before_layer: Sdf.Layer,
        after_layer: Sdf.Layer,
        already_applied: bool = False,
    ) -> None:
        self._target_layer = target_layer
        # The caller creates dedicated anonymous snapshots for this command.
        # Keep them directly: copying a potentially large edit layer twice
        # more would add substantial latency and memory to every drag-connect.
        self._before_layer = before_layer
        self._after_layer = after_layer
        self._already_applied = already_applied
        self._failed = False

    def do(self) -> bool:
        """Apply the after snapshot, except for the initial already-applied call."""
        if self._failed or not self._target_layer:
            self._failed = True
            return False
        if self._already_applied:
            self._already_applied = False
            return True
        self._target_layer.TransferContent(self._after_layer)
        return True

    def undo(self) -> None:
        """Restore the exact layer contents from before the composite edit."""
        if not self._failed and self._target_layer:
            self._target_layer.TransferContent(self._before_layer)
