from omni.kit.widget.graph import GraphModel
from pxr import Sdf, UsdShade

from ...scripts.models.graph.nodes.prim.model import PrimModel
from ...scripts.models.graph.ports.proxy import ProxyAttribute
from ..base import MaterialGraphTestBase
from .helpers import DummyPlugin


class TestExpansionState(MaterialGraphTestBase):
    """Regression coverage for node and group port expansion state updates."""

    async def setUp(self) -> None:
        """Load the simple scene and initialize a shader prim model."""
        await super().setUp()
        await self._load_scene("simple.usda")
        self._shader_path = Sdf.Path("/World/Looks/material/shader")
        self._plugin = DummyPlugin()
        self._shader_prim = self._get_prim_at_path(self._shader_path)
        self._prim_model = PrimModel(
            self._shader_prim,
            "universal",
            self._usd_context,
            self._plugin,
            None,
            UsdShade.Shader,
        )

    async def test_group_port_expansion_state_updates(self) -> None:
        """Setting group port expansion should update the group model."""
        attr = self._shader_prim.CreateAttribute(
            f"{UsdShade.Tokens.inputs}groupedInput",
            Sdf.ValueTypeNames.Float,
        )
        placeholder = ProxyAttribute(attr.GetName(), False, attribute=attr)
        self._prim_model._inputs.sync([(placeholder, "GroupA")])

        group = self._prim_model._inputs._children.get("GroupA")
        self.assertIsNotNone(group)

        self._prim_model[group].expansion_state = GraphModel.ExpansionState.CLOSED
        self.assertEqual(group._expansion_state, GraphModel.ExpansionState.CLOSED)

        self._prim_model[group].expansion_state = GraphModel.ExpansionState.OPEN
        self.assertEqual(group._expansion_state, GraphModel.ExpansionState.OPEN)

    async def test_node_expansion_state_updates(self) -> None:
        """Setting node expansion should update the node model."""
        self._prim_model[self._prim_model].expansion_state = GraphModel.ExpansionState.MINIMIZED
        self.assertEqual(self._prim_model._expansion_state, GraphModel.ExpansionState.MINIMIZED)

        self._prim_model[self._prim_model].expansion_state = GraphModel.ExpansionState.OPEN
        self.assertEqual(self._prim_model._expansion_state, GraphModel.ExpansionState.OPEN)
