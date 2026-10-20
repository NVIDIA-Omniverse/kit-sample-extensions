from types import SimpleNamespace

from ...scripts.models.graph.nodes.nodegraph import NodeGraphModel
from ..base import MaterialGraphTestBase


class TestNodeGraphModelPosition(MaterialGraphTestBase):
    """Tests for NodeGraphModel position stale-item guards."""

    async def test_position_getter_returns_none_for_stale_item(self) -> None:
        """Getter should safely return None when item has no prim_model."""
        model = NodeGraphModel.__new__(NodeGraphModel)
        model._position_txn = SimpleNamespace(is_staging=False)
        stale_item = SimpleNamespace(prim_model=None)
        self.assertIsNone(NodeGraphModel.position.fget(model, stale_item))
