"""Implement material graph extension logic for `context_manager/context.py`."""

from typing import Optional, Type, TypeVar

from pxr import Usd

from ..models.graph.nodes.material import MaterialModel
from ..plugins.core import Plugin as PluginBase

# pylint: disable=no-member

TContext = TypeVar("TContext", bound="Context")


class Context:
    """Wraps a material context with its model and plugin."""

    def __init__(
        self,
        prim: Usd.Prim,
        context_name: str,
        usd_context: object,
        plugin: PluginBase,
        validator: object,
    ) -> None:
        """Create a context wrapper for a material prim."""
        self._plugin = plugin
        self._model = MaterialModel(prim, context_name, usd_context, plugin, validator=validator)

    @classmethod
    def create_context(
        cls: Type[TContext],
        prim: Usd.Prim,
        context_name: str,
        usd_context: object,
        plugin: PluginBase,
        validator: object,
    ) -> TContext:
        """Factory for building a context instance."""
        return cls(prim, context_name, usd_context, plugin, validator=validator)

    def destroy(self) -> None:
        """Release model and plugin references."""
        if self._model:
            self._model.destroy()
            self._model = None
        self._plugin = None

    @property
    def model(self) -> Optional[MaterialModel]:
        """Return the material model for this context."""
        return self._model

    @property
    def plugin(self) -> Optional[PluginBase]:
        """Return the plugin associated with this context."""
        return self._plugin
