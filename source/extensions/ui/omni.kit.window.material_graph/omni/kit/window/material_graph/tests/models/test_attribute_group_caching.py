from collections import OrderedDict
from types import SimpleNamespace
from unittest.mock import MagicMock

from omni.kit.widget.graph import GraphModel
from pxr import Sdf, UsdShade

from ...scripts.models.graph.nodes.material import MaterialModel
from ...scripts.models.graph.ports.group.model import AttributeGroupModel
from ...scripts.models.graph.ports.proxy import ProxyAttribute
from ...scripts.validation.validator import MaterialValidator
from ..base import MaterialGraphTestBase
from .helpers import DummyPlugin


class TestAttributeGroupCaching(MaterialGraphTestBase):
    """Attribute group caching behavior."""

    async def setUp(self) -> None:
        """Load scene and initialize material model."""
        await super().setUp()
        await self._load_scene("simple.usda")
        self._material_path = Sdf.Path("/World/Looks/material")
        self._shader_path = Sdf.Path("/World/Looks/material/shader")
        self._plugin = DummyPlugin()
        self._validator = MaterialValidator()

        material_prim = self._get_prim_at_path(self._material_path)
        self._model = MaterialModel(material_prim, "universal", self._usd_context, self._plugin, self._validator)

    async def test_child_cache_invalidation(self) -> None:
        """Adding inputs should invalidate cached children."""
        inputs = self._model._inputs
        inputs.sync()

        before_version = inputs._children_version

        self._model.prim.CreateAttribute(f"{UsdShade.Tokens.inputs}newInput", Sdf.ValueTypeNames.Float)
        self._model.sync_inputs()

        self.assertGreater(inputs._children_version, before_version)
        after_paths = inputs._collect_child_attribute_paths()
        self.assertIn(self._material_path.AppendProperty(f"{UsdShade.Tokens.inputs}newInput"), after_paths)

    async def test_display_group_refresh(self) -> None:
        """Display group refresh should normalize group labels."""
        inputs = self._model._inputs
        attr = self._model.prim.CreateAttribute(f"{UsdShade.Tokens.inputs}foo", Sdf.ValueTypeNames.Float)
        placeholder = ProxyAttribute(f"{UsdShade.Tokens.inputs}foo", False, attribute=attr)
        inputs.sync([(placeholder, "GroupA:Child")])

        group = inputs._children.get("GroupA")
        self.assertIsInstance(group, AttributeGroupModel)
        self.assertEqual(group.display_group, "")
        child = group._children.get("Child")
        self.assertIsInstance(child, AttributeGroupModel)
        self.assertEqual(child.display_group, "")

    async def test_incoming_connection_cache(self) -> None:
        """Incoming connection flag should update on disconnect."""
        inputs = self._model._inputs
        inputs.sync()

        material_path = Sdf.Path("/World/Looks/TempMat")
        material = UsdShade.Material.Define(self._stage, material_path)
        shader = UsdShade.Shader.Define(self._stage, material_path.AppendChild("Shader"))
        material_input = material.CreateInput("incomingTest", Sdf.ValueTypeNames.Float)
        self.assertTrue(material_input)
        shader_input = shader.CreateInput("drive", Sdf.ValueTypeNames.Float)
        if shader_input:
            shader_input.ConnectToSource(material_input)

        self._model = MaterialModel(material.GetPrim(), "universal", self._usd_context, self._plugin, self._validator)
        inputs = self._model._inputs
        self._model.sync_inputs()
        inputs.sync_ports()
        _ = inputs.expansion_state
        self.assertTrue(inputs._has_incoming_connections)

        if shader_input and shader_input.HasConnectedSource():
            shader_input.DisconnectSource()
            shader_input.GetAttr().ClearConnections()

        self._model.sync_inputs()
        inputs.sync_ports()
        _ = inputs.expansion_state
        self.assertFalse(inputs._has_incoming_connections)

    async def test_group_delegation_connections_and_path_lookup(self) -> None:
        """Grouped ports expose delegated state and recursively collect live connections."""
        group = self._model._inputs
        delegated = SimpleNamespace(
            child_ports=["child"],
            prim_model="prim",
            style={"color": "red"},
            inputs=["in"],
            outputs=["out"],
            ports=["port"],
            expansion_state=GraphModel.ExpansionState.CLOSED,
            connected_ports=["connected"],
            display_group="Display",
            tooltip_text="Tooltip",
        )

        self.assertEqual(AttributeGroupModel.child_ports.fget(group, delegated), ["child"])
        self.assertEqual(AttributeGroupModel.prim_model.fget(group, delegated), "prim")
        self.assertEqual(AttributeGroupModel.style.fget(group, delegated), {"color": "red"})
        self.assertEqual(AttributeGroupModel.inputs.fget(group, delegated), ["in"])
        self.assertEqual(AttributeGroupModel.outputs.fget(group, delegated), ["out"])
        self.assertEqual(AttributeGroupModel.ports.fget(group, delegated), ["port"])
        self.assertEqual(AttributeGroupModel.expansion_state.fget(group, delegated), GraphModel.ExpansionState.CLOSED)
        self.assertEqual(AttributeGroupModel.connected_ports.fget(group, delegated), ["connected"])
        self.assertEqual(AttributeGroupModel.display_group.fget(group, delegated), "Display")
        self.assertEqual(AttributeGroupModel.tooltip_text.fget(group, delegated), "Tooltip")

        AttributeGroupModel.inputs.fset(group, ["new"], delegated)
        AttributeGroupModel.outputs.fset(group, ["new"], delegated)
        AttributeGroupModel.expansion_state.fset(group, GraphModel.ExpansionState.OPEN, delegated)
        self.assertEqual(delegated.inputs, ["new"])
        self.assertEqual(delegated.outputs, ["new"])
        self.assertEqual(delegated.expansion_state, GraphModel.ExpansionState.OPEN)

        leaf_path = self._material_path.AppendProperty("inputs:leaf")
        leaf = SimpleNamespace(path=leaf_path, connected_ports=["source"], pause=False, destroy=MagicMock())
        nested = SimpleNamespace(get_child_by_path=MagicMock(return_value=leaf))
        group._children = OrderedDict((("leaf", leaf), ("nested", nested)))
        group._child_cls = type(leaf)
        self.assertEqual(group.connected_ports, ["source"])
        self.assertIs(group.get_child_by_path(leaf_path), leaf)
        group._child_cls = object
        self.assertIs(group.get_child_by_path(leaf_path), leaf)
        self.assertIsNone(group.get_child_by_path(Sdf.Path("/World")))

    async def test_group_connection_and_filter_boundaries(self) -> None:
        """Connection detection and proxy filtering handle authored, nested, and invalid inputs."""
        group = self._model._inputs
        self.assertFalse(group._has_incoming_connections_from_stage([]))

        connected = SimpleNamespace(
            usdshade_port=SimpleNamespace(
                GetAttr=lambda: SimpleNamespace(GetConnections=lambda: [Sdf.Path("/Source.outputs:out")])
            ),
            connected_ports=[],
            path=None,
        )
        authored_empty = SimpleNamespace(
            # USD 25.02 reports HasConnectedSource for this state, but the
            # composed connection path list is correctly empty.
            usdshade_port=SimpleNamespace(
                HasConnectedSource=lambda: True,
                GetAttr=lambda: SimpleNamespace(GetConnections=lambda: []),
            ),
            connected_ports=[],
            path=None,
        )
        cached = SimpleNamespace(usdshade_port=None, connected_ports=[object()], path=None)
        stale = SimpleNamespace(
            usdshade_port=SimpleNamespace(GetAttr=MagicMock(side_effect=RuntimeError("expired port"))),
            connected_ports=[],
            path=None,
        )
        self.assertTrue(group._port_has_connection(connected))
        self.assertFalse(group._port_has_connection(authored_empty))
        self.assertTrue(group._port_has_connection(cached))
        with self.assertLogs("omni.kit.window.material_graph", level="DEBUG") as captured:
            self.assertFalse(group._port_has_connection(stale))
        self.assertIn("group connection query failed", "\n".join(captured.output))
        self.assertFalse(group._port_has_connection(SimpleNamespace()))

        nested = AttributeGroupModel.__new__(AttributeGroupModel)
        nested._children = OrderedDict((("connected", connected),))
        group._children = OrderedDict((("nested", nested),))
        self.assertTrue(group._has_connected_sources())

        visible = SimpleNamespace(name="inputs:visible", hidden=False, display_group=f"{group._name}:Nested")
        hidden = SimpleNamespace(name="inputs:hidden", hidden=True, display_group=group._name)
        wrong_prefix = SimpleNamespace(name="outputs:wrong", hidden=False, display_group=group._name)
        wrong_group = SimpleNamespace(name="inputs:other", hidden=False, display_group="Other")
        self.assertEqual(group.filter_proxy_attributes(None), [])
        self.assertEqual(
            group.filter_proxy_attributes([visible, hidden, wrong_prefix, wrong_group, (visible, "Explicit")]),
            [(visible, "Nested"), (visible, "Explicit")],
        )

    async def test_group_can_close_after_disconnect_authors_empty_connection_opinion(self) -> None:
        """An authored-empty USD connection list must not pin a parameter group open."""
        source = UsdShade.Shader.Define(self._stage, "/World/Looks/GroupSource")
        target = UsdShade.Shader.Define(self._stage, "/World/Looks/GroupTarget")
        source_output = source.CreateOutput("out", Sdf.ValueTypeNames.Float)
        target_input = target.CreateInput("emission", Sdf.ValueTypeNames.Float)
        self.assertTrue(target_input.ConnectToSource(source_output))

        group = self._model._inputs
        group._children = OrderedDict(
            (
                (
                    "Emission",
                    SimpleNamespace(
                        usdshade_port=None,
                        connected_ports=[],
                        path=target_input.GetAttr().GetPath(),
                    ),
                ),
            )
        )
        group._expansion_state = GraphModel.ExpansionState.CLOSED
        self.assertEqual(group.expansion_state, GraphModel.ExpansionState.OPEN)

        self.assertTrue(target_input.DisconnectSource())
        self.assertTrue(target_input.GetAttr().HasAuthoredConnections())
        self.assertEqual(target_input.GetAttr().GetConnections(), [])
        self.assertEqual(group.expansion_state, GraphModel.ExpansionState.CLOSED)

        # Undo restores a live path and must reopen the group; redo restores
        # the authored-empty disconnect state and must make it closable again.
        target_input.GetAttr().SetConnections([source_output.GetAttr().GetPath()])
        self.assertEqual(group.expansion_state, GraphModel.ExpansionState.OPEN)
        target_input.GetAttr().SetConnections([])
        self.assertEqual(group.expansion_state, GraphModel.ExpansionState.CLOSED)

        # Preserve the fallback's original purpose: a path remains a real
        # connection opinion even if its source cannot currently be resolved.
        target_input.GetAttr().SetConnections([Sdf.Path("/Missing.outputs:out")])
        self.assertEqual(group.expansion_state, GraphModel.ExpansionState.OPEN)
