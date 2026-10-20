"""Input port creation command."""

from typing import Optional

from pxr import Sdf, Usd, UsdShade

from .abstract import MaterialGraph_CreateAbstractPortCommand


class MaterialGraph_CreateInputPortCommand(MaterialGraph_CreateAbstractPortCommand):
    """Create a connectable input on the prim."""

    def __init__(
        self,
        prim_path: Sdf.Path,
        port_name: str,
        port_type: Sdf.ValueTypeName,
        stage: Optional[Usd.Stage] = None,
        variability: Sdf.Variability = Sdf.VariabilityVarying,
    ) -> None:
        """Initialize input-port creation with the inputs namespace prefix."""
        MaterialGraph_CreateAbstractPortCommand.__init__(self, prim_path, port_name, port_type, stage, variability)
        self._port_prefix = UsdShade.Tokens.inputs
