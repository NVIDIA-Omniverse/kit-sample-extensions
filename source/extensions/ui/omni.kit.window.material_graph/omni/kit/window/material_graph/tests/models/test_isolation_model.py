from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from omni.kit.widget.graph import IsolationGraphModel
from omni.kit.widget.graph.graph_model import GraphModel
from pxr import Sdf, UsdShade

from ...scripts.config.paths import Paths
from ...scripts.models.graph import isolation as isolation_module
from ...scripts.models.graph.input_node_view import InputNodeViewMode, IoState
from ...scripts.models.graph.isolation import (
    MaterialGraphIsolationModel,
    _build_input_node_class,
    _build_output_node_class,
    _resolve_node_class,
)
from ..base import MaterialGraphTestBase


class TestIsolationModel(MaterialGraphTestBase):
    """Isolation model cache behavior."""

    async def test_isolation_model_refresh(self) -> None:
        """Refresh should clear caches and notify parents."""
        # Refresh must notify both isolation and root models so UI state remains
        # coherent when isolation internals are rebuilt.
        isolation = MaterialGraphIsolationModel.__new__(MaterialGraphIsolationModel)
        isolation._input_nodes = [object()]
        isolation._output_nodes = [object()]
        isolation._root = MagicMock()
        isolation.clear_caches = MagicMock()
        isolation._item_changed = MagicMock()

        isolation.refresh()
        isolation.clear_caches.assert_called()
        isolation._item_changed.assert_called_with(None)
        isolation._root._item_changed.assert_called_with(None)

    async def test_remove_input_output_nodes(self) -> None:
        """Remove input/output should clear stored nodes."""
        # Remove operations must clear local caches and notify root so graph
        # visuals update immediately.
        isolation = MaterialGraphIsolationModel.__new__(MaterialGraphIsolationModel)
        isolation._input_nodes = [object()]
        isolation._output_nodes = [object()]
        isolation._root = MagicMock()
        isolation.clear_caches = MagicMock()
        isolation._item_changed = MagicMock()

        isolation.remove_input()
        self.assertEqual(isolation._input_nodes, [])
        isolation._root._item_changed.assert_called_with(None)

        isolation._output_nodes = [MagicMock(prim=MagicMock(IsA=lambda _: False))]
        isolation.remove_output()
        self.assertEqual(isolation._output_nodes, [])

    async def test_add_input_output_stops_when_root_authoring_fails(self) -> None:
        """Isolation UI nodes must not appear when their root position was not authored."""
        isolation = MaterialGraphIsolationModel.__new__(MaterialGraphIsolationModel)
        isolation._root = SimpleNamespace(add_input_or_output=MagicMock(return_value=False))

        with patch.object(IsolationGraphModel, "add_input_or_output", return_value=None) as base_add:
            self.assertFalse(isolation.add_input_or_output((10.0, 20.0), True))
            base_add.assert_not_called()
            self.assertFalse(isolation.add_input_or_output(None, True))

            isolation._root.add_input_or_output.return_value = True
            self.assertTrue(isolation.add_input_or_output((30.0, 40.0), False))
            base_add.assert_called_once_with((30.0, 40.0), False)

    async def test_clear_caches_preserves_input_output_positions(self) -> None:
        """Cache rebuild should keep previously rendered IO node positions."""
        # Patch base clear_caches to simulate a normal rebuild step.
        isolation = MaterialGraphIsolationModel.__new__(MaterialGraphIsolationModel)
        input_node = object()
        output_node = object()
        isolation._input_nodes = [input_node]
        isolation._output_nodes = [output_node]
        isolation._input_position = None
        isolation._output_position = None
        isolation._proxy_cache = {}
        input_proxy = MagicMock(position=(11.0, 22.0))
        output_proxy = MagicMock(position=(33.0, 44.0))

        def _getitem(item):
            if item == input_node:
                return input_proxy
            if item == output_node:
                return output_proxy
            raise KeyError(item)

        def _base_clear(_self):
            _self._root_inputs = {}
            _self._root_outputs = {}

        with (
            patch(
                f"{Paths.MODULE_ID}.scripts.models.graph.isolation.IsolationGraphModel.clear_caches",
                _base_clear,
            ),
            patch.object(MaterialGraphIsolationModel, "__getitem__", autospec=True) as getitem,
        ):
            getitem.side_effect = lambda _self, item: _getitem(item)
            isolation.clear_caches()

        self.assertEqual(isolation._input_position, (11.0, 22.0))
        self.assertEqual(isolation._output_position, (33.0, 44.0))

    async def test_position_edit_forwarding_to_root(self) -> None:
        """Isolation model should forward position edit lifecycle to root."""
        # Isolation wrappers must forward begin/end edit lifecycle so root
        # transaction and batch movement logic can run.
        isolation = MaterialGraphIsolationModel.__new__(MaterialGraphIsolationModel)
        isolation._root = MagicMock()

        drive = object()
        isolation.position_begin_edit(drive)
        isolation.position_end_edit(drive)

        isolation._root.position_begin_edit.assert_called_once_with(drive)
        isolation._root.position_end_edit.assert_called_once_with(drive)

    async def test_item_proxy_caches_metadata_invalidates_setters_and_snapshots_ports(self) -> None:
        """Isolation proxies should cache stable reads while reflecting every supported edit."""

        class Item:
            pass

        item = Item()
        child = Item()
        values = {
            item: SimpleNamespace(
                name="Node",
                type="Shader",
                expansion_state=GraphModel.ExpansionState.OPEN,
                stacking_order=3,
                display_color=(0.1, 0.2, 0.3),
                icon="icon.svg",
                size=(240.0, 120.0),
                description="Description",
                position=(10.0, 20.0),
                selected=True,
                valid=False,
                ports=[child],
            ),
            child: SimpleNamespace(
                name="value",
                type="PortModel",
                type_name="float",
                sdf_type="double",
                expansion_state=GraphModel.ExpansionState.CLOSED,
                ports=None,
            ),
        }

        class Model:
            def __getitem__(self, model_item):
                return values[model_item]

            def _get_expansion_state(self, model_item):
                return values[model_item].expansion_state

            def _set_expansion_state(self, value, model_item):
                values[model_item].expansion_state = value

            expansion_state = property(_get_expansion_state, _set_expansion_state)

            def _get_description(self, model_item):
                return values[model_item].description

            def _set_description(self, value, model_item):
                values[model_item].description = value

            description = property(_get_description, _set_description)

        isolation = MaterialGraphIsolationModel.__new__(MaterialGraphIsolationModel)
        isolation._model = Model()
        isolation._proxy_cache = {}
        isolation._ports = {}
        isolation._nodes = {}
        isolation._root_inputs = {}
        isolation._root_outputs = {}
        isolation._root_ports = set()
        isolation._input_position = None
        isolation._output_position = None

        proxy = isolation[item]
        self.assertIs(proxy, isolation[item])
        self.assertEqual(proxy.name, "Node")
        self.assertEqual(proxy.type, "Shader")
        self.assertEqual(proxy.expansion_state, GraphModel.ExpansionState.OPEN)
        self.assertEqual(proxy.stacking_order, 3)
        self.assertEqual(proxy.display_color, (0.1, 0.2, 0.3))
        self.assertEqual(proxy.icon, "icon.svg")
        self.assertEqual(proxy.size, (240.0, 120.0))
        self.assertEqual(proxy.description, "Description")

        values[item].name = "Stale"
        values[item].display_color = (1.0, 1.0, 1.0)
        self.assertEqual(proxy.name, "Node")
        self.assertEqual(proxy.display_color, (0.1, 0.2, 0.3))

        proxy.name = "Renamed"
        proxy.expansion_state = GraphModel.ExpansionState.MINIMIZED
        proxy.display_color = (0.4, 0.5, 0.6)
        proxy.size = (300.0, 200.0)
        proxy.description = "Updated"
        self.assertEqual(proxy.name, "Renamed")
        self.assertEqual(proxy.expansion_state, GraphModel.ExpansionState.MINIMIZED)
        self.assertEqual(proxy.display_color, (0.4, 0.5, 0.6))
        self.assertEqual(proxy.size, (300.0, 200.0))
        self.assertEqual(proxy.description, "Updated")

        node_snapshot = proxy.snapshot_node()
        self.assertEqual(node_snapshot[:7], ("Renamed", "Shader", 300.0, (10.0, 20.0), (0.4, 0.5, 0.6), True, False))
        self.assertEqual(node_snapshot[7], [child])
        self.assertIs(isolation._ports[child], item)

        port_snapshot = isolation[child].snapshot_port_meta()
        self.assertEqual(port_snapshot, ("value", "float", None, GraphModel.ExpansionState.CLOSED.value))

    async def test_can_connect_allows_interface_only_input_node_ports(self) -> None:
        """InputNode wrapper ports should allow interfaceOnly connections in their own direction."""

        class Port:
            def __init__(self, connectability=None) -> None:
                self.proxy_attribute = SimpleNamespace(connectability=connectability)
                self.prim = MagicMock()

        isolation = MaterialGraphIsolationModel.__new__(MaterialGraphIsolationModel)
        isolation._model = MagicMock()
        isolation._model.can_connect.return_value = False
        isolation._is_internal_nodegraph_interface_connection = MagicMock(return_value=False)
        isolation._would_create_prim_cycle = MagicMock(return_value=False)

        shader_output = Port()
        shader_input = Port()
        input_node_port = Port(UsdShade.Tokens.interfaceOnly)
        output_node_port = Port()
        isolation._root_ports = {input_node_port, output_node_port}
        isolation._root_inputs = {input_node_port: []}
        isolation._root_outputs = {output_node_port: []}

        self.assertTrue(isolation.can_connect(input_node_port, shader_input))
        self.assertFalse(isolation.can_connect(shader_output, output_node_port))
        isolation._model.can_connect.assert_called_once_with(shader_output, output_node_port)

        isolation._would_create_prim_cycle.return_value = True
        self.assertFalse(isolation.can_connect(input_node_port, shader_input))

    async def test_can_connect_allows_child_output_to_nodegraph_output_sink(self) -> None:
        """Child shader outputs should connect to current NodeGraph output sinks without plugin rejection."""

        class Port:
            def __init__(self, name: str, candidates=None) -> None:
                self.proxy_attribute = SimpleNamespace(
                    name=name,
                    connectability=None,
                    polymorphic_unresolved=False,
                    type_name="color3f",
                )
                self._candidates = candidates or []
                self.prim = None

            def _get_candidate_port_types(self):
                return self._candidates

        nodegraph_path = Sdf.Path("/World/Looks/Graph")
        root_prim = MagicMock()
        root_prim.IsA.side_effect = lambda schema: schema == UsdShade.NodeGraph
        root_prim.GetPath.return_value = nodegraph_path
        source_parent = MagicMock()
        source_parent.GetPath.return_value = nodegraph_path
        source_prim = MagicMock()
        source_prim.GetParent.return_value = source_parent

        source = Port("outputs:out", candidates=["color3f"])
        source.prim = source_prim
        source.proxy_attribute.polymorphic_unresolved = True
        target = Port("outputs:out01")
        target.prim = root_prim

        isolation = MaterialGraphIsolationModel.__new__(MaterialGraphIsolationModel)
        isolation._root = SimpleNamespace(prim=root_prim)
        isolation._root_ports = set()
        isolation._root_inputs = {}
        isolation._root_outputs = {target: []}
        isolation._model = MagicMock()
        isolation._model.can_connect.return_value = False
        isolation._would_create_prim_cycle = MagicMock(return_value=False)

        self.assertTrue(isolation.can_connect(source, target))
        isolation._model.can_connect.assert_called_once_with(source, target)

        # Internal NodeGraph interface wiring bypasses the prim-level cycle
        # detector (which gives false positives for child→parent connections).
        isolation._would_create_prim_cycle.return_value = True
        self.assertTrue(isolation.can_connect(source, target))

    async def test_empty_input_node_port_exports_on_output_side(self) -> None:
        """InputNode Add Port placeholders should be exported as output-side ports."""

        class InputParent:
            """Parent stub that identifies as an InputNode."""

            @staticmethod
            def get_type_name() -> str:
                """Return the graph item type name."""
                return "InputNode"

        class DummyEmptyPort:
            """Empty-port stub with an InputNode-like parent."""

            def __init__(self) -> None:
                self.parent = InputParent()

        isolation = MaterialGraphIsolationModel.__new__(MaterialGraphIsolationModel)
        out = []
        entries = []
        with patch.object(IsolationGraphModel, "EmptyPort", DummyEmptyPort):
            isolation._export_ports(None, [DummyEmptyPort()], 0, False, out, entries, set(), True)

        self.assertGreaterEqual(len(out), 1, "_export_ports should export the empty InputNode port")
        self.assertIsNone(out[0]["inputs"])
        self.assertEqual(out[0]["outputs"], [])

    async def test_empty_output_node_port_exports_as_graph_sink(self) -> None:
        """OutputNode Add Port placeholders should be exported as left-side graph sinks."""

        class OutputParent:
            """Parent stub that identifies as an OutputNode."""

            @staticmethod
            def get_type_name() -> str:
                """Return the graph item type name."""
                return "OutputNode"

        class DummyEmptyPort:
            """Empty-port stub with an OutputNode-like parent."""

            def __init__(self) -> None:
                self.parent = OutputParent()

        isolation = MaterialGraphIsolationModel.__new__(MaterialGraphIsolationModel)
        out = []
        entries = []
        with patch.object(IsolationGraphModel, "EmptyPort", DummyEmptyPort):
            isolation._export_ports(None, [DummyEmptyPort()], 0, False, out, entries, set(), True)

        self.assertGreaterEqual(len(out), 1, "_export_ports should export the empty OutputNode port")
        self.assertEqual(out[0]["inputs"], [])
        self.assertIsNone(out[0]["outputs"])
        self.assertTrue(out[0]["graph_sink"])

    async def test_output_node_ports_export_as_graph_sinks_without_root_cache(self) -> None:
        """Fresh OutputNode ports should render left-side even before root port caches catch up."""

        class DummyModel:
            """Minimal model lookup for _export_ports."""

            def __init__(self, port, inner) -> None:
                self._port = port
                self._inner = inner

            def __getitem__(self, item):
                if item is self._port:
                    return self._inner
                raise KeyError(item)

        class OutputPort:
            """Hashable output-shaped port stub."""

        port = OutputPort()
        port.proxy_attribute = SimpleNamespace(
            name="outputs:out01",
            polymorphic_unresolved=False,
            variability=Sdf.VariabilityVarying,
            connectability=UsdShade.Tokens.full,
        )
        inner = SimpleNamespace(name="out01", type="color3f", expansion_state=0, ports=None, outputs=[])

        isolation = MaterialGraphIsolationModel.__new__(MaterialGraphIsolationModel)
        out = []
        entries = []
        isolation._export_ports(
            DummyModel(port, inner),
            [port],
            0,
            False,
            out,
            entries,
            set(),
            False,
            parent_is_output_node=True,
        )

        self.assertEqual(out[0]["inputs"], [])
        self.assertIsNone(out[0]["outputs"])
        self.assertTrue(out[0]["graph_sink"])

    async def test_material_outputs_export_as_input_side_ports(self) -> None:
        """Root material outputs are USD outputs but graph connection targets."""

        class DummyModel:
            """Minimal model lookup for _export_ports."""

            def __init__(self, port, inner) -> None:
                self._port = port
                self._inner = inner

            def __getitem__(self, item):
                if item is self._port:
                    return self._inner
                raise KeyError(item)

        port = SimpleNamespace()
        port.prim = MagicMock()
        port.prim.IsA.side_effect = lambda schema: schema == UsdShade.Material
        port.proxy_attribute = SimpleNamespace(
            name=f"{UsdShade.Tokens.outputs}:{UsdShade.Tokens.surface}",
            polymorphic_unresolved=False,
            variability=Sdf.VariabilityVarying,
            connectability=UsdShade.Tokens.full,
        )
        inner = SimpleNamespace(name="surface", type="token", expansion_state=0, ports=None)

        isolation = MaterialGraphIsolationModel.__new__(MaterialGraphIsolationModel)
        out = []
        entries = []
        isolation._export_ports(DummyModel(port, inner), [port], 0, False, out, entries, set(), False)

        self.assertEqual(out[0]["inputs"], [])
        self.assertIsNone(out[0]["outputs"])

    async def test_material_output_connection_lists_use_output_sources_as_inputs(self) -> None:
        """Material output USD connections should become graph input-side sources."""

        class MaterialOutputPort:
            """Hashable material output-shaped port stub."""

        source_port = SimpleNamespace(path=Sdf.Path("/World/Looks/Source.outputs:out"))
        material_port = MaterialOutputPort()
        material_port.prim = MagicMock()
        material_port.prim.IsA.side_effect = lambda schema: schema == UsdShade.Material
        material_port.proxy_attribute = SimpleNamespace(name=f"{UsdShade.Tokens.outputs}:{UsdShade.Tokens.surface}")
        material_port.usdshade_port = MagicMock()
        material_port.usdshade_port.HasConnectedSource.return_value = True
        source_prim = MagicMock()
        source_prim.GetPath.return_value = Sdf.Path("/World/Looks/Source")
        source_prim.IsValid.return_value = True
        source_api = MagicMock()
        source_api.GetPrim.return_value = source_prim
        material_port.usdshade_port.GetConnectedSources.return_value = [
            SimpleNamespace(source=source_api, sourceName="out", sourceType=UsdShade.AttributeType.Output)
        ]
        inner = SimpleNamespace(inputs=None, outputs=[source_port])

        isolation = MaterialGraphIsolationModel.__new__(MaterialGraphIsolationModel)
        raw_in, raw_out = isolation._connection_lists_for_port(material_port, inner, set(), {}, {})

        self.assertEqual(raw_in, [source_port])
        self.assertIsNone(raw_out)

    async def test_material_output_connection_lists_filter_inner_outputs_to_usd_sources(self) -> None:
        """Material output cached connections should match the live USD source paths."""

        class MaterialOutputPort:
            """Hashable material output-shaped port stub."""

        live_source_port = SimpleNamespace(path=Sdf.Path("/World/Looks/Source.outputs:out"))
        stale_source_port = SimpleNamespace(path=Sdf.Path("/World/Looks/Other.outputs:out"))
        material_port = MaterialOutputPort()
        material_port.prim = MagicMock()
        material_port.prim.IsA.side_effect = lambda schema: schema == UsdShade.Material
        material_port.proxy_attribute = SimpleNamespace(name=f"{UsdShade.Tokens.outputs}:{UsdShade.Tokens.surface}")
        material_port.usdshade_port = MagicMock()
        material_port.usdshade_port.HasConnectedSource.return_value = True
        source_prim = MagicMock()
        source_prim.GetPath.return_value = Sdf.Path("/World/Looks/Source")
        source_prim.IsValid.return_value = True
        source_api = MagicMock()
        source_api.GetPrim.return_value = source_prim
        material_port.usdshade_port.GetConnectedSources.return_value = [
            SimpleNamespace(source=source_api, sourceName="out", sourceType=UsdShade.AttributeType.Output)
        ]
        mixed_inner = SimpleNamespace(inputs=None, outputs=[stale_source_port, live_source_port])

        isolation = MaterialGraphIsolationModel.__new__(MaterialGraphIsolationModel)
        raw_in, raw_out = isolation._connection_lists_for_port(material_port, mixed_inner, set(), {}, {})

        self.assertEqual(raw_in, [live_source_port])
        self.assertIsNone(raw_out)

    async def test_material_output_connection_lists_prefer_synced_outputs_over_stale_root_cache(self) -> None:
        """Disconnected material outputs should not redraw stale root-cache connections."""

        class MaterialOutputPort:
            """Hashable material output-shaped port stub."""

        stale_source_port = object()
        material_port = MaterialOutputPort()
        material_port.prim = MagicMock()
        material_port.prim.IsA.side_effect = lambda schema: schema == UsdShade.Material
        material_port.proxy_attribute = SimpleNamespace(name=f"{UsdShade.Tokens.outputs}:{UsdShade.Tokens.surface}")
        synced_inner = SimpleNamespace(inputs=None, outputs=[])

        isolation = MaterialGraphIsolationModel.__new__(MaterialGraphIsolationModel)
        raw_in, raw_out = isolation._connection_lists_for_port(
            material_port,
            synced_inner,
            {material_port},
            {},
            {material_port: [stale_source_port]},
        )

        self.assertEqual(raw_in, [])
        self.assertIsNone(raw_out)

    async def test_material_output_connection_lists_drop_stale_inner_outputs_when_usd_disconnected(self) -> None:
        """Disconnected material outputs should not redraw stale inner cache connections."""

        class MaterialOutputPort:
            """Hashable material output-shaped port stub."""

        stale_source_port = object()
        material_port = MaterialOutputPort()
        material_port.prim = MagicMock()
        material_port.prim.IsA.side_effect = lambda schema: schema == UsdShade.Material
        material_port.proxy_attribute = SimpleNamespace(name=f"{UsdShade.Tokens.outputs}:{UsdShade.Tokens.surface}")
        material_port.usdshade_port = MagicMock()
        material_port.usdshade_port.HasConnectedSource.return_value = False
        stale_inner = SimpleNamespace(inputs=None, outputs=[stale_source_port])

        isolation = MaterialGraphIsolationModel.__new__(MaterialGraphIsolationModel)
        raw_in, raw_out = isolation._connection_lists_for_port(material_port, stale_inner, set(), {}, {})

        self.assertEqual(raw_in, [])
        self.assertIsNone(raw_out)

    async def test_material_output_connection_lists_drop_inner_outputs_without_usd_port(self) -> None:
        """Material output cached connections need a live USD source to draw."""

        class MaterialOutputPort:
            """Hashable material output-shaped port stub."""

        stale_source_port = object()
        material_port = MaterialOutputPort()
        material_port.prim = MagicMock()
        material_port.prim.IsA.side_effect = lambda schema: schema == UsdShade.Material
        material_port.proxy_attribute = SimpleNamespace(name=f"{UsdShade.Tokens.outputs}:{UsdShade.Tokens.surface}")
        stale_inner = SimpleNamespace(inputs=None, outputs=[stale_source_port])

        isolation = MaterialGraphIsolationModel.__new__(MaterialGraphIsolationModel)
        raw_in, raw_out = isolation._connection_lists_for_port(material_port, stale_inner, set(), {}, {})

        self.assertEqual(raw_in, [])
        self.assertIsNone(raw_out)

    async def test_material_output_connection_lists_drop_inner_outputs_when_usd_check_fails(self) -> None:
        """Material output cached connections fail closed if USD state cannot be read."""

        class MaterialOutputPort:
            """Hashable material output-shaped port stub."""

        stale_source_port = object()
        material_port = MaterialOutputPort()
        material_port.prim = MagicMock()
        material_port.prim.IsA.side_effect = lambda schema: schema == UsdShade.Material
        material_port.proxy_attribute = SimpleNamespace(name=f"{UsdShade.Tokens.outputs}:{UsdShade.Tokens.surface}")
        material_port.usdshade_port = MagicMock()
        material_port.usdshade_port.HasConnectedSource.side_effect = RuntimeError("stale port")
        stale_inner = SimpleNamespace(inputs=None, outputs=[stale_source_port])

        isolation = MaterialGraphIsolationModel.__new__(MaterialGraphIsolationModel)
        raw_in, raw_out = isolation._connection_lists_for_port(material_port, stale_inner, set(), {}, {})

        self.assertEqual(raw_in, [])
        self.assertIsNone(raw_out)

    async def test_material_output_connection_lists_do_not_fall_back_when_inner_outputs_are_none(self) -> None:
        """Existing inner models are authoritative even before they expose a list."""

        class MaterialOutputPort:
            """Hashable material output-shaped port stub."""

        root_source_port = object()
        material_port = MaterialOutputPort()
        material_port.prim = MagicMock()
        material_port.prim.IsA.side_effect = lambda schema: schema == UsdShade.Material
        material_port.proxy_attribute = SimpleNamespace(name=f"{UsdShade.Tokens.outputs}:{UsdShade.Tokens.surface}")
        unsynced_inner = SimpleNamespace(inputs=None, outputs=None)

        isolation = MaterialGraphIsolationModel.__new__(MaterialGraphIsolationModel)
        raw_in, raw_out = isolation._connection_lists_for_port(
            material_port,
            unsynced_inner,
            {material_port},
            {},
            {material_port: [root_source_port]},
        )

        self.assertIsNone(raw_in)
        self.assertIsNone(raw_out)

    async def test_material_output_connection_lists_fall_back_to_root_cache_without_inner_model(self) -> None:
        """Material outputs should still use root cache before the inner model exists."""

        class MaterialOutputPort:
            """Hashable material output-shaped port stub."""

        root_source_port = object()
        material_port = MaterialOutputPort()
        material_port.prim = MagicMock()
        material_port.prim.IsA.side_effect = lambda schema: schema == UsdShade.Material
        material_port.proxy_attribute = SimpleNamespace(name=f"{UsdShade.Tokens.outputs}:{UsdShade.Tokens.surface}")

        isolation = MaterialGraphIsolationModel.__new__(MaterialGraphIsolationModel)
        raw_in, raw_out = isolation._connection_lists_for_port(
            material_port,
            None,
            {material_port},
            {},
            {material_port: [root_source_port]},
        )

        self.assertEqual(raw_in, [root_source_port])
        self.assertIsNone(raw_out)

    async def test_root_output_connection_lists_prefer_synced_outputs_over_stale_root_cache(self) -> None:
        """OutputNode ports should not redraw stale root-cache connections after disconnect."""

        class RootOutputPort:
            """Hashable nodegraph output-shaped port stub."""

        stale_source_port = object()
        root_output = RootOutputPort()
        root_output.proxy_attribute = SimpleNamespace(name=f"{UsdShade.Tokens.outputs}:out")
        synced_inner = SimpleNamespace(inputs=None, outputs=[])

        isolation = MaterialGraphIsolationModel.__new__(MaterialGraphIsolationModel)
        raw_in, raw_out = isolation._connection_lists_for_port(
            root_output,
            synced_inner,
            {root_output},
            {},
            {root_output: [stale_source_port]},
        )

        self.assertEqual(raw_in, [])
        self.assertIsNone(raw_out)

    async def test_root_output_empty_inputs_skip_usd_fallback_recovery(self) -> None:
        """Explicitly disconnected OutputNode ports should not be recovered from fallback data."""

        class RootOutputPort:
            """Hashable nodegraph output-shaped port stub."""

        root_output = RootOutputPort()
        root_output.proxy_attribute = SimpleNamespace(name=f"{UsdShade.Tokens.outputs}:out")

        isolation = MaterialGraphIsolationModel.__new__(MaterialGraphIsolationModel)
        self.assertTrue(isolation._is_graph_sink_output_port(root_output, {root_output}))

    async def test_root_output_root_cache_fallback_filters_disconnected_usd_sources(self) -> None:
        """OutputNode root-cache fallback should not redraw USD-disconnected wires."""

        class RootOutputPort:
            """Hashable nodegraph output-shaped port stub."""

        stale_source_port = SimpleNamespace(path=Sdf.Path("/World/Looks/Source.outputs:out"))
        root_output = RootOutputPort()
        root_output.proxy_attribute = SimpleNamespace(name=f"{UsdShade.Tokens.outputs}:out")
        root_output.usdshade_port = MagicMock()
        root_output.usdshade_port.HasConnectedSource.return_value = False

        isolation = MaterialGraphIsolationModel.__new__(MaterialGraphIsolationModel)
        raw_in, raw_out = isolation._connection_lists_for_port(
            root_output,
            None,
            {root_output},
            {},
            {root_output: [stale_source_port]},
        )

        self.assertEqual(raw_in, [])
        self.assertIsNone(raw_out)

    async def test_root_output_connection_lists_do_not_fall_back_when_inner_outputs_are_none(self) -> None:
        """Existing OutputNode inner models are authoritative even before they expose a list."""

        class RootOutputPort:
            """Hashable nodegraph output-shaped port stub."""

        root_source_port = object()
        root_output = RootOutputPort()
        root_output.proxy_attribute = SimpleNamespace(name=f"{UsdShade.Tokens.outputs}:out")
        unsynced_inner = SimpleNamespace(inputs=None, outputs=None)

        isolation = MaterialGraphIsolationModel.__new__(MaterialGraphIsolationModel)
        raw_in, raw_out = isolation._connection_lists_for_port(
            root_output,
            unsynced_inner,
            {root_output},
            {},
            {root_output: [root_source_port]},
        )

        self.assertIsNone(raw_in)
        self.assertIsNone(raw_out)

    async def test_root_material_inputs_are_not_exported_on_material_node(self) -> None:
        """Root material inputs are rendered by the InputNode, not the material node."""

        class FakeModel:
            """Minimal model object with nodes and item lookup."""

            def __init__(self, root, values) -> None:
                self.nodes = [root]
                self._values = values

            def __getitem__(self, item):
                return self._values[item]

        material_input = object()
        material_output = object()
        isolation = MaterialGraphIsolationModel.__new__(MaterialGraphIsolationModel)
        isolation._root = object()
        isolation._root_inputs = {material_input: []}
        isolation._root_outputs = {material_output: []}
        isolation._root_ports = {material_input, material_output}
        isolation._nodes = {}
        isolation._ports = {}
        isolation._input_nodes = []
        isolation._output_nodes = []
        isolation._proxy_cache = {}
        isolation._invalid_connection_paths = set()
        isolation._warning_node_paths = set()
        values = {
            isolation._root: SimpleNamespace(
                name="Material",
                type="Material",
                size=(200.0, 100.0),
                display_color=None,
                selected=False,
                valid=True,
                position=(0.0, 0.0),
                ports=[material_output, material_input],
                stacking_order=0,
                expansion_state=0,
            ),
            material_output: SimpleNamespace(name="surface", type="token", ports=None, inputs=[]),
        }
        isolation._model = FakeModel(isolation._root, values)
        isolation._is_material_output_port = lambda port: port is material_output

        snapshot = isolation.export_snapshot(False)

        self.assertEqual([p["port"] for p in snapshot[0]["ports"]], [material_output])

    async def test_dynamic_input_output_wrappers_filter_ports_and_delegate(self) -> None:
        class InputBase:
            @staticmethod
            def get_type_name():
                return "InputNode"

        class OutputBase:
            @staticmethod
            def get_type_name():
                return "OutputNode"

        class EmptyPort:
            def __init__(self, parent):
                self.parent = parent

        class Source:
            label = "source-label"

        source = Source()
        input_port, output_port, filtered_port = object(), object(), object()
        values = {
            source: SimpleNamespace(
                ports=[input_port, output_port, filtered_port],
                add_empty_input_port=True,
                add_empty_output_port=True,
            ),
            input_port: SimpleNamespace(inputs=[], outputs=None),
            output_port: SimpleNamespace(inputs=None, outputs=[]),
            filtered_port: SimpleNamespace(inputs=None, outputs=None),
        }

        class Model:
            def __getitem__(self, item):
                return values[item]

        input_node = _build_input_node_class(InputBase, EmptyPort)(Model(), source)
        output_node = _build_output_node_class(OutputBase, EmptyPort)(Model(), source)
        self.assertEqual(input_node.ports, [input_port, input_node.empty_port])
        self.assertEqual(output_node.ports, [output_port, output_node.empty_port])
        self.assertEqual(input_node.label, "source-label")
        self.assertEqual(input_node.get_type_name(), "InputNode")
        self.assertEqual(output_node.get_type_name(), "OutputNode")
        self.assertNotEqual(hash(input_node), hash(output_node))

    async def test_node_class_resolution_supports_direct_property_and_failure(self) -> None:
        class Direct:
            class InputNode:
                pass

        self.assertIs(_resolve_node_class(Direct, None, "InputNode"), Direct.InputNode)

        class PropertyOwner:
            @property
            def InputNode(self):
                return Direct.InputNode

        instance = PropertyOwner()
        self.assertIs(_resolve_node_class(PropertyOwner, instance, "InputNode"), Direct.InputNode)

        class BrokenOwner:
            @property
            def InputNode(self):
                raise RuntimeError("injected")

        self.assertIsNone(_resolve_node_class(BrokenOwner, BrokenOwner(), "InputNode"))
        self.assertIsNone(_resolve_node_class(Direct, None, "Missing"))

    async def test_current_context_phase_builds_summaries_maps_and_collapse_state(self) -> None:
        isolation = MaterialGraphIsolationModel.__new__(MaterialGraphIsolationModel)
        active_group, active_child = object(), object()
        other_group, other_child = object(), object()
        unused, empty = object(), object()
        ports = [
            {"name": "Active", "port": active_group, "is_group": True, "level": 0, "io_state": 0, "exp": 0},
            {"name": "activeChild", "port": active_child, "level": 1, "io_state": 0},
            {"name": "Other", "port": other_group, "is_group": True, "level": 0, "io_state": 1, "exp": 0},
            {"name": "otherChild", "port": other_child, "level": 1, "io_state": 1},
            {"name": "unused", "port": unused, "level": 0, "io_state": 2},
            {"name": "EmptyPort", "port": empty, "level": 0, "is_empty": True},
        ]
        vm = SimpleNamespace(
            _group_collapse_state={"Active": False},
            _unused_group_expanded=True,
        )
        result = isolation._phase4_current_context(ports, True, IoState, vm)
        names = [port["name"] for port in result]
        self.assertEqual(
            names,
            [
                "Active",
                "activeChild",
                "Other context ports",
                "Other",
                "otherChild",
                "Unused ports",
                "unused",
                "EmptyPort",
            ],
        )
        self.assertEqual(vm._other_summary_port_index, 2)
        self.assertEqual(vm._synthetic_row_indices, {"other": 2, "unused": 5})
        self.assertEqual(vm._scene_idx_to_port[0], active_group)
        self.assertIn(0, vm._scene_group_indices)

        vm._group_collapse_state = {"Active": True}
        collapsed = isolation._phase4_current_context(ports, False, IoState, vm)
        self.assertNotIn("activeChild", [port["name"] for port in collapsed])
        self.assertEqual(collapsed[0]["exp"], 2)

    async def test_all_used_phase_and_group_walk_filter_unused_entries(self) -> None:
        isolation = MaterialGraphIsolationModel.__new__(MaterialGraphIsolationModel)
        ports = [
            {"name": "Active", "is_group": True, "level": 0, "io_state": 0},
            {"name": "unusedChild", "level": 1, "io_state": 2},
            {"name": "Other", "is_group": True, "level": 0, "io_state": 1},
            {"name": "usedChild", "level": 1, "io_state": 1},
            {"name": "unusedLeaf", "level": 0, "io_state": 2},
            {"name": "empty", "level": 0, "is_empty": True},
        ]
        children, next_index = isolation._walk_group(ports, 0, 0)
        self.assertEqual([port["name"] for port in children], ["unusedChild"])
        self.assertEqual(next_index, 2)
        result = isolation._phase4_all_used(ports, IoState)
        self.assertEqual(
            [port["name"] for port in result],
            ["Active", "unusedChild", "Other", "usedChild", "empty"],
        )

    async def test_context_identification_covers_connected_and_fallback_ports(self) -> None:
        port = object()
        connected_model = {port: SimpleNamespace(connected_ports=[object()], inputs=None, outputs=None)}
        fallback_model = {port: SimpleNamespace(connected_ports=[], inputs=[object()], outputs=[])}
        empty_model = {port: SimpleNamespace(connected_ports=[], inputs=[], outputs=[])}
        handles = {
            "current": SimpleNamespace(is_valid=True, context=SimpleNamespace(model=connected_model)),
            "connected": SimpleNamespace(is_valid=True, context=SimpleNamespace(model=connected_model)),
            "fallback": SimpleNamespace(is_valid=True, context=SimpleNamespace(model=fallback_model)),
            "empty": SimpleNamespace(is_valid=True, context=SimpleNamespace(model=empty_model)),
            "invalid": SimpleNamespace(is_valid=False, context=None),
        }
        manager = SimpleNamespace(
            get_context_names=lambda: list(handles),
            get_context=lambda name: handles[name],
        )
        self.assertEqual(
            MaterialGraphIsolationModel._identify_port_contexts(port, "current", manager),
            ["connected", "fallback"],
        )
        self.assertEqual(MaterialGraphIsolationModel._identify_port_contexts(port, "current", None), [])

    async def test_context_probe_extracts_connected_attribute_names_and_cleans_up(self) -> None:
        connected = SimpleNamespace(proxy_attribute=SimpleNamespace(name="inputs:connected"))
        disconnected = SimpleNamespace(proxy_attribute=SimpleNamespace(name="inputs:unused"))
        snapshot = [
            {
                "ports": [
                    {"port": connected, "inputs": [object()], "outputs": None},
                    {"port": disconnected, "inputs": [], "outputs": []},
                    {"port": None, "inputs": [object()]},
                ]
            }
        ]
        temp = SimpleNamespace(export_snapshot=MagicMock(return_value=snapshot), destroy=MagicMock())
        model = SimpleNamespace(nodes=[object()])
        handle = SimpleNamespace(is_valid=True, context=SimpleNamespace(model=model))
        manager = SimpleNamespace(get_context=MagicMock(return_value=handle))
        with patch.object(isolation_module, "MaterialGraphIsolationModel", return_value=temp):
            result = MaterialGraphIsolationModel._probe_context_connections("mdl", manager)
        self.assertEqual(result, {"inputs:connected"})
        temp.export_snapshot.assert_called_once_with(True)
        temp.destroy.assert_called_once_with()

        manager.get_context.return_value = SimpleNamespace(is_valid=False, context=None)
        self.assertEqual(MaterialGraphIsolationModel._probe_context_connections("invalid", manager), set())

    async def test_port_name_type_candidates_and_polymorphic_matching_are_safe(self) -> None:
        proxy_port = SimpleNamespace(proxy_attribute=SimpleNamespace(name="inputs:value", type_name="float"))
        self.assertEqual(MaterialGraphIsolationModel._port_attr_name(proxy_port), "inputs:value")
        fallback_port = SimpleNamespace(proxy_attribute=None, attribute_name="outputs:value")
        self.assertEqual(MaterialGraphIsolationModel._port_attr_name(fallback_port), "outputs:value")
        self.assertEqual(MaterialGraphIsolationModel._port_type_name(proxy_port), "float")

        candidate = SimpleNamespace(_get_candidate_port_types=lambda: ["float", "", "color3f"])
        self.assertEqual(MaterialGraphIsolationModel._candidate_type_names(candidate), {"float", "color3f"})
        broken = SimpleNamespace(_get_candidate_port_types=MagicMock(side_effect=RuntimeError("injected")))
        self.assertEqual(MaterialGraphIsolationModel._candidate_type_names(broken), set())

        source = SimpleNamespace(
            proxy_attribute=SimpleNamespace(type_name="float", polymorphic_unresolved=False),
            _get_candidate_port_types=lambda: ["color3f"],
        )
        target = SimpleNamespace(
            proxy_attribute=SimpleNamespace(type_name="color3f", polymorphic_unresolved=False),
            _get_candidate_port_types=lambda: [],
        )
        self.assertTrue(MaterialGraphIsolationModel._is_polymorphic_nodegraph_output_sink_connection(source, target))
        source._get_candidate_port_types = lambda: []
        source.proxy_attribute.polymorphic_unresolved = True
        self.assertTrue(MaterialGraphIsolationModel._is_polymorphic_nodegraph_output_sink_connection(source, target))

    async def test_valid_state_root_port_and_material_output_helpers(self) -> None:
        isolation = MaterialGraphIsolationModel.__new__(MaterialGraphIsolationModel)
        isolation._warning_node_paths = {"/Warning"}
        warning_prim = SimpleNamespace(GetPath=lambda: Sdf.Path("/Warning"))
        self.assertEqual(isolation._compute_valid_state(True, object()), 0)
        self.assertEqual(isolation._compute_valid_state(False, SimpleNamespace(prim=warning_prim)), 1)
        self.assertEqual(isolation._compute_valid_state(False, object()), 2)

        root_port, input_port, output_port = object(), object(), object()
        isolation._root_ports = {root_port}
        isolation._root_inputs = {input_port}
        isolation._root_outputs = {output_port}
        self.assertTrue(isolation._is_root_port(root_port))
        self.assertTrue(isolation._is_root_port(input_port))
        self.assertTrue(isolation._is_root_port(output_port))
        self.assertFalse(isolation._is_root_port(object()))

        prim = MagicMock()
        prim.IsA.side_effect = lambda schema: schema == UsdShade.Material
        material_output = SimpleNamespace(
            prim=prim,
            proxy_attribute=SimpleNamespace(name="outputs:mtlx:surface"),
        )
        self.assertTrue(isolation._is_material_output_port(material_output))
        prim.IsA.side_effect = RuntimeError("injected")
        self.assertFalse(isolation._is_material_output_port(material_output))

    async def test_export_snapshot_preserves_metadata_connections_and_collapsed_ports(self) -> None:
        """Snapshot export should retain graph semantics without rendering the canvas."""

        class Item:
            """Hashable model item carrying optional USD state."""

        class Model:
            """Minimal graph model used by the snapshot exporter."""

            def __init__(self, nodes, values) -> None:
                self.nodes = nodes
                self._values = values

            def __getitem__(self, item):
                return self._values[item]

        source_node, target_node, backdrop_node = Item(), Item(), Item()
        source_node.prim = UsdShade.Shader.Define(self._stage, "/World/Source").GetPrim()
        target_node.prim = UsdShade.Shader.Define(self._stage, "/World/Target").GetPrim()
        backdrop_node.prim = self._stage.DefinePrim("/World/Backdrop")
        source_node.polymorphic_unresolved = True
        target_node.polymorphic_unresolved = False
        backdrop_node.polymorphic_unresolved = False

        source_port, target_port = Item(), Item()
        source_port.proxy_attribute = SimpleNamespace(name="outputs:out")
        target_port.proxy_attribute = SimpleNamespace(name="inputs:in")
        values = {
            source_node: SimpleNamespace(
                name="Source",
                type="Shader",
                size=(180.0, 90.0),
                display_color=(1.0, 0.0, 0.0),
                selected=True,
                valid=True,
                position=(10.0, 20.0),
                ports=[source_port],
                stacking_order=3,
                expansion_state=1,
            ),
            target_node: SimpleNamespace(
                name="Target",
                type="Shader",
                size=(220.0, 100.0),
                display_color=None,
                selected=False,
                valid=False,
                position=(30.0, 40.0),
                ports=[target_port],
                stacking_order=4,
                expansion_state=2,
            ),
            backdrop_node: SimpleNamespace(
                name="Notes",
                type="Backdrop",
                size=(400.0, 250.0),
                display_color=(0.1, 0.2, 0.3),
                selected=False,
                valid=True,
                position=(0.0, 0.0),
                ports=[],
                stacking_order=1,
                expansion_state=0,
                description="Backdrop description",
            ),
            source_port: SimpleNamespace(
                name="out",
                type="float",
                type_name="float",
                expansion_state=0,
                ports=None,
                inputs=None,
                outputs=[target_port],
            ),
            target_port: SimpleNamespace(
                name="in",
                type="float",
                type_name="float",
                expansion_state=0,
                ports=None,
                inputs=[source_port],
                outputs=None,
            ),
        }
        isolation = MaterialGraphIsolationModel.__new__(MaterialGraphIsolationModel)
        isolation._model = Model([source_node, target_node, backdrop_node], values)
        isolation._root = source_node
        isolation._root_inputs = {}
        isolation._root_outputs = {}
        isolation._root_ports = set()
        isolation._nodes = {}
        isolation._ports = {}
        isolation._input_nodes = []
        isolation._output_nodes = []
        isolation._proxy_cache = {}
        isolation._invalid_connection_paths = {"/World/Target.inputs:in"}
        isolation._warning_node_paths = {"/World/Target"}

        with patch.object(isolation_module, "get_node_menu_items", return_value=["Inspect"]):
            snapshot = isolation.export_snapshot(True)

        source_snapshot, target_snapshot, backdrop_snapshot = snapshot
        self.assertEqual(source_snapshot["name"], "Source")
        self.assertEqual(source_snapshot["size_w"], 180.0)
        self.assertTrue(source_snapshot["selected"])
        self.assertTrue(source_snapshot["polymorphic_unresolved"])
        self.assertEqual(source_snapshot["ports"][0]["outputs"], [target_port])
        self.assertEqual(target_snapshot["valid_state"], 1)
        self.assertEqual(len(target_snapshot["ports"]), 1)
        self.assertTrue(target_snapshot["ports"][0]["is_empty"])
        self.assertTrue(target_snapshot["ports"][0]["has_error"])
        self.assertEqual(target_snapshot["ports"][0]["inputs"], [source_port])
        self.assertTrue(backdrop_snapshot["is_backdrop"])
        self.assertEqual(backdrop_snapshot["description"], "Backdrop description")
        self.assertEqual(backdrop_snapshot["size_h"], 250.0)
        self.assertTrue(backdrop_snapshot["has_menu"])

    async def test_export_snapshot_filters_unconnected_ports_when_minimized(self) -> None:
        """Minimized nodes should keep connected ports and omit unused leaf ports."""

        class Item:
            """Hashable graph item."""

        connected, unused = Item(), Item()
        node = Item()
        node.polymorphic_unresolved = False
        values = {
            node: SimpleNamespace(
                name="Node",
                type="Shader",
                size=(200.0, 100.0),
                display_color=None,
                selected=False,
                valid=True,
                position=None,
                ports=[connected, unused],
                stacking_order=0,
                expansion_state=1,
            ),
            connected: SimpleNamespace(
                name="connected",
                type="float",
                expansion_state=0,
                ports=None,
                inputs=[connected],
                outputs=None,
            ),
            unused: SimpleNamespace(
                name="unused",
                type="float",
                expansion_state=0,
                ports=None,
                inputs=[],
                outputs=None,
            ),
        }

        class Model:
            nodes = [node]

            def __getitem__(self, item):
                return values[item]

        isolation = MaterialGraphIsolationModel.__new__(MaterialGraphIsolationModel)
        isolation._model = Model()
        isolation._root = node
        isolation._root_inputs = {}
        isolation._root_outputs = {}
        isolation._root_ports = set()
        isolation._nodes = {}
        isolation._ports = {}
        isolation._input_nodes = []
        isolation._output_nodes = []
        isolation._proxy_cache = {}
        isolation._invalid_connection_paths = set()
        isolation._warning_node_paths = set()
        with patch.object(isolation_module, "get_node_menu_items", return_value=[]):
            snapshot = isolation.export_snapshot(False)
        self.assertEqual([entry["name"] for entry in snapshot[0]["ports"]], ["connected"])

    async def test_export_snapshot_classifies_input_ports_without_ui(self) -> None:
        """InputNode context filtering should operate entirely on snapshot data."""

        class Item:
            """Hashable graph item."""

        root = Item()

        class InputNode:
            """Minimal InputNode-shaped item."""

            def __init__(self) -> None:
                self.source = root

            @staticmethod
            def get_type_name() -> str:
                return "InputNode"

        node = InputNode()
        active_a, active_b, other, unused = Item(), Item(), Item(), Item()
        ports = [active_a, active_b, other, unused]
        for port, name in zip(ports, ("activeA", "activeB", "other", "unused")):
            port.proxy_attribute = SimpleNamespace(name=f"inputs:{name}")
        values = {
            root: SimpleNamespace(nodes=[]),
            active_a: SimpleNamespace(inputs=None, outputs=[active_b]),
            active_b: SimpleNamespace(inputs=[active_a], outputs=None),
            other: SimpleNamespace(inputs=[], outputs=None),
            unused: SimpleNamespace(inputs=[], outputs=None),
        }

        class Model:
            nodes = [node]

            def __getitem__(self, item):
                return values[item]

        node_proxy = SimpleNamespace(
            snapshot_node=lambda: ("Inputs", "InputNode", 200.0, (0.0, 0.0), None, False, True, ports)
        )
        port_proxies = {
            port: SimpleNamespace(snapshot_port_meta=lambda name=name: (name, "float", None, 0))
            for port, name in zip(ports, ("activeA", "activeB", "other", "unused"))
        }
        isolation = MaterialGraphIsolationModel.__new__(MaterialGraphIsolationModel)
        isolation._model = Model()
        isolation._root = root
        isolation._root_inputs = {}
        isolation._root_outputs = {}
        isolation._root_ports = set()
        isolation._nodes = {}
        isolation._ports = {port: node for port in ports}
        isolation._input_nodes = [node]
        isolation._output_nodes = []
        isolation._proxy_cache = {}
        isolation._invalid_connection_paths = set()
        isolation._warning_node_paths = set()
        vm = SimpleNamespace(
            mode=InputNodeViewMode.CURRENT_CONTEXT,
            _current_context="mdl",
            _context_manager_ref=None,
            _ctx_connected_attrs={"otherContext": {"inputs:other"}},
            _port_contexts={},
            _other_group_expanded=False,
            _unused_group_expanded=False,
            _group_collapse_state={},
        )

        def proxy_for(_self, item):
            return node_proxy if item is node else port_proxies[item]

        with (
            patch.object(MaterialGraphIsolationModel, "__getitem__", proxy_for),
            patch.object(isolation_module, "get_node_menu_items", return_value=[]),
        ):
            snapshot = isolation.export_snapshot(False, vm)

        names = [entry["name"] for entry in snapshot[0]["ports"]]
        self.assertEqual(names, ["activeA", "activeB", "Other context ports", "Unused ports"])
        self.assertEqual(vm._ctx_connected_attrs["mdl"], {"inputs:activeA", "inputs:activeB"})
        self.assertEqual(vm._port_contexts[id(other)], ["otherContext"])
        self.assertEqual(vm._port_contexts[id(unused)], [])

    async def test_invalid_shader_snapshot_falls_back_to_authored_usd_ports(self) -> None:
        """Invalid shader definitions should still expose their authored USD ports."""

        class Node:
            """Hashable shader model item."""

        shader = UsdShade.Shader.Define(self._stage, "/World/InvalidShader")
        shader.CreateInput("roughness", Sdf.ValueTypeNames.Float)
        shader.CreateOutput("out", Sdf.ValueTypeNames.Token)
        node = Node()
        node.prim = shader.GetPrim()
        node.polymorphic_unresolved = False
        values = {
            node: SimpleNamespace(
                name="Invalid",
                type="Shader",
                size=(200.0, 100.0),
                display_color=None,
                selected=False,
                valid=False,
                position=(0.0, 0.0),
                ports=None,
                stacking_order=0,
                expansion_state=0,
            )
        }

        class Model:
            nodes = [node]

            def __getitem__(self, item):
                return values[item]

        isolation = MaterialGraphIsolationModel.__new__(MaterialGraphIsolationModel)
        isolation._model = Model()
        isolation._root = node
        isolation._root_inputs = {}
        isolation._root_outputs = {}
        isolation._root_ports = set()
        isolation._nodes = {}
        isolation._ports = {}
        isolation._input_nodes = []
        isolation._output_nodes = []
        isolation._proxy_cache = {}
        isolation._invalid_connection_paths = set()
        isolation._warning_node_paths = set()
        with patch.object(isolation_module, "get_node_menu_items", return_value=[]):
            snapshot = isolation.export_snapshot(False)

        self.assertEqual(snapshot[0]["valid_state"], 2)
        self.assertEqual({entry["name"] for entry in snapshot[0]["ports"]}, {"roughness", "out"})
