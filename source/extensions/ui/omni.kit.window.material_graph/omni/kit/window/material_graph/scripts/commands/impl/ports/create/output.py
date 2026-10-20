"""Output port creation command."""

from typing import Optional

from pxr import Sdf, Usd, UsdShade

from .abstract import MaterialGraph_CreateAbstractPortCommand


class MaterialGraph_CreateOutputPortCommand(MaterialGraph_CreateAbstractPortCommand):
    """Create a connectable output on the prim."""

    def __init__(
        self,
        prim_path: Sdf.Path,
        port_name: str,
        port_type: Sdf.ValueTypeName,
        stage: Optional[Usd.Stage] = None,
        variability: Sdf.Variability = Sdf.VariabilityVarying,
    ) -> None:
        """Initialize output-port creation with the outputs namespace prefix."""
        MaterialGraph_CreateAbstractPortCommand.__init__(self, prim_path, port_name, port_type, stage, variability)
        self._port_prefix = UsdShade.Tokens.outputs
