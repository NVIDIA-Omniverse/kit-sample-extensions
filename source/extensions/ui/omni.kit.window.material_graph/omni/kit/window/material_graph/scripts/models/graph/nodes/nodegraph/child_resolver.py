"""Child-prim discovery logic for nodegraph models across supported prim types."""

from typing import Any, List

from pxr import Usd, UsdShade, UsdUI

from .....utils.context_visibility import is_context_visible


class NodeGraphChildResolver:
    """Resolve child prims for a nodegraph model."""

    def __init__(self, model: Any):
        """Store nodegraph model reference used for child-prim filtering."""
        self._model = model

    def is_visible_child_prim(self, prim: Usd.Prim) -> bool:
        """Return whether ``prim`` is a direct child that should appear in the graph."""
        if not prim or prim == self._model._prim:
            return False
        if prim.IsA(UsdShade.NodeGraph) or prim.IsA(UsdUI.Backdrop):
            return self._should_show_contextual_prim(prim)
        return self._model._plugin.is_supported_prim(prim)

    def get_child_prims(self) -> List[Usd.Prim]:
        """Collect child prims that should be shown in the nodegraph."""
        child_prims = []
        children = self._model.prim.GetChildren()
        for prim in children:
            if not prim or prim == self._model._prim:
                continue
            if self.is_visible_child_prim(prim):
                child_prims.append(prim)
        return child_prims

    def _should_show_contextual_prim(self, prim: Usd.Prim) -> bool:
        """Return True when prim context-visibility includes active context."""
        return is_context_visible(prim, self._model.context_name)
