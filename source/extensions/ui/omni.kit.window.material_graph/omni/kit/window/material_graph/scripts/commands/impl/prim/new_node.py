"""Command for creating shader nodes from resolved SDR node definitions."""

from typing import Dict, Optional, Sequence, Union

import omni.kit.commands
from pxr import Sdf, Usd, UsdShade

from ....utils.sdr_wrappers import SdrShaderNodeWrapper, resolve_output_value_type
from .create import MaterialGraph_CreatePrimCommand
from .utils import sanitize_identifier

_PathLike = Union[Sdf.Path, str]


class MaterialGraph_NewUsdShadeNodeCommand(omni.kit.commands.Command):
    """Create a USD shader prim from an SDR node."""

    def __init__(
        self,
        parent_path: _PathLike,
        node: Optional[SdrShaderNodeWrapper],
        position: Optional[Sequence[float]] = None,
        custom_data: Optional[Dict[str, object]] = None,
        stage: Optional[Usd.Stage] = None,
    ) -> None:
        """Initialize node creation inputs, custom data, and delegated create command."""
        identifier = node.GetIdentifier() if node else ""
        prim_name = sanitize_identifier(identifier)
        output_types = {}
        if node:
            for name in node.GetShaderOutputNames():
                prop = node.GetShaderOutput(name)
                if prop:
                    output_types[name] = resolve_output_value_type(prop)
        self._create_cmd = MaterialGraph_CreatePrimCommand(
            parent_path=parent_path,
            prim_type=UsdShade.Tokens.Shader,
            prim_name=prim_name or UsdShade.Tokens.Shader,
            select_new_prim=False,
            shader_identifier=sanitize_identifier(identifier),
            output_types=output_types,
            position=position,
            custom_data=custom_data,
            stage=stage,
        )

    def do(self):
        """Create shader prim, assign shader id/position/custom data, and return prim."""
        return self._create_cmd.do()

    def undo(self) -> None:
        """Undo created shader node by delegating to the wrapped create command."""
        self._create_cmd.undo()
