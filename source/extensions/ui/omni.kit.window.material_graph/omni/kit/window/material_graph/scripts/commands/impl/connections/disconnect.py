"""Undoable command for disconnecting an input port from its current source."""

import logging

import omni.kit.commands
from pxr import Sdf, Tf

from ....config.logging import log_exception, logger
from .utils import is_valid_port

# pylint: disable=no-member


class MaterialGraph_UsdShadeDisconnectSourceCommand(omni.kit.commands.Command):
    """Undoable command wrapper that disconnects a UsdShade port from its current source."""

    def __init__(self, target: object) -> None:
        """Capture target port and cache previous source information for undo."""
        super().__init__()
        self._target = target
        self._previous_connections: list[Sdf.Path] = []
        self._failed = False

    def do(self) -> bool:
        """Disconnect target while preserving the exact authored source list for undo."""
        if self._failed:
            return False
        if not is_valid_port(self._target):
            self._failed = True
            return False
        target_attr = self._target.GetAttr()
        self._previous_connections = list(target_attr.GetConnections())
        if not self._previous_connections:
            self._failed = True
            return False
        try:
            disconnected = bool(self._target.DisconnectSource())
        except (RuntimeError, ValueError, TypeError, AttributeError, Tf.ErrorException) as exc:
            log_exception(
                logger,
                "USD disconnection command failed",
                level=logging.WARNING,
                prim_path=str(target_attr.GetPath()),
                action="disconnect",
                exc=exc,
            )
            disconnected = False
        if not disconnected:
            target_attr.SetConnections(self._previous_connections)
            self._failed = True
        return disconnected

    def undo(self) -> None:
        """Restore the exact cached source paths when the target still exists."""
        if not self._failed and is_valid_port(self._target):
            self._target.GetAttr().SetConnections(self._previous_connections)
