"""Input-port attribute model implementation for authored UsdShade input sockets."""

from typing import Any, Optional

from pxr import UsdShade

from .....commands.wrappers.ports import CreateInputPort
from .model import AttributeModel


class InputAttributeModel(AttributeModel):
    """Attribute model specialization for UsdShade input-port behavior and commands."""

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

        super().__init__(parent, prim, context_name, usd_context, plugin, pause, proxy_attribute, UsdShade.Input)

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
    ) -> Optional["InputAttributeModel"]:
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
            CreateInputPort,
            InputAttributeModel,
            variability=variability,
        )

    def create_port(self) -> bool:
        """Execute create port behavior for material graph workflows."""

        return super().create_port(UsdShade.Tokens.inputs, CreateInputPort)

    def get_inputs(self) -> Optional[list]:
        """Execute get inputs behavior for material graph workflows."""

        return self._connections.connected_ports()

    def set_name(self, value: str) -> bool:
        """Rename the input and report whether the command succeeded."""

        return super().set_name(f"{UsdShade.Tokens.inputs}{value}")
