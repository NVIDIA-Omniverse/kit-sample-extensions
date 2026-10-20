"""Command for creating nodegraph prims with optional stored position metadata."""

from typing import Optional, Sequence, Union

import omni.kit.commands
from pxr import Sdf, Usd, UsdShade

from .create import MaterialGraph_CreatePrimCommand

_PathLike = Union[Sdf.Path, str]


class MaterialGraph_NewUsdShadeNodeGraphCommand(omni.kit.commands.Command):
    """Create a USD nodegraph prim with UI metadata."""

    def __init__(
        self,
        parent_path: _PathLike,
        identifier: str,
        position: Optional[Sequence[float]] = None,
        position_key: Optional[str] = None,
        context_visibility: Optional[Union[Sequence[str], str]] = None,
        stage: Optional[Usd.Stage] = None,
    ) -> None:
        """Initialize nodegraph creation and optional position-authoring behavior."""
        prim_name = identifier or UsdShade.Tokens.NodeGraph
        self._create_cmd = MaterialGraph_CreatePrimCommand(
            parent_path=parent_path,
            prim_type=UsdShade.Tokens.NodeGraph,
            prim_name=prim_name,
            select_new_prim=False,
            position=position,
            position_key=position_key,
            context_visibility=context_visibility,
            stage=stage,
        )

    def do(self):
        """Create nodegraph prim and author either custom-key or UI position metadata."""
        return self._create_cmd.do()

    def undo(self) -> None:
        """Undo nodegraph creation by delegating to the wrapped create command."""
        self._create_cmd.undo()
