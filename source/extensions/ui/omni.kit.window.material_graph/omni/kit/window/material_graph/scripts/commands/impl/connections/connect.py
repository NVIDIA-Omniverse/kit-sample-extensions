"""UsdShade connection command used by the material graph command layer."""

import logging

import omni.kit.commands
from pxr import Sdf, Tf, UsdShade

from ....config.logging import log_exception, logger
from .utils import is_valid_port

# pylint: disable=no-member


class MaterialGraph_ConnectUsdShadeToSourceCommand(omni.kit.commands.Command):
    """Undoable command wrapper that connects a UsdShade input to a source attribute path."""

    def __init__(self, target: UsdShade.Input, source: UsdShade.Output) -> None:
        """Capture validated target/source ports for command execution and undo."""
        super().__init__()
        self._target = target
        self._source = source
        self._previous_connections: list[Sdf.Path] = []
        self._failed = False

    def do(self) -> bool:
        """Connect target to source when both ports are still valid."""
        if self._failed:
            return False
        if not is_valid_port(self._target) or not is_valid_port(self._source):
            self._failed = True
            return False
        target_attr = self._target.GetAttr()
        self._previous_connections = list(target_attr.GetConnections())
        try:
            connected = bool(self._target.ConnectToSource(self._source))
        except (RuntimeError, ValueError, TypeError, AttributeError, Tf.ErrorException) as exc:
            log_exception(
                logger,
                "USD connection command failed",
                level=logging.WARNING,
                prim_path=str(target_attr.GetPath()),
                action="connect",
                exc=exc,
            )
            connected = False
        if not connected:
            target_attr.SetConnections(self._previous_connections)
            self._failed = True
        return connected

    def undo(self) -> None:
        """Disconnect the target source connection if the target still exists."""
        if not self._failed and is_valid_port(self._target):
            self._target.GetAttr().SetConnections(self._previous_connections)
