"""Command for creating a new USD material prim with optional initial position."""

from typing import Optional, Sequence, Union

import omni.kit.commands
from pxr import Sdf, Usd, UsdShade

from .create import MaterialGraph_CreatePrimCommand

_PathLike = Union[Sdf.Path, str]


class MaterialGraph_NewUsdShadeMaterialCommand(omni.kit.commands.Command):
    """Create a USD material prim and optional selection."""

    def __init__(
        self,
        parent_path: _PathLike,
        identifier: str,
        position: Optional[Sequence[float]] = None,
        select_new_prim: bool = True,
        stage: Optional[Usd.Stage] = None,
    ) -> None:
        """Initialize material creation command and delegated prim-creation command."""
        prim_name = identifier or UsdShade.Tokens.Material
        self._create_cmd = MaterialGraph_CreatePrimCommand(
            parent_path=parent_path,
            prim_type=UsdShade.Tokens.Material,
            prim_name=prim_name,
            select_new_prim=select_new_prim,
            position=position,
            stage=stage,
        )

    def do(self):
        """Create the material prim and author a UI position when provided."""
        return self._create_cmd.do()

    def undo(self) -> None:
        """Undo material creation by delegating to the wrapped create command."""
        self._create_cmd.undo()
