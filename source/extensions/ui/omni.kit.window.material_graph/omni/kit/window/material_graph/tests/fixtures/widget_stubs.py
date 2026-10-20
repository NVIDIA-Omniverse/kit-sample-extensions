"""Reusable widget stubs for controller and drop-handler tests."""

from types import SimpleNamespace
from unittest.mock import MagicMock

from .graph_stubs import DummyGraphView


class DummyGraphRootModel:
    """Minimal graph root stub with selection/get-item API used by payload drops."""

    def __init__(self, prim_path="/World/Looks/Material") -> None:
        self.prim_path = prim_path
        self.selection = []

    @staticmethod
    def get_item_model(_path):
        return None


class DummyWidget:
    """Widget stub for payload drop and node-creation controller tests."""

    def __init__(
        self,
        *,
        graph_view: DummyGraphView | None = None,
        current_context: str = "universal",
        isolation_model: SimpleNamespace | None = None,
        prim=None,
    ) -> None:
        self.graph_view = graph_view if graph_view is not None else DummyGraphView()
        self.current_context = current_context
        self.isolation_model = isolation_model or SimpleNamespace(root=DummyGraphRootModel())
        self.show_error = MagicMock()
        self.clear_error = MagicMock()
        self.prim = prim


class DropHandlerWidget:
    """Widget stub for path/texture/catalog drop handler tests."""

    def __init__(self, prim=None) -> None:
        self.prim = prim
        self.current_context = "mdl"
        self.graph_view = MagicMock(model=True)
        self.edit_graph = MagicMock()
        self.show_error = MagicMock()
        self.clear_error = MagicMock()
