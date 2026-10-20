"""Input attribute-group model for creating and synchronizing input port entries."""

from typing import Any

from pxr import UsdShade

from ..attribute.input import InputAttributeModel
from .model import AttributeGroupModel


class InputAttributeGroupModel(AttributeGroupModel):
    """Input-port group model that owns, sorts, and creates input attribute items."""

    def __init__(
        self,
        parent: Any,
        prim: Any,
        context_name: str,
        usd_context: Any,
        plugin: Any,
        pause: bool,
        name: str = "Inputs",
    ) -> None:
        """Initialize instance state for this material graph component."""

        super().__init__(
            name,
            parent,
            prim,
            context_name,
            usd_context,
            plugin,
            pause,
            InputAttributeModel,
            InputAttributeGroupModel,
            UsdShade.Tokens.inputs,
        )
