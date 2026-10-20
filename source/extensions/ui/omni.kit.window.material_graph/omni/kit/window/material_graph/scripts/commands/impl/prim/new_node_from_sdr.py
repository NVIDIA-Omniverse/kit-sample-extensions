"""Command that resolves an SDR identifier and creates the corresponding shader node."""

from typing import Dict, Optional, Sequence, Union

import omni.kit.commands
from pxr import Sdf, Usd

from ....config.logging import logger
from ....utils.sdr_wrappers import SdrRegistryWrapper
from .new_node import MaterialGraph_NewUsdShadeNodeCommand

_PathLike = Union[Sdf.Path, str]


class MaterialGraph_NewUsdShadeNodeFromSdrCommand(omni.kit.commands.Command):
    """Create a USD shader prim from an SDR identifier."""

    def __init__(
        self,
        parent_path: _PathLike,
        identifier: str,
        position: Optional[Sequence[float]] = None,
        custom_data: Optional[Dict[str, object]] = None,
        stage: Optional[Usd.Stage] = None,
    ) -> None:
        """Store SDR lookup inputs and defer node creation to execution time."""
        self._parent_path = parent_path
        self._identifier = identifier
        self._position = position
        self._custom_data = dict(custom_data or {})
        self._stage = stage
        self._create_cmd: Optional[MaterialGraph_NewUsdShadeNodeCommand] = None

    def do(self):
        """Resolve SDR node by identifier, create command, and execute node creation."""
        sdr_node = SdrRegistryWrapper().GetShaderNodeByIdentifier(self._identifier)
        if not sdr_node:
            logger.warning("failed to create shader from sdr: unknown identifier=%s", self._identifier)
            return None
        self._create_cmd = MaterialGraph_NewUsdShadeNodeCommand(
            parent_path=self._parent_path,
            node=sdr_node,
            position=self._position,
            custom_data=self._custom_data,
            stage=self._stage,
        )
        return self._create_cmd.do()

    def undo(self) -> None:
        """Undo shader-node creation when a delegated create command was executed."""
        if self._create_cmd:
            self._create_cmd.undo()
