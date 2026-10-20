"""Output-port attribute model implementation for authored UsdShade output sockets."""

from typing import Any, Optional

from pxr import UsdShade

from .....commands.wrappers.ports import CreateOutputPort
from .model import AttributeModel


class OutputAttributeModel(AttributeModel):
    """Attribute model specialization for UsdShade output-port behavior and commands."""

    def __init__(
        self,
        parent: Any,
        prim: Any,
        context_name: str,
        usd_context: Any,
        plugin: Any,
        pause: bool,
        proxy_attribute: Any,
    ) -> None:
        """Initialize instance state for this material graph component."""

        super().__init__(parent, prim, context_name, usd_context, plugin, pause, proxy_attribute, UsdShade.Output)

    @classmethod
    def create(
        cls,
        parent: Any,
        prim: Any,
        context_name: str,
        usd_context: Any,
        plugin: Any,
        pause: bool,
        name: str,
        value_type_name: Any,
        variability: Optional[Any] = None,
    ) -> Optional["OutputAttributeModel"]:
        """Execute create behavior for material graph workflows."""

        return AttributeModel.create(
            parent,
            prim,
            context_name,
            usd_context,
            plugin,
            pause,
            name,
            value_type_name,
            CreateOutputPort,
            OutputAttributeModel,
            variability=variability,
        )

    def create_port(self) -> bool:
        """Execute create port behavior for material graph workflows."""

        return super().create_port(UsdShade.Tokens.outputs, CreateOutputPort)

    def get_outputs(self) -> Optional[list]:
        """Execute get outputs behavior for material graph workflows."""

        return self._connections.connected_ports()

    def set_name(self, value: str) -> bool:
        """Rename the output unless it is a reserved material terminal."""

        token_name = self._attribute_name.split(":")[-1]
        is_material_output = bool(self.parent and self.parent.prim and self.parent.prim.IsA(UsdShade.Material))
        if is_material_output and token_name in (
            UsdShade.Tokens.displacement,
            UsdShade.Tokens.surface,
            UsdShade.Tokens.volume,
        ):
            return False
        return super().set_name(f"{UsdShade.Tokens.outputs}{value}")
