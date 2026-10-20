"""Output attribute-group model for creating and synchronizing output port entries."""

from typing import Any, Optional, Sequence

from pxr import UsdShade

from ..attribute.output import OutputAttributeModel
from .model import AttributeGroupModel


class OutputAttributeGroupModel(AttributeGroupModel):
    """Output-port group model that owns, sorts, and creates output attribute items."""

    def __init__(
        self,
        parent: Any,
        prim: Any,
        context_name: str,
        usd_context: Any,
        plugin: Any,
        pause: bool,
        name: str = "Outputs",
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
            OutputAttributeModel,
            OutputAttributeGroupModel,
            UsdShade.Tokens.outputs,
        )

    @property
    def inputs(self, item: Optional[Any] = None) -> Optional[Sequence[Any]]:
        """Execute inputs behavior for material graph workflows."""

        if item:
            return item.inputs
        return None

    @inputs.setter
    def inputs(self, value: Optional[Sequence[Any]], item: Optional[Any] = None) -> None:
        """Execute inputs behavior for material graph workflows."""

        if item:
            item.inputs = value

    @property
    def outputs(self, item: Optional[Any] = None) -> Optional[Sequence[Any]]:
        """Execute outputs behavior for material graph workflows."""

        if item:
            return item.outputs
        return []

    @outputs.setter
    def outputs(self, value: Optional[Sequence[Any]], item: Optional[Any] = None) -> None:
        """Execute outputs behavior for material graph workflows."""

        if item:
            item.outputs = value
