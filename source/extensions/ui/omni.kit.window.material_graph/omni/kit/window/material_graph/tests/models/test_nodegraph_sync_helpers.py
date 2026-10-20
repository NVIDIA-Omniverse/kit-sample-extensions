# pylint: disable=relative-beyond-top-level,no-member,protected-access
import logging
from unittest.mock import MagicMock, patch

import omni.UsdMdl
from pxr import Sdf, UsdShade

from ...scripts.commands.wrappers.nodes import CreateShader
from ...scripts.commands.wrappers.ports import ConnectInputToSource, ConnectPortToSource
from ...scripts.config.paths import Paths
from ...scripts.models.graph.isolation import MaterialGraphIsolationModel
from ...scripts.models.graph.nodes.material import MaterialModel
from ...scripts.models.graph.nodes.nodegraph.model import NodeGraphModel
from ...scripts.plugins.impl.mdl.plugin import MdlPlugin
from ...scripts.plugins.impl.mdl.polymorphic import MdlPolymorphicResolver
from ...scripts.ui.graph_canvas_view import GraphCanvasView
from ...scripts.utils.sdr_wrappers import resolve_property_type_name, wrap_shader_node
from ...scripts.validation.validator import MaterialValidator
from ..base import MaterialGraphTestBase
from .helpers import DummyPlugin

logger = logging.getLogger(__name__)


class TestNodegraphSyncHelpers(MaterialGraphTestBase):
    """Nodegraph sync helper coverage."""

    async def setUp(self) -> None:
        """Load scene and initialize a material model."""
        await super().setUp()
        await self._load_scene("simple.usda")
        self._material_path = Sdf.Path("/World/Looks/material")
        self._plugin = DummyPlugin()
        self._validator = MaterialValidator()
        material_prim = self._get_prim_at_path(self._material_path)
        self._model = MaterialModel(material_prim, "universal", self._usd_context, self._plugin, self._validator)
        self._model.sync()

    async def test_sync_children_removes_missing(self) -> None:
        """_sync_children should drop removed prims."""
        child_paths = list(self._model._children.keys())
        self.assertTrue(child_paths)
        removed = child_paths[0]
        self._stage.RemovePrim(removed)

        self._model._sync_children()
        self.assertNotIn(removed, self._model._children)

    async def test_remove_stale_children_clears_entry(self) -> None:
        """_remove_stale_children should destroy removed entries."""
        child_paths = list(self._model._children.keys())
        self.assertTrue(child_paths)
        stale_path = child_paths[0]

        self._model._remove_stale_children([stale_path])
        self.assertNotIn(stale_path, self._model._children)

    async def test_sync_child_ports_invokes_children(self) -> None:
        """_sync_child_ports should call child sync_ports."""
        child = next(iter(self._model._children.values()))
        with patch.object(child, "sync_ports") as mock_sync:
            self._model._sync_child_ports()
        mock_sync.assert_called()

    async def test_polymorphic_resolver_caches_sdr_nodes(self) -> None:
        """Repeated overload lookups should reuse resolver-owned SDR node cache."""
        resolver = MdlPolymorphicResolver("mdl")
        source_asset = Sdf.AssetPath("test.mdl")
        sdr_node = object()

        with (
            patch("omni.UsdMdl.RegistryUtils.GetShaderNode", return_value=sdr_node) as get_shader_node,
            patch(
                "omni.kit.window.material_graph.scripts.plugins.impl.mdl.polymorphic.wrap_shader_node",
                lambda node: node,
            ),
        ):
            self.assertIs(resolver._get_sdr_node(source_asset, "fn(float)"), sdr_node)
            self.assertIs(resolver._get_sdr_node(source_asset, "fn(float)"), sdr_node)

        get_shader_node.assert_called_once_with(source_asset, "fn(float)")

    async def test_polymorphic_resolver_does_not_pin_missing_sdr_nodes(self) -> None:
        """Transient SDR misses should be retried instead of cached as permanent misses."""
        resolver = MdlPolymorphicResolver("mdl")
        source_asset = Sdf.AssetPath("test.mdl")
        sdr_node = object()

        with (
            patch("omni.UsdMdl.RegistryUtils.GetShaderNode", side_effect=[None, sdr_node]) as get_shader_node,
            patch(
                "omni.kit.window.material_graph.scripts.plugins.impl.mdl.polymorphic.wrap_shader_node",
                lambda node: node,
            ),
        ):
            self.assertIsNone(resolver._get_sdr_node(source_asset, "fn(float)"))
            self.assertIs(resolver._get_sdr_node(source_asset, "fn(float)"), sdr_node)

        self.assertEqual(get_shader_node.call_count, 2)

    async def test_polymorphic_graph_index_collects_connection_constraints(self) -> None:
        """Graph index should precompute direct input and consumer output constraints once."""
        nodegraph = UsdShade.NodeGraph.Define(self._stage, self._material_path.AppendChild("IndexedGraph"))
        source = UsdShade.Shader.Define(self._stage, nodegraph.GetPrim().GetPath().AppendChild("source"))
        target = UsdShade.Shader.Define(self._stage, nodegraph.GetPrim().GetPath().AppendChild("target"))
        source_output = source.CreateOutput("out", Sdf.ValueTypeNames.Float)
        target_input = target.CreateInput("in", Sdf.ValueTypeNames.Float)
        target_input.ConnectToSource(source_output)

        resolver = MdlPolymorphicResolver("mdl")
        resolver.cache_graph_connection_index(nodegraph.GetPrim())
        index = resolver._graph_connection_indexes[str(nodegraph.GetPrim().GetPath())]

        source_key = str(source.GetPrim().GetPath())
        target_key = str(target.GetPrim().GetPath())
        self.assertIn(("in", "float", True), index["input_constraints"][target_key])
        self.assertIn(("out", "float", False), index["output_constraints"][source_key])

    async def test_connection_notify_invalidates_polymorphic_runtime_cache(self) -> None:
        """Connection-only updates should invalidate resolver state without forcing full sync."""
        self._plugin.invalidate_polymorphic_runtime_cache = MagicMock()
        item = MagicMock()
        self._model._item_changed = MagicMock()

        self._model.notify_connection_changed(item)

        self._plugin.invalidate_polymorphic_runtime_cache.assert_called_once_with()
        self._model._item_changed.assert_called_once_with(item)

    async def test_connection_notify_syncs_changed_port_owner(self) -> None:
        """Connection-only rebuilds should see refreshed polymorphic state for the owning node."""
        prim_model = MagicMock()
        item = MagicMock(prim_model=prim_model)
        self._model._item_changed = MagicMock()

        self._model.notify_connection_changed(item)

        item.sync.assert_not_called()
        prim_model.sync.assert_called_once_with()
        self._model._item_changed.assert_called_once_with(item)

    async def test_connection_notify_syncs_root_owned_port(self) -> None:
        """Root-owned material/nodegraph ports should still refresh their connection cache."""
        item = MagicMock(prim_model=self._model)
        self._model._item_changed = MagicMock()

        self._model.notify_connection_changed(item)

        item.sync.assert_called_once_with()
        self._model._item_changed.assert_called_once_with(item)

    async def test_connection_notify_none_syncs_before_visual_callback(self) -> None:
        """Full connection refreshes should rebuild from synced model state."""
        visual_sync = MagicMock()
        self._model.sync = MagicMock()
        self._model._item_changed = MagicMock()
        self._model.set_connection_visual_sync_callback(visual_sync)

        self._model.notify_connection_changed(None)

        self._model.sync.assert_called_once_with(sync_reason="connection_changed")
        visual_sync.assert_called_once_with(None)
        self._model._item_changed.assert_called_once_with(None)

    async def test_connection_notify_none_suppresses_duplicate_item_changed_sync(self) -> None:
        """Full connection refresh should not sync again through item-changed subscribers."""
        self._model.sync = MagicMock()

        self._model.notify_connection_changed(None)

        self._model.sync.assert_called_once_with(sync_reason="connection_changed")

    async def test_nodegraph_child_exports_authored_interface_ports(self) -> None:
        """NodeGraph children should expose authored inputs/outputs in the parent graph."""
        nodegraph = UsdShade.NodeGraph.Define(self._stage, self._material_path.AppendChild("NestedGraph"))
        nodegraph.CreateInput("a", Sdf.ValueTypeNames.Float)
        nodegraph.CreateOutput("out", Sdf.ValueTypeNames.Float)

        self._model.sync()
        child = self._model._children.get(nodegraph.GetPrim().GetPath())
        self.assertIsNotNone(child)

        port_names = {port.attribute_name for port in child.ports}
        self.assertIn("inputs:a", port_names)
        self.assertIn("outputs:out", port_names)

    async def test_nodegraph_interface_ports_mirror_unresolved_child_ports(self) -> None:
        """NodeGraph interface ports should display unresolved when linked child ports are unresolved."""
        nodegraph = UsdShade.NodeGraph.Define(self._stage, self._material_path.AppendChild("PolyGraph"))
        ng_input = nodegraph.CreateInput("a", Sdf.ValueTypeNames.Float)
        ng_output = nodegraph.CreateOutput("out", Sdf.ValueTypeNames.Float)
        child_graph = UsdShade.NodeGraph.Define(self._stage, nodegraph.GetPrim().GetPath().AppendChild("poly"))
        child_input = child_graph.CreateInput("a", Sdf.ValueTypeNames.Float)
        child_output = child_graph.CreateOutput("out", Sdf.ValueTypeNames.Float)
        child_input.ConnectToSource(ng_input)
        ng_output.ConnectToSource(child_output)

        self._model.sync()
        nodegraph_model = self._model._children[nodegraph.GetPrim().GetPath()]
        child_graph_model = nodegraph_model._children[child_graph.GetPrim().GetPath()]
        child_input_model = child_graph_model._inputs.get_child_by_path(child_input.GetAttr().GetPath())
        child_output_model = child_graph_model._outputs.get_child_by_path(child_output.GetAttr().GetPath())

        child_input_model.proxy_attribute.polymorphic_unresolved = True
        child_input_model.proxy_attribute.type_name = Sdf.ValueTypeNames.Int
        child_input_model.update_proxy_attribute(child_input_model.proxy_attribute)
        child_output_model.proxy_attribute.polymorphic_unresolved = True
        child_output_model.proxy_attribute.type_name = Sdf.ValueTypeNames.Int
        child_output_model.update_proxy_attribute(child_output_model.proxy_attribute)

        nodegraph_model._sync_interface_polymorphic_flags()
        input_model = nodegraph_model._inputs.get_child_by_path(ng_input.GetAttr().GetPath())
        output_model = nodegraph_model._outputs.get_child_by_path(ng_output.GetAttr().GetPath())

        self.assertTrue(input_model.proxy_attribute.polymorphic_unresolved)
        self.assertTrue(output_model.proxy_attribute.polymorphic_unresolved)
        self.assertEqual(input_model.type, Sdf.ValueTypeNames.Int)
        self.assertEqual(output_model.type, Sdf.ValueTypeNames.Int)

        child_input_model.proxy_attribute.polymorphic_unresolved = False
        child_input_model.proxy_attribute.type_name = Sdf.ValueTypeNames.Float
        child_input_model.update_proxy_attribute(child_input_model.proxy_attribute)
        child_output_model.proxy_attribute.polymorphic_unresolved = False
        child_output_model.proxy_attribute.type_name = Sdf.ValueTypeNames.Float
        child_output_model.update_proxy_attribute(child_output_model.proxy_attribute)

        nodegraph_model._sync_interface_polymorphic_flags()

        self.assertFalse(input_model.proxy_attribute.polymorphic_unresolved)
        self.assertFalse(output_model.proxy_attribute.polymorphic_unresolved)
        self.assertEqual(input_model.type, Sdf.ValueTypeNames.Float)
        self.assertEqual(output_model.type, Sdf.ValueTypeNames.Float)

    async def test_output_node_empty_port_creates_connected_interface_output(self) -> None:
        """Connecting to OutputNode Add Port should create and connect a nodegraph output."""
        nodegraph = UsdShade.NodeGraph.Define(self._stage, self._material_path.AppendChild("OutputAddPortGraph"))
        child_graph = UsdShade.NodeGraph.Define(self._stage, nodegraph.GetPrim().GetPath().AppendChild("source"))
        child_output = child_graph.CreateOutput("out", Sdf.ValueTypeNames.Color3f)

        self._model.sync()
        nodegraph_model = self._model._children[nodegraph.GetPrim().GetPath()]
        child_graph_model = nodegraph_model._children[child_graph.GetPrim().GetPath()]
        source_model = child_graph_model._outputs.get_child_by_path(child_output.GetAttr().GetPath())
        self.assertIsNotNone(source_model)

        isolation = MaterialGraphIsolationModel(nodegraph_model, nodegraph_model)
        try:
            isolation.add_input_or_output((0.0, 0.0), False)
            output_node = next(node for node in isolation.nodes if type(node).get_type_name() == "OutputNode")
            empty_port = output_node.empty_port
            self.assertIsNotNone(empty_port)

            isolation[empty_port].inputs = [source_model]

            created_outputs = nodegraph.GetOutputs()
            self.assertEqual(len(created_outputs), 1)
            self.assertTrue(created_outputs[0].HasConnectedSource())
            self.assertEqual(created_outputs[0].GetConnectedSource()[0].GetPrim(), child_graph.GetPrim())
        finally:
            isolation.destroy()

    def _find_real_mdl_polymorphic_node(self, base_name: str = "test_poly_abs"):
        """Find a real MDL polymorphic shader family from registered modules."""
        plugin = MdlPlugin(load_catalog=False)
        try:
            test_module = str(Paths.DATA_PATH / "tests" / "mdl" / "test_poly_abs.mdl")
            source_assets = [Sdf.AssetPath(test_module, test_module)] + plugin._resolve_source_assets(id(self))
            plugin._ensure_modules_registered(source_assets, id(self))
            for source_asset in source_assets:
                try:
                    subidentifiers = list(omni.UsdMdl.RegistryUtils.GetSubIdentifiersForAsset(source_asset) or [])
                except RuntimeError as exc:
                    logger.warning(
                        "failed to list MDL subidentifiers for %s while finding %s: %s",
                        source_asset,
                        base_name,
                        exc,
                        exc_info=True,
                    )
                    continue
                family = [sub for sub in subidentifiers if str(sub).split("(")[0].strip() == base_name]
                if len(family) <= 1:
                    continue
                fallback = None
                for subidentifier in family:
                    try:
                        sdr_node = wrap_shader_node(
                            omni.UsdMdl.RegistryUtils.GetShaderNode(source_asset, subidentifier)
                        )
                    except RuntimeError as exc:
                        logger.warning(
                            "failed to resolve MDL shader node %s from %s: %s",
                            subidentifier,
                            source_asset,
                            exc,
                            exc_info=True,
                        )
                        continue
                    if not (sdr_node and sdr_node.GetShaderOutputNames()):
                        continue
                    if fallback is None:
                        fallback = (source_asset, family, subidentifier, sdr_node)
                    first_output = sdr_node.GetShaderOutput(sdr_node.GetShaderOutputNames()[0])
                    if first_output and resolve_property_type_name(first_output) in ("color", "color3f"):
                        return source_asset, family, subidentifier, sdr_node
                if fallback is not None:
                    return fallback
        finally:
            plugin.destroy()
        self.skipTest(f"real MDL polymorphic family not available: {base_name}")

    @staticmethod
    def _make_resolve_port_canvas_view(isolation, snapshot):
        """Build a minimal GraphCanvasView shell for _resolve_port tests."""
        canvas_view = GraphCanvasView.__new__(GraphCanvasView)
        canvas_view._model = isolation
        canvas_view._scene_model_nodes = [entry["node"] for entry in snapshot]
        canvas_view._input_node_vm = None
        canvas_view._fallback_port_map = {}
        return canvas_view

    async def test_real_mdl_polymorphic_outputnode_add_port_creates_connection(self) -> None:
        """Real MDL polymorphic output wired to OutputNode Add Port should create a connection."""
        source_asset, family, subidentifier, sdr_node = self._find_real_mdl_polymorphic_node("test_poly_abs")
        nodegraph = UsdShade.NodeGraph.Define(self._stage, self._material_path.AppendChild("RealMdlPolyGraph"))
        result = CreateShader(
            nodegraph.GetPrim().GetPath(),
            sdr_node,
            (0.0, 0.0),
            source_asset_path=source_asset.path,
            context="mdl",
            subidentifier=subidentifier,
            is_polymorphic=True,
            polymorphic_subidentifiers=list(family),
        )
        self.assertTrue(result.success)

        plugin = MdlPlugin(load_catalog=False)
        # Seed the resolver cache so the model sees this real family as unresolved.
        plugin._polymorphic.cache_family_overloads(source_asset.path, "test_poly_abs", family)
        nodegraph_model = NodeGraphModel(
            nodegraph.GetPrim(),
            "mdl",
            self._usd_context,
            plugin,
            None,
            sync=True,
        )
        nodegraph_model.validator = MaterialValidator()
        try:
            shader_model = nodegraph_model._children[result.payload.GetPath()]
            output_name = sdr_node.GetShaderOutputNames()[0]
            shader_output = UsdShade.Shader(result.payload).GetOutput(output_name)
            source_model = shader_model._outputs.get_child_by_path(shader_output.GetAttr().GetPath())
            self.assertIsNotNone(source_model)
            self.assertTrue(source_model.proxy_attribute.polymorphic_unresolved)

            isolation = MaterialGraphIsolationModel(nodegraph_model, nodegraph_model)
            try:
                isolation.add_input_or_output((0.0, 0.0), False)
                output_node = next(node for node in isolation.nodes if type(node).get_type_name() == "OutputNode")
                snapshot = isolation.export_snapshot(True)
                canvas_view = self._make_resolve_port_canvas_view(isolation, snapshot)

                shader_node_index = canvas_view._scene_model_nodes.index(shader_model)
                shader_port_index = snapshot[shader_node_index]["ports"].index(
                    next(port for port in snapshot[shader_node_index]["ports"] if port["port"] is source_model)
                )
                output_node_index = canvas_view._scene_model_nodes.index(output_node)
                empty_port_index = snapshot[output_node_index]["ports"].index(
                    next(port for port in snapshot[output_node_index]["ports"] if port.get("is_empty"))
                )
                resolved_source = canvas_view._resolve_port(shader_node_index, shader_port_index)
                resolved_empty = canvas_view._resolve_port(output_node_index, empty_port_index)

                self.assertIs(resolved_source, source_model)
                self.assertIs(resolved_empty, output_node.empty_port)
                isolation[resolved_empty].inputs = [resolved_source]

                created_outputs = nodegraph.GetOutputs()
                self.assertEqual(len(created_outputs), 1)
                self.assertTrue(created_outputs[0].HasConnectedSource())
                source_prim = created_outputs[0].GetConnectedSource()[0].GetPrim()
                self.assertEqual(source_prim, result.payload)

                nodegraph_model.sync()
                interface_model = nodegraph_model._outputs.get_child_by_path(created_outputs[0].GetAttr().GetPath())
                self.assertIsNotNone(interface_model)
                self.assertTrue(interface_model.proxy_attribute.polymorphic_unresolved)

                consumer = UsdShade.Shader.Define(self._stage, self._material_path.AppendChild("RealMdlPolyConsumer"))
                consumer_input = consumer.CreateInput("in", Sdf.ValueTypeNames.Float)
                concrete_result = ConnectInputToSource(consumer_input, created_outputs[0])
                self.assertTrue(concrete_result.success)

                nodegraph_model.sync()
                shader_model.sync()
                interface_model = nodegraph_model._outputs.get_child_by_path(created_outputs[0].GetAttr().GetPath())
                state = plugin.get_polymorphic_state_for_prim(result.payload)
                candidate_types = []
                for candidate in state.candidates:
                    candidate_node = wrap_shader_node(omni.UsdMdl.RegistryUtils.GetShaderNode(source_asset, candidate))
                    candidate_output = candidate_node.GetShaderOutput(created_outputs[0].GetBaseName())
                    candidate_types.append(
                        (candidate, resolve_property_type_name(candidate_output) if candidate_output else None)
                    )
                self.assertFalse(
                    interface_model.proxy_attribute.polymorphic_unresolved,
                    (state.to_dict(), created_outputs[0].GetBaseName(), candidate_types),
                )
                self.assertFalse(shader_model.polymorphic_unresolved, state.to_dict())
                self.assertEqual(state.candidates, ("test_poly_abs(float)",))
            finally:
                isolation.destroy()
        finally:
            nodegraph_model.destroy()
            plugin.destroy()

    async def test_real_mdl_polymorphic_existing_output_port_creates_connection(self) -> None:
        """Real MDL polymorphic output should connect to an existing NodeGraph output port."""
        source_asset, family, subidentifier, sdr_node = self._find_real_mdl_polymorphic_node("test_poly_abs")
        nodegraph = UsdShade.NodeGraph.Define(
            self._stage, self._material_path.AppendChild("RealMdlExistingOutputGraph")
        )
        ng_output = nodegraph.CreateOutput("out", Sdf.ValueTypeNames.Color3f)
        result = CreateShader(
            nodegraph.GetPrim().GetPath(),
            sdr_node,
            (0.0, 0.0),
            source_asset_path=source_asset.path,
            context="mdl",
            subidentifier=subidentifier,
            is_polymorphic=True,
            polymorphic_subidentifiers=list(family),
        )
        self.assertTrue(result.success)

        plugin = MdlPlugin(load_catalog=False)
        plugin._polymorphic.cache_family_overloads(source_asset.path, "test_poly_abs", family)
        nodegraph_model = NodeGraphModel(nodegraph.GetPrim(), "mdl", self._usd_context, plugin, None, sync=True)
        nodegraph_model.validator = MaterialValidator()
        try:
            shader_model = nodegraph_model._children[result.payload.GetPath()]
            output_name = sdr_node.GetShaderOutputNames()[0]
            shader_output = UsdShade.Shader(result.payload).GetOutput(output_name)
            source_model = shader_model._outputs.get_child_by_path(shader_output.GetAttr().GetPath())
            interface_model = nodegraph_model._outputs.get_child_by_path(ng_output.GetAttr().GetPath())
            self.assertIsNotNone(source_model)
            self.assertIsNotNone(interface_model)

            isolation = MaterialGraphIsolationModel(nodegraph_model, nodegraph_model)
            try:
                isolation.add_input_or_output((0.0, 0.0), False)
                snapshot = isolation.export_snapshot(True)
                canvas_view = self._make_resolve_port_canvas_view(isolation, snapshot)
                shader_node_index = canvas_view._scene_model_nodes.index(shader_model)
                shader_port_index = snapshot[shader_node_index]["ports"].index(
                    next(port for port in snapshot[shader_node_index]["ports"] if port["port"] is source_model)
                )
                output_node = next(node for node in isolation.nodes if type(node).get_type_name() == "OutputNode")
                output_node_index = canvas_view._scene_model_nodes.index(output_node)
                output_port_index = snapshot[output_node_index]["ports"].index(
                    next(port for port in snapshot[output_node_index]["ports"] if port["port"] is interface_model)
                )
                resolved_source = canvas_view._resolve_port(shader_node_index, shader_port_index)
                resolved_output = canvas_view._resolve_port(output_node_index, output_port_index)

                self.assertTrue(isolation.can_connect(resolved_source, resolved_output))
                isolation[resolved_output].inputs = [resolved_source]

                self.assertTrue(ng_output.HasConnectedSource())
                self.assertEqual(ng_output.GetConnectedSource()[0].GetPrim(), result.payload)
                self.assertTrue(interface_model.proxy_attribute.polymorphic_unresolved)

                isolation[resolved_output].inputs = []
                self.assertFalse(ng_output.HasConnectedSource())
                self.assertFalse(interface_model.proxy_attribute.polymorphic_unresolved)

                isolation.clear_caches()
                snapshot = isolation.export_snapshot(True)
                canvas_view = self._make_resolve_port_canvas_view(isolation, snapshot)
                shader_node_index = canvas_view._scene_model_nodes.index(shader_model)
                shader_port_index = snapshot[shader_node_index]["ports"].index(
                    next(port for port in snapshot[shader_node_index]["ports"] if port["port"] is source_model)
                )
                output_node = next(node for node in isolation.nodes if type(node).get_type_name() == "OutputNode")
                output_node_index = canvas_view._scene_model_nodes.index(output_node)
                output_port_index = snapshot[output_node_index]["ports"].index(
                    next(port for port in snapshot[output_node_index]["ports"] if port["port"] is interface_model)
                )
                resolved_source = canvas_view._resolve_port(shader_node_index, shader_port_index)
                resolved_output = canvas_view._resolve_port(output_node_index, output_port_index)

                with patch.object(nodegraph_model, "can_connect", return_value=False) as delegate_can_connect:
                    self.assertTrue(isolation.can_connect(resolved_source, resolved_output))
                    delegate_can_connect.assert_called_once_with(resolved_source, resolved_output)

                self.assertTrue(isolation.can_connect(resolved_source, resolved_output))
                isolation[resolved_output].inputs = [resolved_source]
                self.assertTrue(ng_output.HasConnectedSource())
            finally:
                isolation.destroy()
        finally:
            nodegraph_model.destroy()
            plugin.destroy()

    async def test_real_mdl_polymorphic_inputnode_add_port_promotes_from_external_int(self) -> None:
        """Real MDL polymorphic input through a NodeGraph input should promote from an external int."""
        source_asset, family, subidentifier, sdr_node = self._find_real_mdl_polymorphic_node("test_poly_abs")
        nodegraph = UsdShade.NodeGraph.Define(self._stage, self._material_path.AppendChild("RealMdlPolyInputGraph"))
        result = CreateShader(
            nodegraph.GetPrim().GetPath(),
            sdr_node,
            (0.0, 0.0),
            source_asset_path=source_asset.path,
            context="mdl",
            subidentifier=subidentifier,
            is_polymorphic=True,
            polymorphic_subidentifiers=list(family),
        )
        self.assertTrue(result.success)

        plugin = MdlPlugin(load_catalog=False)
        plugin._polymorphic.cache_family_overloads(source_asset.path, "test_poly_abs", family)
        nodegraph_model = NodeGraphModel(nodegraph.GetPrim(), "mdl", self._usd_context, plugin, None, sync=True)
        nodegraph_model.validator = MaterialValidator()
        try:
            shader_model = nodegraph_model._children[result.payload.GetPath()]
            self.assertTrue(shader_model._inputs.ports, "polymorphic shader should expose at least one input port")
            input_model = shader_model._inputs.ports[0]
            self.assertTrue(input_model.proxy_attribute.polymorphic_unresolved)

            isolation = MaterialGraphIsolationModel(nodegraph_model, nodegraph_model)
            try:
                isolation.add_input_or_output((0.0, 0.0), True)
                input_node = next(node for node in isolation.nodes if type(node).get_type_name() == "InputNode")
                isolation[input_model].inputs = [input_node.empty_port]

                created_inputs = nodegraph.GetInputs()
                self.assertEqual(len(created_inputs), 1)
                self.assertTrue(UsdShade.Shader(result.payload).GetInput(input_model.name).HasConnectedSource())

                nodegraph_model.sync()
                shader_model.sync()
                interface_model = nodegraph_model._inputs.get_child_by_path(created_inputs[0].GetAttr().GetPath())
                self.assertTrue(interface_model.proxy_attribute.polymorphic_unresolved)
                self.assertTrue(shader_model.polymorphic_unresolved)

                int_source = UsdShade.NodeGraph.Define(
                    self._stage, self._material_path.AppendChild("ExternalIntSource")
                )
                int_output = int_source.CreateOutput("out", Sdf.ValueTypeNames.Int)
                external_result = ConnectPortToSource(created_inputs[0], int_output)
                self.assertTrue(external_result.success)

                nodegraph_model.sync()
                shader_model.sync()
                interface_model = nodegraph_model._inputs.get_child_by_path(created_inputs[0].GetAttr().GetPath())
                state = plugin.get_polymorphic_state_for_prim(result.payload)
                self.assertFalse(interface_model.proxy_attribute.polymorphic_unresolved)
                self.assertFalse(shader_model.polymorphic_unresolved, state.to_dict())
                self.assertEqual(state.candidates, ("test_poly_abs(int)",))
            finally:
                isolation.destroy()
        finally:
            nodegraph_model.destroy()
            plugin.destroy()
